import 'server-only'

import { betterAuth } from "better-auth";
import { mongodbAdapter } from "better-auth/adapters/mongodb";
import { MongoClient, Db } from "mongodb";

const mongoUrl = process.env.DATABASE_URL || "mongodb://localhost:27017/auto_author";
const dbName = process.env.DATABASE_NAME || "auto_author";

// Retry configuration
const MAX_RETRY_ATTEMPTS = parseInt(process.env.MONGO_MAX_RETRY_ATTEMPTS || '3', 10);
const BASE_RETRY_DELAY_MS = parseInt(process.env.MONGO_BASE_RETRY_DELAY_MS || '1000', 10);

// Lazy singleton pattern for MongoDB connection and auth instance
let client: MongoClient | null = null;
let db: Db | null = null;
let authInstance: ReturnType<typeof betterAuth> | null = null;

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
    authInstance = betterAuth({
      database: mongodbAdapter(db),
      emailAndPassword: {
        enabled: true,
        autoSignIn: true,
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
              console.log(`Password reset email sent to ${user.email}`);
            } catch (error) {
              console.error("Failed to send password reset email:", error);
            }
          })();
        },
      },
      session: {
        expiresIn: 60 * 60 * 24 * 7, // 7 days
        updateAge: 60 * 60 * 24, // Refresh every 24 hours
        cookieCache: {
          enabled: true,
          maxAge: 5 * 60, // Cache for 5 minutes
        },
      },
      advanced: {
        defaultCookieAttributes: {
          sameSite: "lax",
          secure: process.env.NODE_ENV === "production",
          httpOnly: true,
        },
      },
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('Failed to create auth instance:', errorMessage, { error });
    throw new Error(`Auth instance creation failed: ${errorMessage}`);
  }

  return authInstance;
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
