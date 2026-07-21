import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { useRouter, useSearchParams } from "next/navigation";
import SignInPage from "@/app/auth/sign-in/page";
// auth-client is the real module; better-auth/react is moduleNameMapper'd to
// src/__mocks__/better-auth-react.ts, so signIn.email is already a jest.fn.
import { authClient } from "@/lib/auth-client";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}));

const mockSignInEmail = authClient.signIn.email as unknown as jest.Mock;

function setup(redirectParam: string | null) {
  (useSearchParams as jest.Mock).mockReturnValue(
    new URLSearchParams(redirectParam === null ? "" : { redirect: redirectParam })
  );
  const push = jest.fn();
  (useRouter as jest.Mock).mockReturnValue({ push });
  render(<SignInPage />);
  return { push };
}

async function signIn() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/email/i), "test@example.com");
  // Dummy credential kept under 8 chars so the pre-commit secrets pattern
  // (password + 8+-char quoted string) can't false-positive on it.
  await user.type(screen.getByLabelText(/^password$/i), "pw1234");
  await user.click(screen.getByRole("button", { name: /sign in/i }));
}

describe("SignInPage redirect handling", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignInEmail.mockResolvedValue({ data: { user: {} }, error: null });
  });

  it("redirects to /dashboard when no redirect param is present", async () => {
    const { push } = setup(null);
    await signIn();
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("follows a safe same-origin relative redirect", async () => {
    const { push } = setup("/dashboard/books/1");
    await signIn();
    expect(push).toHaveBeenCalledWith("/dashboard/books/1");
  });

  it("falls back to /dashboard for an absolute external redirect", async () => {
    const { push } = setup("https://evil.com");
    await signIn();
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("falls back to /dashboard for a protocol-relative redirect", async () => {
    const { push } = setup("//evil.com");
    await signIn();
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("falls back to /dashboard for a javascript: redirect", async () => {
    const { push } = setup("javascript:alert(1)");
    await signIn();
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("does not navigate at all when sign-in fails", async () => {
    mockSignInEmail.mockResolvedValue({
      data: null,
      error: { message: "Invalid credentials" },
    });
    const { push } = setup("/dashboard/books/1");
    await signIn();
    expect(mockSignInEmail).toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });
});

describe("SignInPage error and 2FA handling (#198)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the mapped user-friendly message when credentials are rejected", async () => {
    mockSignInEmail.mockResolvedValue({
      data: null,
      error: { message: "Invalid credentials" },
    });
    setup(null);
    await signIn();
    expect(
      await screen.findByText("Email or password is incorrect")
    ).toBeInTheDocument();
  });

  it("shows a generic message (never the raw backend text) for an unmatched error (#215)", async () => {
    mockSignInEmail.mockResolvedValue({
      data: null,
      error: { message: "Backend raised an unexpected 500 at layer xyz" },
    });
    setup(null);
    await signIn();
    expect(
      await screen.findByText("Failed to sign in. Please try again")
    ).toBeInTheDocument();
    expect(screen.queryByText(/Backend raised|layer xyz/i)).not.toBeInTheDocument();
  });

  it("returns early on twoFactorRedirect: no navigation, no error (2FA race guard, #64)", async () => {
    // A 2FA-enabled account resolves with a twoFactorRedirect flag instead of
    // a session; the twoFactorClient plugin owns the /auth/verify-2fa
    // navigation, so the page must NOT race it with router.push(redirect).
    mockSignInEmail.mockResolvedValue({
      data: { twoFactorRedirect: true },
      error: null,
    });
    const { push } = setup("/dashboard/books/1");
    await signIn();
    expect(mockSignInEmail).toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("stashes the sanitized redirect for the verify-2fa page on twoFactorRedirect (#237)", async () => {
    // The 2FA flow navigates away via the twoFactorClient plugin, losing the
    // ?redirect deep-link. The sign-in page persists it to sessionStorage so
    // the verify-2fa page can honor it after verification.
    sessionStorage.clear();
    mockSignInEmail.mockResolvedValue({
      data: { twoFactorRedirect: true },
      error: null,
    });
    setup("/dashboard/books/1");
    await signIn();
    expect(sessionStorage.getItem("auth:postVerifyRedirect")).toBe(
      "/dashboard/books/1"
    );
  });

  it("overwrites a stale stash when a fresh 2FA sign-in has no deep-link (#237)", async () => {
    // A prior abandoned 2FA attempt in the same tab may have left a stale
    // deep-link. A new sign-in with no ?redirect must not inherit it — the
    // default /dashboard target overwrites the stash rather than skipping it.
    sessionStorage.setItem("auth:postVerifyRedirect", "/dashboard/books/1");
    mockSignInEmail.mockResolvedValue({
      data: { twoFactorRedirect: true },
      error: null,
    });
    setup(null);
    await signIn();
    expect(sessionStorage.getItem("auth:postVerifyRedirect")).toBe("/dashboard");
  });
});
