import 'server-only'

import { betterAuth } from "better-auth";
import { mongodbAdapter } from "better-auth/adapters/mongodb";
import { twoFactor } from "better-auth/plugins";
import { MongoClient, Db } from "mongodb";

import { createAuthMiddleware } from "better-auth/api";
import { getDefaultCookieAttributes } from "./auth-cookies";
import { rejectWeakPassword } from "./auth-password-policy";
import { getIpAddressConfig } from "./auth-ip";
import { stampTermsAcceptance, termsAcceptanceFields } from "./auth-terms";
import { endOtherSessionsOnSecondFactorChange, forgetTrustedDevices } from "./auth-second-factor";

const mongoUrl = process.env.DATABASE_URL || "mongodb://localhost:27017/auto_author";
const dbName = process.env.DATABASE_NAME || "auto_author";

// Retry configuration
const MAX_RETRY_ATTEMPTS = parseInt(process.env.MONGO_MAX_RETRY_ATTEMPTS || '3', 10);
const BASE_RETRY_DELAY_MS = parseInt(process.env.MONGO_BASE_RETRY_DELAY_MS || '1000', 10);

/**
 * Build the better-auth instance for a connected database.
 *
 * Extracted from `getAuth()` so the singleton below can be typed as this
 * function's return type. better-auth 1.6 made `Auth<TOptions>` invariant over
 * its options, so the old `ReturnType<typeof betterAuth>` annotation — which
 * resolves to the widened `Auth<BetterAuthOptions>` — no longer accepts the
 * instance built from these concrete options. The `twoFactor()` plugin is what
 * makes them concretely different: it adds `twoFactorEnabled` to the user
 * schema, so the widened type is genuinely a different shape, not just a looser
 * one. Naming the factory keeps the full inferred options type intact.
 */
