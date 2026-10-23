// better-auth/api is ESM-only, so Jest cannot load it. Tests need only these:
// the middleware wrapper (identity here), the error it throws (#794) and its guard (#972).
export const createAuthMiddleware = <T>(handler: T): T => handler;

export class APIError extends Error {
  constructor(
    public status: string,
    public body: { message?: string } = {}
  ) {
    super(body.message);
  }
}

export const isAPIError = (error: unknown): error is APIError => error instanceof APIError;
