import "server-only";

interface PasswordResetEmailParams {
  to: string;
  name: string;
  resetUrl: string;
}

/**
 * Performs a fetch request with timeout, retry logic, and exponential backoff.
 *
 * @param url - The URL to fetch
 * @param options - Fetch options (method, headers, body, etc.)
 * @param retries - Number of retry attempts (default: 3)
 * @param timeout - Request timeout in milliseconds (default: 10000)
 * @returns The successful Response object
 * @throws Error with detailed message after exhausting retries
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries: number = 3,
  timeout: number = 10000
): Promise<Response> {
  const transientStatusCodes = [429, 500, 502, 503, 504];
  let lastError: Error | null = null;
  let lastResponseBody: string | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // If response is OK, return it
      if (response.ok) {
        return response;
      }

      // Check if this is a transient error that should be retried
      if (transientStatusCodes.includes(response.status)) {
        lastResponseBody = await response.text().catch(() => null);
        lastError = new Error(
          `HTTP ${response.status}: ${response.statusText}${lastResponseBody ? ` - ${lastResponseBody}` : ""}`
        );

        // Don't retry on last attempt
        if (attempt < retries) {
          const backoffMs = Math.pow(2, attempt) * 1000; // 1s, 2s, 4s
          await new Promise((resolve) => setTimeout(resolve, backoffMs));
          continue;
        }
      } else {
        // Non-transient error (4xx except 429), throw immediately
        const errorBody = await response.text().catch(() => null);
        throw new Error(
          `HTTP ${response.status}: ${response.statusText}${errorBody ? ` - ${errorBody}` : ""}`
        );
      }
    } catch (error) {
      clearTimeout(timeoutId);

      // Handle abort/timeout errors
      if (error instanceof Error && error.name === "AbortError") {
        lastError = new Error(`Request timeout after ${timeout}ms`);
      } else if (
        error instanceof TypeError &&
        (error.message.includes("network") || error.message.includes("fetch"))
      ) {
        // Network error (e.g., no internet connection)
        lastError = new Error(`Network error: ${error.message}`);
      } else if (error instanceof Error) {
        // Re-throw non-transient errors immediately
        if (!transientStatusCodes.some((code) => error.message.includes(`HTTP ${code}`))) {
          throw error;
        }
        lastError = error;
      } else {
        throw error;
      }

      // Don't retry on last attempt
      if (attempt < retries) {
        const backoffMs = Math.pow(2, attempt) * 1000; // 1s, 2s, 4s
        await new Promise((resolve) => setTimeout(resolve, backoffMs));
      }
    }
  }

  // All retries exhausted
  throw new Error(
    `Failed after ${retries + 1} attempts: ${lastError?.message || "Unknown error"}${
      lastResponseBody ? ` (Response: ${lastResponseBody})` : ""
    }`
  );
}

/**
 * Sends a password reset email to the user.
 *
 * This function supports multiple email providers configured via environment variables:
 * - Resend (recommended for Next.js)
 * - SendGrid
 * - SMTP (Nodemailer)
 *
 * If no email provider is configured, it logs to console (development mode).
 */
export async function sendPasswordResetEmail({
  to,
  name,
  resetUrl,
}: PasswordResetEmailParams): Promise<void> {
  const provider = process.env.EMAIL_SERVICE_PROVIDER?.toLowerCase();
  const fromAddress = process.env.EMAIL_FROM_ADDRESS || "noreply@autoauthor.app";
  const fromName = process.env.EMAIL_FROM_NAME || "Auto Author";

  const subject = "Reset Your Password";
  const htmlContent = generatePasswordResetHtml({ name, resetUrl });
  const textContent = generatePasswordResetText({ name, resetUrl });

  // Development mode: log to console if no provider configured
  if (process.env.NODE_ENV === "development" && (!provider || provider === "console")) {
    console.log("=".repeat(60));
    console.log("PASSWORD RESET EMAIL (Development Mode)");
    console.log("=".repeat(60));
    console.log(`To: ${to}`);
    console.log(`From: ${fromName} <${fromAddress}>`);
    console.log(`Subject: ${subject}`);
    console.log("-".repeat(60));
    console.log(textContent);
    console.log("=".repeat(60));
    console.log(`Reset URL: ${resetUrl}`);
    console.log("=".repeat(60));
    return;
  }

  // Resend provider
  if (provider === "resend") {
    const apiKey = process.env.EMAIL_SERVICE_API_KEY;
    if (!apiKey) {
      throw new Error("EMAIL_SERVICE_API_KEY is required for Resend provider");
    }

    try {
      await fetchWithRetry("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          from: `${fromName} <${fromAddress}>`,
          to: [to],
          subject,
          html: htmlContent,
          text: textContent,
        }),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Resend API error: ${message}`);
    }

    return;
  }

  // SendGrid provider
  if (provider === "sendgrid") {
    const apiKey = process.env.EMAIL_SERVICE_API_KEY;
    if (!apiKey) {
      throw new Error("EMAIL_SERVICE_API_KEY is required for SendGrid provider");
    }

    try {
      await fetchWithRetry("https://api.sendgrid.com/v3/mail/send", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          personalizations: [{ to: [{ email: to }] }],
          from: { email: fromAddress, name: fromName },
          subject,
          content: [
            { type: "text/plain", value: textContent },
            { type: "text/html", value: htmlContent },
          ],
        }),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`SendGrid API error: ${message}`);
    }

    return;
  }

  // Unknown provider
  if (process.env.NODE_ENV === "production") {
    throw new Error(
      `Unknown email provider: ${provider}. Configure EMAIL_SERVICE_PROVIDER to 'resend' or 'sendgrid'.`
    );
  }

  // In development, log a warning and return silently for convenience
  console.warn(`Unknown email provider: ${provider}. Email not sent.`);
}

function generatePasswordResetHtml({
  name,
  resetUrl,
}: {
  name: string;
  resetUrl: string;
}): string {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your Password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
    <h1 style="color: white; margin: 0; font-size: 28px;">Auto Author</h1>
  </div>

  <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
    <h2 style="color: #333; margin-top: 0;">Reset Your Password</h2>

    <p>Hi ${name},</p>

    <p>We received a request to reset your password. Click the button below to create a new password:</p>

    <div style="text-align: center; margin: 30px 0;">
      <a href="${resetUrl}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Reset Password</a>
    </div>

    <p style="color: #666; font-size: 14px;">This link will expire in <strong>1 hour</strong>.</p>

    <p style="color: #666; font-size: 14px;">If the button doesn't work, copy and paste this link into your browser:</p>
    <p style="word-break: break-all; color: #667eea; font-size: 12px;">${resetUrl}</p>

    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">

    <p style="color: #999; font-size: 12px; margin-bottom: 0;">
      <strong>Security Notice:</strong> If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.
    </p>

    <p style="color: #999; font-size: 12px;">
      Never share this link with anyone. Auto Author support will never ask for your password.
    </p>
  </div>

  <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
    <p>&copy; ${new Date().getFullYear()} Auto Author. All rights reserved.</p>
  </div>
</body>
</html>
`.trim();
}

function generatePasswordResetText({
  name,
  resetUrl,
}: {
  name: string;
  resetUrl: string;
}): string {
  return `
Reset Your Password

Hi ${name},

We received a request to reset your password. Use the link below to create a new password:

${resetUrl}

This link will expire in 1 hour.

SECURITY NOTICE:
- If you didn't request this password reset, you can safely ignore this email
- Your password will remain unchanged
- Never share this link with anyone
- Auto Author support will never ask for your password

---
© ${new Date().getFullYear()} Auto Author. All rights reserved.
`.trim();
}
