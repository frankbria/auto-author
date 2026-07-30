import { getAuth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

// Type for Next.js route handler
type RouteHandler = (req: Request) => Promise<Response> | Response;

// Handlers object type from toNextJsHandler
type AuthHandlers = {
  POST: RouteHandler;
  GET: RouteHandler;
};

// Create handlers with async auth initialization
let handlers: AuthHandlers | null = null;

async function getHandlers(): Promise<AuthHandlers> {
  if (!handlers) {
    try {
      const auth = await getAuth();
      handlers = toNextJsHandler(auth) as AuthHandlers;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to initialize auth handlers:', errorMessage, { error });
      throw new Error(`Auth initialization failed: ${errorMessage}`);
    }
  }
  return handlers;
}

// Export async route handlers with error handling
export async function POST(req: Request): Promise<Response> {
  try {
    const { POST } = await getHandlers();
    return POST(req);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown authentication error';
    // Logged server-side in full; the client gets a generic message. This
    // endpoint answers unauthenticated callers, and internal errors here name
    // database hosts, driver versions and config keys — free reconnaissance
    // for anyone probing the auth surface (#352).
    console.error('POST /api/auth error:', errorMessage, { error });
    return new Response(
      JSON.stringify({
        error: 'Authentication service unavailable',
        message: 'The authentication service is temporarily unavailable. Please try again.'
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

export async function GET(req: Request): Promise<Response> {
  try {
    const { GET } = await getHandlers();
    return GET(req);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown authentication error';
    // See the POST handler: full detail to the server log, generic text to the
    // client (#352).
    console.error('GET /api/auth error:', errorMessage, { error });
    return new Response(
      JSON.stringify({
        error: 'Authentication service unavailable',
        message: 'The authentication service is temporarily unavailable. Please try again.'
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}
