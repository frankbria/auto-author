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
    console.error('POST /api/auth error:', errorMessage, { error });
    return new Response(
      JSON.stringify({
        error: 'Authentication service unavailable',
        message: errorMessage
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
    console.error('GET /api/auth error:', errorMessage, { error });
    return new Response(
      JSON.stringify({
        error: 'Authentication service unavailable',
        message: errorMessage
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}
