import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { useRouter, useSearchParams } from "next/navigation";
import SignInPage from "@/app/auth/sign-in/page";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}));

const mockSignInEmail = jest.fn();
jest.mock("@/lib/auth-client", () => ({
  authClient: {
    signIn: {
      email: (...args: unknown[]) => mockSignInEmail(...args),
    },
  },
}));

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
});
