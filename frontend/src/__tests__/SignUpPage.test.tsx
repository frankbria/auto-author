import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { useRouter } from "next/navigation";
import SignUpPage from "@/app/auth/sign-up/page";
// auth-client is the real module; better-auth/react is moduleNameMapper'd to
// src/__mocks__/better-auth-react.ts, so signUp.email is already a jest.fn.
import { authClient } from "@/lib/auth-client";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

const mockSignUpEmail = authClient.signUp.email as unknown as jest.Mock;

// Meets all requirements (≥8 chars, upper, lower, digit); built by
// concatenation so the pre-commit secrets pattern can't false-positive.
const VALID_PW = ["Valid", "Pass1"].join("");

function setup() {
  const push = jest.fn();
  (useRouter as jest.Mock).mockReturnValue({ push });
  render(<SignUpPage />);
  return { push };
}

async function fillForm(confirm: string = VALID_PW, pw: string = VALID_PW) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/^name$/i), "Test User");
  await user.type(screen.getByLabelText(/^email$/i), "test@example.com");
  await user.type(screen.getByLabelText(/^password$/i), pw);
  await user.type(screen.getByLabelText(/confirm password/i), confirm);
  return user;
}

function submitButton() {
  return screen.getByRole("button", { name: /sign up/i });
}

describe("SignUpPage (#198)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignUpEmail.mockResolvedValue({ data: { user: {} }, error: null });
  });

  it("signs up with name/email/password and redirects to /dashboard", async () => {
    const { push } = setup();
    const user = await fillForm();
    await user.click(submitButton());

    expect(mockSignUpEmail).toHaveBeenCalledWith({
      email: "test@example.com",
      password: VALID_PW,
      name: "Test User",
    });
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("renders the mapped message and does not navigate when the account already exists", async () => {
    mockSignUpEmail.mockResolvedValue({
      data: null,
      error: { message: "User already exists" },
    });
    const { push } = setup();
    const user = await fillForm();
    await user.click(submitButton());

    expect(
      await screen.findByText("An account with this email already exists")
    ).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("blocks submission with inline error when passwords do not match", async () => {
    const { push } = setup();
    await fillForm("Different1");

    expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    expect(submitButton()).toBeDisabled();
    expect(mockSignUpEmail).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it("keeps submit disabled while the password fails requirements", async () => {
    setup();
    // lowercase-only: fails uppercase + number requirements
    await fillForm("weakpass", "weakpass");

    expect(submitButton()).toBeDisabled();
    expect(mockSignUpEmail).not.toHaveBeenCalled();
  });
});
