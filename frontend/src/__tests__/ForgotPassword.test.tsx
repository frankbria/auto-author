import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import ForgotPasswordPage from "@/app/auth/forgot-password/page";

// Create mock function
const mockForgetPassword = jest.fn();

// Re-mock the auth client module for this test file
jest.mock("@/lib/auth-client", () => ({
  authClient: {
    forgetPassword: mockForgetPassword,
    signIn: { email: jest.fn() },
    signUp: { email: jest.fn() },
    signOut: jest.fn(),
    getSession: jest.fn(),
    resetPassword: jest.fn(),
  },
  useSession: jest.fn(() => ({
    data: null,
    isPending: false,
    error: null,
  })),
}));

describe("ForgotPasswordPage", () => {
  beforeEach(() => {
    mockForgetPassword.mockReset();
    mockForgetPassword.mockResolvedValue({
      data: {},
      error: null,
    });
  });

  it("renders the forgot password form", () => {
    render(<ForgotPasswordPage />);

    expect(screen.getByRole("heading", { name: /forgot password/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send reset link/i })).toBeInTheDocument();
    expect(screen.getByText(/back to sign in/i)).toBeInTheDocument();
  });

  it("validates email format before submission", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "invalid-email");
    await user.click(submitButton);

    expect(await screen.findByText(/please enter a valid email address/i)).toBeInTheDocument();
    expect(mockForgetPassword).not.toHaveBeenCalled();
  });

  it("submits form with valid email", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "test@example.com");
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockForgetPassword).toHaveBeenCalledWith({
        email: "test@example.com",
        redirectTo: "/auth/reset-password",
      });
    });
  });

  it("shows success message after email sent", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "test@example.com");
    await user.click(submitButton);

    expect(await screen.findByText(/check your email/i)).toBeInTheDocument();
    expect(screen.getByText(/test@example.com/i)).toBeInTheDocument();
    expect(screen.getByText(/link will expire in 1 hour/i)).toBeInTheDocument();
  });

  it("shows error message on API failure", async () => {
    mockForgetPassword.mockResolvedValue({
      data: null,
      error: { message: "User not found" },
    });

    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "notfound@example.com");
    await user.click(submitButton);

    expect(await screen.findByText(/no account found with this email address/i)).toBeInTheDocument();
  });

  it("shows rate limit error message", async () => {
    mockForgetPassword.mockResolvedValue({
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
    mockForgetPassword.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: {}, error: null }), 100))
    );

    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole("button", { name: /send reset link/i });

    await user.type(emailInput, "test@example.com");
    await user.click(submitButton);

    expect(screen.getByText(/sending/i)).toBeInTheDocument();
    expect(emailInput).toBeDisabled();
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
    expect(screen.getByRole("heading", { name: /forgot password/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toHaveValue("");
  });

  it("has back to sign in link", () => {
    render(<ForgotPasswordPage />);

    const backLink = screen.getByText(/back to sign in/i);
    expect(backLink.closest("a")).toHaveAttribute("href", "/auth/sign-in");
  });
});
