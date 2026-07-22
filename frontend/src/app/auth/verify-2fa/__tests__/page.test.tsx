import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { useRouter } from "next/navigation";
import VerifyTwoFactorPage from "@/app/auth/verify-2fa/page";
import { authClient } from "@/lib/auth-client";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

jest.mock("@/lib/toast", () => ({
  toast: jest.fn(),
}));

const mockVerifyTotp = authClient.twoFactor.verifyTotp as unknown as jest.Mock;

function setup() {
  const push = jest.fn();
  (useRouter as jest.Mock).mockReturnValue({ push });
  render(<VerifyTwoFactorPage />);
  return { push };
}

async function enterCode(code = "123456") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/verification code/i), code);
}

describe("VerifyTwoFactorPage post-verification redirect (#237)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    mockVerifyTotp.mockResolvedValue({ data: {}, error: null });
  });

  it("redirects to the stashed deep-link after successful verification", async () => {
    sessionStorage.setItem("auth:postVerifyRedirect", "/dashboard/books/1");
    const { push } = setup();
    await enterCode();
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/dashboard/books/1")
    );
    // The one-shot value is cleared once consumed.
    expect(sessionStorage.getItem("auth:postVerifyRedirect")).toBeNull();
  });

  it("falls back to /dashboard when no redirect was stashed", async () => {
    const { push } = setup();
    await enterCode();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });

  it("re-sanitizes the stashed value at the consumption point (defense in depth)", async () => {
    // Even if a tampered/unsafe value reaches sessionStorage, the verify page
    // runs it through sanitizeRedirectPath before navigating.
    sessionStorage.setItem("auth:postVerifyRedirect", "https://evil.com");
    const { push } = setup();
    await enterCode();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });

  it("does not redirect when verification fails", async () => {
    mockVerifyTotp.mockResolvedValue({
      data: null,
      error: { message: "bad code" },
    });
    sessionStorage.setItem("auth:postVerifyRedirect", "/dashboard/books/1");
    const { push } = setup();
    await enterCode();
    await waitFor(() => expect(mockVerifyTotp).toHaveBeenCalled());
    expect(push).not.toHaveBeenCalled();
    // The stash survives a failed attempt so a retry still honors it.
    expect(sessionStorage.getItem("auth:postVerifyRedirect")).toBe(
      "/dashboard/books/1"
    );
  });
});
