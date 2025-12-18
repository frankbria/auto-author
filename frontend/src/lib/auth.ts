import 'server-only'

import { betterAuth } from "better-auth";
import { mongodbAdapter } from "better-auth/adapters/mongodb";
import { MongoClient, Db } from "mongodb";

const mongoUrl = process.env.DATABASE_URL || "mongodb://localhost:27017/auto_author";
const dbName = process.env.DATABASE_NAME || "auto_author";

// Lazy singleton pattern for MongoDB connection and auth instance
let client: MongoClient | null = null;
let db: Db | null = null;
let authInstance: ReturnType<typeof betterAuth> | null = null;

/**
 * Async factory function to get the auth instance with a connected MongoDB client.
 * Uses lazy initialization - connects to MongoDB on first call and caches the instance.
 *
 * @returns Promise<BetterAuth> - The connected auth instance
 */
export async function getAuth() {
  // Return cached instance if already initialized
  if (authInstance) {
    return authInstance;
  }

  // Initialize MongoDB client and connect
  if (!client) {
    client = new MongoClient(mongoUrl);
    await client.connect();
    console.log('MongoDB client connected for better-auth');
  }

  // Get database instance
  if (!db) {
    db = client.db(dbName);
  }

  // Create auth instance with connected database
  authInstance = betterAuth({
    database: mongodbAdapter(db),
    emailAndPassword: {
      enabled: true,
      autoSignIn: true,
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

  return authInstance;
}

/**
 * Gracefully close the MongoDB connection.
 * Should be called during application shutdown.
 */
export async function closeAuth() {
  if (client) {
    await client.close();
    console.log('MongoDB client closed for better-auth');
    client = null;
    db = null;
    authInstance = null;
  }
}
