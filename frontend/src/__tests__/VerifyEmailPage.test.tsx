import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { redirect } from "next/navigation";
import VerifyEmailPage from "@/app/auth/verify-email/page";

jest.mock("next/navigation", () => ({
  redirect: jest.fn(() => {
    throw new Error("NEXT_REDIRECT");
  }),
}));

// Where better-auth's /verify-email lands the user (#969): it appends
// ?error=TOKEN_EXPIRED / INVALID_TOKEN / USER_NOT_FOUND on failure.
async function renderPage(params: Record<string, string>) {
  render(await VerifyEmailPage({ searchParams: Promise.resolve(params) }));
}

describe("VerifyEmailPage (#969)", () => {
  beforeEach(() => jest.clearAllMocks());

  it("sends a verified user on to the destination", async () => {
    await expect(
      VerifyEmailPage({ searchParams: Promise.resolve({ next: "/dashboard/books/1" }) })
    ).rejects.toThrow("NEXT_REDIRECT");
    expect(redirect).toHaveBeenCalledWith("/dashboard/books/1");
  });

  it("never redirects off-site, whatever next says", async () => {
    await expect(
      VerifyEmailPage({ searchParams: Promise.resolve({ next: "//evil.com" }) })
    ).rejects.toThrow("NEXT_REDIRECT");
    expect(redirect).toHaveBeenCalledWith("/dashboard");
  });

  it("explains an expired link and how to get a new one", async () => {
    await renderPage({ error: "TOKEN_EXPIRED", next: "/dashboard/books/1" });
    expect(redirect).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: /link has expired/i })).toBeInTheDocument();
    expect(screen.getByText(/with your email and password and we will email you a fresh one/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute(
      "href",
      "/auth/sign-in?redirect=%2Fdashboard%2Fbooks%2F1"
    );
  });

  it("explains a damaged or unknown link", async () => {
    await renderPage({ error: "INVALID_TOKEN" });
    expect(screen.getByRole("heading", { name: /link is not valid/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute(
      "href",
      "/auth/sign-in?redirect=%2Fdashboard"
    );
  });
});
