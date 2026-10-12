// better-auth/api is ESM-only, so Jest cannot load it. Tests need only these
// two: the middleware wrapper (identity here) and the error it throws (#794).
export const createAuthMiddleware = <T>(handler: T): T => handler;

export class APIError extends Error {
  constructor(
    public status: string,
    public body: { message?: string } = {}
  ) {
    super(body.message);
  }
}
