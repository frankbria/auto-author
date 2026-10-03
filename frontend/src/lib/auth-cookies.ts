/**
 * Session cookie attributes for better-auth.
 *
 * Kept separate from `auth.ts` (which pulls in `server-only` and the MongoDB
 * driver) so these security-critical attributes are unit-testable.
 */

/**
 * Extract cookie domain from BETTER_AUTH_URL
 * - localhost → undefined (browser handles it)
 * - dev.autoauthor.app → .dev.autoauthor.app (shared with api.dev.autoauthor.app)
 * - app.autoauthor.app → .app.autoauthor.app (shared with api.app.autoauthor.app)
 * - autoauthor.app → undefined, a host-only cookie (issue #778)
 *
 * An apex is never widened: `.autoauthor.app` domain-matches every subdomain,
 * including the shared staging box at dev.autoauthor.app / api.dev.autoauthor.app,
 * so a production session cookie would be sent there. A host-only cookie at the
 * apex is not sent to any subdomain, which means the API must then be reached on
 * the same host (or production moves to a subdomain, mirroring staging).
 */
export function getCookieDomain(): string | undefined {
  const authUrl = process.env.BETTER_AUTH_URL || process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "";

  if (!authUrl || authUrl.includes("localhost")) {
    return undefined; // Localhost - browser handles domain
  }

  try {
    const url = new URL(authUrl);
    const hostname = url.hostname;

    // ponytail: two labels = apex; a multi-label public suffix (example.co.uk)
    // reads as a subdomain here. Switch to a public-suffix list if we ever host there.
    if (hostname.split(".").length <= 2) {
      console.warn(
        `Auth cookie for apex host ${hostname} is host-only: it will not reach any subdomain, including an api.${hostname} backend.`
      );
      return undefined;
    }

    // Leading dot shares the cookie with this host's own subdomains (api.<host>)
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
    // BETTER_AUTH_URL's host and its subdomains; never a whole apex (#778)
    domain: getCookieDomain(),
  };
}
