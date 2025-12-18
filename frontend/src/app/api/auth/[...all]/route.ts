import { getAuth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

// Create handlers with async auth initialization
let handlers: { POST: any; GET: any } | null = null;

async function getHandlers() {
  if (!handlers) {
    const auth = await getAuth();
    handlers = toNextJsHandler(auth);
  }
  return handlers;
}

// Export async route handlers
export async function POST(req: Request) {
  const { POST } = await getHandlers();
  return POST(req);
}

export async function GET(req: Request) {
  const { GET } = await getHandlers();
  return GET(req);
}
