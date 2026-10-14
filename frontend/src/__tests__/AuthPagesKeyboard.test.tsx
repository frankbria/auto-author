/**
 * #837: sign-in and sign-up with a keyboard and nothing else.
 *
 * "Forgot password?" and the show-password buttons had `tabIndex={-1}`, so Tab
 * went past them. For someone who cannot use a mouse that removed the only way
 * to recover an account, and the only way to check what they had typed.
 *
 * No test here clicks.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import SignInPage from "@/app/auth/sign-in/page";
import SignUpPage from "@/app/auth/sign-up/page";

expect.extend(toHaveNoViolations);

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(() => ({ push: jest.fn() })),
  useSearchParams: jest.fn(() => new URLSearchParams()),
}));

// Every element Tab stops on, from the top of the page until the focus leaves it.
async function tabStops(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement[]> {
  const stops: HTMLElement[] = [];
  for (let presses = 0; presses < 30; presses++) {
    await user.tab();
    const focused = document.activeElement as HTMLElement;
    if (focused === document.body || stops.includes(focused)) break;
    stops.push(focused);
  }
  return stops;
}

async function tabTo(user: ReturnType<typeof userEvent.setup>, element: HTMLElement) {
  for (let presses = 0; presses < 30 && document.activeElement !== element; presses++) {
    await user.tab();
  }
  expect(element).toHaveFocus();
}

const takenOutOfTheTabOrder = (container: HTMLElement) =>
  [...container.querySelectorAll('a[tabindex="-1"], button[tabindex="-1"], input[tabindex="-1"]')].map(
    element => element.getAttribute("aria-label") || element.textContent
  );

describe("sign-in with the keyboard (#837)", () => {
  it("stops on Forgot password? and on the show-password button", async () => {
    const user = userEvent.setup();
    render(<SignInPage />);

    const stops = await tabStops(user);

    expect(stops).toContain(screen.getByRole("link", { name: "Forgot password?" }));
    expect(stops).toContain(screen.getByRole("button", { name: "Show password" }));
  });

  it("shows and hides the password from the keyboard", async () => {
    const user = userEvent.setup();
    render(<SignInPage />);
    const password = screen.getByLabelText(/^password$/i);
    await tabTo(user, screen.getByRole("button", { name: "Show password" }));

    await user.keyboard("{Enter}");
    expect(password).toHaveAttribute("type", "text");

    await user.keyboard(" ");
    expect(password).toHaveAttribute("type", "password");
  });

  it("takes no link, button or field out of the tab order", () => {
    const { container } = render(<SignInPage />);

    expect(takenOutOfTheTabOrder(container)).toEqual([]);
  });

  it("has no axe violations", async () => {
    const { container } = render(<SignInPage />);

    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("sign-up with the keyboard (#837)", () => {
  it("stops on both show-password buttons", async () => {
    const user = userEvent.setup();
    render(<SignUpPage />);

    const stops = await tabStops(user);

    const toggles = screen.getAllByRole("button", { name: "Show password" });
    expect(toggles).toHaveLength(2);
    toggles.forEach(toggle => expect(stops).toContain(toggle));
  });

  it("shows each password from the keyboard", async () => {
    const user = userEvent.setup();
    render(<SignUpPage />);
    const [first, second] = screen.getAllByRole("button", { name: "Show password" });

    await tabTo(user, first);
    await user.keyboard("{Enter}");
    expect(screen.getByLabelText(/^password$/i)).toHaveAttribute("type", "text");
    expect(screen.getByLabelText(/confirm password/i)).toHaveAttribute("type", "password");

    await tabTo(user, second);
    await user.keyboard("{Enter}");
    expect(screen.getByLabelText(/confirm password/i)).toHaveAttribute("type", "text");
  });

  it("takes no link, button or field out of the tab order", () => {
    const { container } = render(<SignUpPage />);

    expect(takenOutOfTheTabOrder(container)).toEqual([]);
  });

  it("has no axe violations", async () => {
    const { container } = render(<SignUpPage />);

    expect(await axe(container)).toHaveNoViolations();
  });
});