function createAuthInstance(database: Db) {
  return betterAuth({
    appName: "Auto Author",
    database: mongodbAdapter(database),
    // TOTP two-factor authentication (#64). The MongoDB adapter creates the
    // twoFactor collection on demand — no migration step required.
    plugins: [twoFactor()],
    // Every new account records the Terms version it accepted and when (#789).
    user: { additionalFields: termsAcceptanceFields },
    databaseHooks: { user: { create: { before: stampTermsAcceptance } } },
    // The password rule the pages show is enforced here too (#794).
    hooks: {
      before: createAuthMiddleware(rejectWeakPassword),
      // A 2FA change ends the account's other sessions in the same request (#972).
      after: createAuthMiddleware((ctx) => endOtherSessionsOnSecondFactorChange(ctx, database)),
    },
    emailAndPassword: {
      enabled: true,
      // No session until the address is verified (#792): sign-up returns none
      // and sign-in answers 403 EMAIL_NOT_VERIFIED.
      requireEmailVerification: true,
      // A reset ends every session of the account (#793). better-auth's default
      // leaves them alive, so a session an attacker held would survive the reset.
      revokeSessionsOnPasswordReset: true,
      // ...and forgets the devices trusted to skip the second factor (#972).
      // better-auth ends the sessions right after this returns; it never throws.
      onPasswordReset: async ({ user }) => {
        await forgetTrustedDevices(database, user.id);
      },
      // Password reset configuration
      sendResetPassword: async ({ user, url }) => {
        // Send password reset email
        // Use void to prevent timing attacks (don't reveal if email exists)
        void (async () => {
          try {
            // Import email service dynamically to avoid issues during build
            const { sendPasswordResetEmail } = await import("@/lib/email");
            await sendPasswordResetEmail({
              to: user.email,
              name: user.name || "User",
              resetUrl: url,
            });
            // No address in either line (#794): logs outlive and outreach the user record.
            console.log("Password reset email sent");
          } catch (error) {
            // A provider's error can echo the recipient in any case or
            // encoding, so anything address-shaped is masked.
            console.error(
              "Failed to send password reset email:",
              String(error).replace(/[^\s"'<>]+(?:@|%40)[^\s"'<>]+/gi, "[address]")
            );
          }
        })();
      },
    },
    emailVerification: {
      sendOnSignUp: true,
      // A refused sign-in mails a fresh link, which is how a user gets another one.
      sendOnSignIn: true,
      autoSignInAfterVerification: true,
      expiresIn: 60 * 60, // the email says one hour
      // Awaited, so a failed send rejects here. better-auth catches that and
      // logs it; the response is the same whether or not the email went out.
      sendVerificationEmail: async ({ user, url }) => {
        const { sendVerificationEmail } = await import("@/lib/email");
        await sendVerificationEmail({ to: user.email, verifyUrl: url });
      },
    },
    session: {
      expiresIn: 60 * 60 * 24 * 7, // 7 days
      updateAge: 60 * 60 * 24, // Refresh every 24 hours
      // No cookieCache (#793): with it, get-session kept answering from the
      // cookie for up to five minutes after a session was revoked.
    },
    advanced: {
      defaultCookieAttributes: getDefaultCookieAttributes(),
      // Rate-limit bucketing per client rather than one shared bucket (#602).
      ipAddress: getIpAddressConfig(),
    },
  });
}

// Lazy singleton pattern for MongoDB connection and auth instance
let client: MongoClient | null = null;
let db: Db | null = null;
let authInstance: ReturnType<typeof createAuthInstance> | null = null;

/**
 * Sleep for a specified duration with jitter
 * @param ms Base delay in milliseconds
 * @param jitterFactor Random jitter factor (0-1)
 */
function sleep(ms: number, jitterFactor = 0.3): Promise<void> {
  const jitter = Math.random() * ms * jitterFactor;
  return new Promise(resolve => setTimeout(resolve, ms + jitter));
}

/**
 * Async factory function to get the auth instance with a connected MongoDB client.
 * Uses lazy initialization - connects to MongoDB on first call and caches the instance.
 * Implements retry logic with exponential backoff for transient connection failures.
 *
 * @returns Promise<BetterAuth> - The connected auth instance
 * @throws Error if MongoDB connection fails after all retry attempts
 */
export async function getAuth() {
  // Return cached instance if already initialized
  if (authInstance) {
    return authInstance;
  }

  // Initialize MongoDB client and connect with retry logic
  if (!client) {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= MAX_RETRY_ATTEMPTS; attempt++) {
      try {
        client = new MongoClient(mongoUrl);
        await client.connect();
        console.log(`MongoDB client connected for better-auth (attempt ${attempt}/${MAX_RETRY_ATTEMPTS})`);
        break; // Success - exit retry loop
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Log detailed error information
        console.error(
          `MongoDB connection attempt ${attempt}/${MAX_RETRY_ATTEMPTS} failed:`,
          {
            message: lastError.message,
            stack: lastError.stack,
            mongoUrl: mongoUrl.replace(/\/\/([^:]+):([^@]+)@/, '//$1:****@'), // Mask credentials
          }
        );

        // Close partially opened client if it exists
        if (client) {
          try {
            await client.close();
          } catch (closeError) {
            console.error('Failed to close partially opened MongoDB client:', closeError);
          }
          client = null;
        }

        // If this was the last attempt, throw the error
        if (attempt === MAX_RETRY_ATTEMPTS) {
          const errorMsg = `MongoDB connection failed after ${MAX_RETRY_ATTEMPTS} attempts: ${lastError.message}`;
          console.error(errorMsg, { stack: lastError.stack });
          throw new Error(errorMsg);
        }

        // Calculate exponential backoff delay with jitter
        const delay = BASE_RETRY_DELAY_MS * Math.pow(2, attempt - 1);
        console.log(`Retrying MongoDB connection in ${delay}ms (with jitter)...`);
        await sleep(delay);
      }
    }
  }

  // Get database instance
  if (!db) {
    try {
      if (!client) {
        throw new Error('MongoDB client is null - connection failed');
      }
      db = client.db(dbName);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to get database instance:', errorMessage, { error });
      throw new Error(`Database initialization failed: ${errorMessage}`);
    }
  }

  // Create auth instance with connected database
  try {
    const instance = createAuthInstance(db);
    authInstance = instance;
    // Return the local, not the module-level cache: the cache is declared
    // `| null` (it has to be, to start empty), and returning it directly would
    // widen this function's inferred return type to include null — which is
    // what forced the null-check at the route handler.
    return instance;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('Failed to create auth instance:', errorMessage, { error });
    throw new Error(`Auth instance creation failed: ${errorMessage}`);
  }
}

/**
 * Gracefully close the MongoDB connection.
 * Should be called during application shutdown.
 * Ensures cleanup happens even if close() fails.
 */
export async function closeAuth() {
  if (client) {
    try {
      await client.close();
      console.log('MongoDB client closed for better-auth');
    } catch (error) {
      console.error(
        'Failed to close MongoDB client for better-auth:',
        error instanceof Error ? error.message : 'Unknown error',
        { error }
      );
    } finally {
      // Always reset module state, even if close() threw an error
      client = null;
      db = null;
      authInstance = null;
    }
  }
}
