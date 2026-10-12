import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import ForgotPasswordPage from "@/app/auth/forgot-password/page";

// Import the mock function directly from the better-auth mock
// This gives us the same reference that authClient uses
import { mockRequestPasswordReset } from "../__mocks__/better-auth-react";

describe("ForgotPasswordPage", () => {
  beforeEach(() => {
    mockRequestPasswordReset.mockReset();
    mockRequestPasswordReset.mockResolvedValue({
      data: {},
      error: null,
    });
  });

  it("renders the forgot password form", () => {
    render(<ForgotPasswordPage />);

    expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send reset link/i })).toBeInTheDocument();
    expect(screen.getByText(/back to sign in/i)).toBeInTheDocument();
  });

  it("validates email format before submission", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    // Use an email that passes HTML5 validation but fails our stricter regex (no TLD)
    await user.type(emailInput, "test@test");
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
    });
    expect(mockRequestPasswordReset).not.toHaveBeenCalled();
  });

  it("submits form with valid email and shows success", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "test@example.com");
    await user.click(submitButton);

    // Verify success state is shown
    expect(await screen.findByText(/check your email/i)).toBeInTheDocument();
    expect(screen.getByText(/test@example.com/i)).toBeInTheDocument();
    // #794: the page does not claim an email was sent, only that one is if the account exists.
    expect(screen.getByText(/if an account exists for/i)).toBeInTheDocument();
    expect(screen.queryByText(/we've sent a password reset link to/i)).not.toBeInTheDocument();
    expect(screen.getByText(/link will expire in 1 hour/i)).toBeInTheDocument();
  });

  it("shows error message on API failure", async () => {
    // Configure mock to return error before rendering
    mockRequestPasswordReset.mockResolvedValueOnce({
      data: null,
      error: { message: "User not found" },
    });

    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "notfound@example.com");
    await user.click(submitButton);

    // #794: never say whether the account exists, and never echo the server's text.
    expect(await screen.findByText(/could not send the reset link/i)).toBeInTheDocument();
    expect(screen.queryByText(/no account found/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/user not found/i)).not.toBeInTheDocument();
  });

  it("does not echo a thrown error's text (#794)", async () => {
    mockRequestPasswordReset.mockRejectedValueOnce(new Error("User notfound@example.com does not exist"));

    const user = userEvent.setup();
    render(<ForgotPasswordPage />);
    await user.type(screen.getByLabelText(/email/i), "notfound@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByText(/could not send the reset link/i)).toBeInTheDocument();
    expect(screen.queryByText(/does not exist/i)).not.toBeInTheDocument();
  });

  it("shows rate limit error message", async () => {
    // Configure mock to return rate limit error before rendering
    mockRequestPasswordReset.mockResolvedValueOnce({
      data: null,
      error: { message: "Rate limit exceeded" },
    });

    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "test@example.com");
    await user.click(submitButton);

    expect(await screen.findByText(/too many requests/i)).toBeInTheDocument();
  });

  it("shows loading state during submission", async () => {
    // Make mock delay response
    mockRequestPasswordReset.mockImplementationOnce(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: {}, error: null }), 500))
    );

    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "test@example.com");
    await user.click(submitButton);

    // Should show loading state immediately after click
    await waitFor(() => {
      expect(screen.getByText(/sending/i)).toBeInTheDocument();
    });
  });

  it("allows requesting another link from success state", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    // Submit form
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    // Wait for success state
    await screen.findByText(/check your email/i);

    // Click "Send another link"
    await user.click(screen.getByRole("button", { name: /send another link/i }));

    // Should be back to form state
    await waitFor(() => {
      expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/email/i)).toHaveValue("");
  });

  it("has back to sign in link", () => {
    render(<ForgotPasswordPage />);

    const backLink = screen.getByText(/back to sign in/i);
    expect(backLink.closest("a")).toHaveAttribute("href", "/auth/sign-in");
  });
});
