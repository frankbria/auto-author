import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import ResetPasswordPage from "@/app/auth/reset-password/page";

// Get the mock function - will be accessed in tests
let mockResetPassword: jest.Mock;
const mockPush = jest.fn();
let mockSearchParams = new Map<string, string>();

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  useSearchParams: () => ({
    get: (key: string) => mockSearchParams.get(key) || null,
  }),
}));

describe("ResetPasswordPage", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    // Get fresh reference to the mock each time
    const { authClient } = jest.requireMock("@/lib/auth-client");
    mockResetPassword = authClient.resetPassword;
    mockResetPassword.mockReset();
    mockResetPassword.mockResolvedValue({
      data: {},
      error: null,
    });
    mockPush.mockReset();
    mockSearchParams = new Map([["token", "valid-token-123"]]);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders the reset password form with valid token", () => {
    render(<ResetPasswordPage />);

    expect(screen.getByText(/reset password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset password/i })).toBeInTheDocument();
  });

  it("shows invalid token message when token is missing", () => {
    mockSearchParams.delete("token");
    render(<ResetPasswordPage />);

    expect(screen.getByText(/invalid reset link/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /request new link/i })).toBeInTheDocument();
  });

  it("shows error message for invalid token in URL", () => {
    mockSearchParams.set("error", "INVALID_TOKEN");
    mockSearchParams.delete("token");
    render(<ResetPasswordPage />);

    expect(screen.getByText(/this reset link is invalid/i)).toBeInTheDocument();
  });

  it("shows error message for expired token in URL", () => {
    mockSearchParams.set("error", "EXPIRED_TOKEN");
    mockSearchParams.delete("token");
    render(<ResetPasswordPage />);

    expect(screen.getByText(/invalid reset link/i)).toBeInTheDocument();
  });

  it("shows password requirements", () => {
    render(<ResetPasswordPage />);

    expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    expect(screen.getByText(/at least one uppercase letter/i)).toBeInTheDocument();
    expect(screen.getByText(/at least one lowercase letter/i)).toBeInTheDocument();
    expect(screen.getByText(/at least one number/i)).toBeInTheDocument();
  });

  it("validates password match in real-time", async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ResetPasswordPage />);

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm new password/i);

    await user.type(passwordInput, "ValidPass1");
    await user.type(confirmInput, "DifferentPass1");

    expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
  });

  it("disables submit button until password is valid", () => {
    render(<ResetPasswordPage />);

    const submitButton = screen.getByRole("button", { name: /reset password/i });
    expect(submitButton).toBeDisabled();
  });

  it("enables submit button when password is valid and matches", async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ResetPasswordPage />);

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm new password/i);

    await user.type(passwordInput, "ValidPass1");
    await user.type(confirmInput, "ValidPass1");

    const submitButton = screen.getByRole("button", { name: /reset password/i });
    expect(submitButton).toBeEnabled();
  });

  it("submits form with valid password", async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ResetPasswordPage />);

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm new password/i);
    const submitButton = screen.getByRole("button", { name: /reset password/i });

    await user.type(passwordInput, "ValidPass1");
    await user.type(confirmInput, "ValidPass1");
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockResetPassword).toHaveBeenCalledWith({
        newPassword: "ValidPass1",
        token: "valid-token-123",
      });
    });
  });

  it("shows success message after password reset", async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ResetPasswordPage />);

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm new password/i);
    const submitButton = screen.getByRole("button", { name: /reset password/i });

    await user.type(passwordInput, "ValidPass1");
    await user.type(confirmInput, "ValidPass1");
    await user.click(submitButton);

    expect(await screen.findByText(/password has been successfully reset/i)).toBeInTheDocument();
  });

  it("redirects to sign-in after success", async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ResetPasswordPage />);

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm new password/i);
    const submitButton = screen.getByRole("button", { name: /reset password/i });

    await user.type(passwordInput, "ValidPass1");
    await user.type(confirmInput, "ValidPass1");
    await user.click(submitButton);

    await screen.findByText(/password has been successfully reset/i);

    // Advance timer for redirect
    jest.advanceTimersByTime(3000);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/auth/sign-in");
    });
  });

  it("shows error for expired token from API", async () => {
    mockResetPassword.mockResolvedValue({
      data: null,
      error: { message: "Token expired" },
    });

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ResetPasswordPage />);

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm new password/i);
    const submitButton = screen.getByRole("button", { name: /reset password/i });

    await user.type(passwordInput, "ValidPass1");
    await user.type(confirmInput, "ValidPass1");
    await user.click(submitButton);

    expect(await screen.findByText(/this reset link has expired/i)).toBeInTheDocument();
  });

  it("toggles password visibility", async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ResetPasswordPage />);

    const passwordInput = screen.getByLabelText(/new password/i);
    expect(passwordInput).toHaveAttribute("type", "password");

    // Find and click the show password button (first one)
    const toggleButtons = screen.getAllByRole("button", { name: /show password/i });
    await user.click(toggleButtons[0]);

    expect(passwordInput).toHaveAttribute("type", "text");
  });

  it("has back to sign in link", () => {
    render(<ResetPasswordPage />);

    const backLink = screen.getByText(/back to sign in/i);
    expect(backLink.closest("a")).toHaveAttribute("href", "/auth/sign-in");
  });

  it("shows password strength indicator", async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ResetPasswordPage />);

    const passwordInput = screen.getByLabelText(/new password/i);
    await user.type(passwordInput, "ValidPass1");

    expect(screen.getByText(/password strength/i)).toBeInTheDocument();
    expect(screen.getByText(/strong/i)).toBeInTheDocument();
  });
});
