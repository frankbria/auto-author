import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
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
const mockSendVerificationEmail =
  authClient.sendVerificationEmail as unknown as jest.Mock;

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

  it("signs up, then asks the user to check their email instead of entering the app (#792)", async () => {
    const { push } = setup();
    const user = await fillForm();
    await user.click(submitButton());

    expect(mockSignUpEmail).toHaveBeenCalledWith({
      email: "test@example.com",
      password: VALID_PW,
      name: "Test User",
      // The emailed link lands on the page that reads ?error= (#969).
      callbackURL: "/auth/verify-email?next=%2Fdashboard",
    });
    expect(
      await screen.findByRole("heading", { name: /check your email/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/test@example\.com/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /resend verification email/i })
    ).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /sign up/i })).not.toBeInTheDocument();
  });

  it("shows a generic message (never the raw backend text) for an unmatched error (#215)", async () => {
    mockSignUpEmail.mockResolvedValue({
      data: null,
      error: { message: "Backend raised an unexpected 500 at layer xyz" },
    });
    const { push } = setup();
    const user = await fillForm();
    await user.click(submitButton());

    expect(
      await screen.findByText("Unable to create account. Please try again later")
    ).toBeInTheDocument();
    expect(screen.queryByText(/Backend raised|layer xyz/i)).not.toBeInTheDocument();
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

  // #335: taking payments requires the sign-up flow to surface the legal docs.
  it("links to the Terms of Service and Privacy Policy", () => {
    setup();
    expect(
      screen.getByRole("link", { name: /terms of service/i })
    ).toHaveAttribute("href", "/terms");
    expect(
      screen.getByRole("link", { name: /privacy policy/i })
    ).toHaveAttribute("href", "/privacy");
  });

  // #789: the agreement has to be read before the button that makes it.
  it("shows the Terms notice above the submit button", () => {
    setup();
    const notice = screen.getByText(/by creating an account, you agree/i);
    expect(
      notice.compareDocumentPosition(submitButton()) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });
});

describe("Check your email: resend (#969)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignUpEmail.mockResolvedValue({ data: { user: {} }, error: null });
    mockSendVerificationEmail.mockResolvedValue({ data: { status: true }, error: null });
  });

  afterEach(() => jest.useRealTimers());

  async function reachCheckEmail() {
    setup();
    const user = await fillForm();
    await user.click(submitButton());
    await screen.findByRole("heading", { name: /check your email/i });
    return screen.getByRole("button", { name: /resend verification email/i });
  }

  it("sends another link to the address it knows, without the password", async () => {
    const resend = await reachCheckEmail();
    await userEvent.setup().click(resend);

    expect(mockSendVerificationEmail).toHaveBeenCalledWith({
      email: "test@example.com",
      callbackURL: "/auth/verify-email?next=%2Fdashboard",
    });
    expect(
      await screen.findByText(/sent a new link to test@example\.com/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/sent a new link/i);
  });

  it("holds off for 60 seconds with a countdown, then allows another send", async () => {
    const resend = await reachCheckEmail();
    jest.useFakeTimers();

    fireEvent.click(resend);
    await act(async () => {});
    expect(resend).toHaveAttribute("aria-disabled", "true");
    expect(resend).toHaveTextContent("(60s)");

    fireEvent.click(resend);
    expect(mockSendVerificationEmail).toHaveBeenCalledTimes(1);

    act(() => jest.advanceTimersByTime(59_000));
    expect(resend).toHaveTextContent("(1s)");

    act(() => jest.advanceTimersByTime(1_000));
    expect(resend).not.toHaveAttribute("aria-disabled", "true");
    fireEvent.click(resend);
    await act(async () => {});
    expect(mockSendVerificationEmail).toHaveBeenCalledTimes(2);
  });

  it("says so in the status region when better-auth refuses the send", async () => {
    mockSendVerificationEmail.mockResolvedValue({
      data: null,
      error: { status: 429, message: "Too many requests. Please try again later." },
    });
    const resend = await reachCheckEmail();
    await userEvent.setup().click(resend);

    expect(await screen.findByText(/too many requests/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/wait a minute/i);
  });

  it("reports a failed send without claiming success", async () => {
    mockSendVerificationEmail.mockResolvedValue({
      data: null,
      error: { status: 500, message: "boom" },
    });
    const resend = await reachCheckEmail();
    await userEvent.setup().click(resend);

    expect(
      await screen.findByText(/could not send a new link/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/sent a new link/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/boom/)).not.toBeInTheDocument();
  });
});
