/**
 * Session cookie attributes for better-auth.
 *
 * Kept separate from `auth.ts` (which pulls in `server-only` and the MongoDB
 * driver) so these security-critical attributes are unit-testable.
 */

/**
 * Extract cookie domain from BETTER_AUTH_URL
 * - localhost → undefined (browser handles it)
 * - dev.autoauthor.app → .dev.autoauthor.app (subdomain sharing)
 * - autoauthor.app → .autoauthor.app (subdomain sharing)
 */
export function getCookieDomain(): string | undefined {
  const authUrl = process.env.BETTER_AUTH_URL || process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "";

  if (!authUrl || authUrl.includes("localhost")) {
    return undefined; // Localhost - browser handles domain
  }

  try {
    const url = new URL(authUrl);
    const hostname = url.hostname;

    // Extract base domain (e.g., dev.autoauthor.app → .dev.autoauthor.app)
    // Leading dot makes cookie available to all subdomains
    return `.${hostname}`;
  } catch (error) {
    console.error("Failed to parse BETTER_AUTH_URL for cookie domain:", error);
    return undefined;
  }
}

/**
 * Default cookie attributes for the better-auth session cookie (issue #339).
 *
 * `sameSite: "lax"` is the CSRF defense. The backend authenticates from
 * `request.cookies`, and multipart uploads (avatar, book cover) are CORS-"simple"
 * requests that trigger no preflight — under `"none"` a cross-site form POST would
 * carry the victim's session cookie and execute server-side, since CORS only
 * blocks *reading* the response, not the write.
 *
 * `"lax"` costs nothing here because every frontend→backend hop is same-site
 * (same-site is computed on the registrable domain and ignores port/subdomain):
 * - Development: localhost:3000 → localhost:8000
 * - Staging/Prod: dev.autoauthor.app → api.dev.autoauthor.app (both autoauthor.app)
 *
 * If a genuinely cross-site deployment topology is ever introduced, `"none"` may
 * come back only alongside a double-submit CSRF token or an explicit Origin
 * allowlist check on state-changing methods.
 */
export function getDefaultCookieAttributes() {
  return {
    sameSite: "lax" as const,
    secure: true,
    httpOnly: true,
    // Share cookies across subdomains by setting domain to base domain
    // Automatically extracted from BETTER_AUTH_URL environment variable
    domain: getCookieDomain(),
  };
}
