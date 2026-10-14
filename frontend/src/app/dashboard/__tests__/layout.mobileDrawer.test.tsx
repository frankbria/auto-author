/**
 * #837: the dashboard's mobile menu, with a keyboard and nothing else.
 *
 * The drawer was two `div`s: no dialog role, no name, nothing to keep the
 * focus inside it, nothing on Escape, and a toggle that did not say whether
 * the menu was open. It is now the Radix sheet the chapter tabs already use.
 *
 * jsdom applies no stylesheet, so the toggle is rendered at any width.
 * No test here clicks.
 */
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import DashboardLayout from '../layout';

expect.extend(toHaveNoViolations);

jest.mock('next/navigation', () => ({ usePathname: () => '/dashboard' }));
jest.mock('@/components/auth/ProtectedRoute', () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock('@/components/ui/user-button', () => ({ UserButton: () => null }));
// A link that goes nowhere: jsdom cannot navigate, and what is tested is that choosing one closes the menu.
jest.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, onClick, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a
      href={href}
      onClick={event => {
        event.preventDefault();
        onClick?.(event);
      }}
      {...rest}
    >
      {children}
    </a>
  ),
}));

// Once the menu is open the rest of the page is hidden from assistive technology, the toggle with it,
// and a hidden element has no accessible name to be found by: it is found by its label attribute.
const toggle = () => document.querySelector('button[aria-label="Toggle mobile menu"]') as HTMLElement;

async function openWithTheKeyboard() {
  const user = userEvent.setup();
  render(
    <DashboardLayout>
      <p>The page</p>
    </DashboardLayout>
  );
  for (let presses = 0; presses < 20 && document.activeElement !== toggle(); presses++) {
    await user.tab();
  }
  expect(toggle()).toHaveFocus();
  await user.keyboard('{Enter}');
  return { user, menu: await screen.findByRole('dialog', { name: 'Menu' }) };
}

describe('the mobile menu with the keyboard (#837)', () => {
  it('has a toggle that says the menu is closed', () => {
    render(
      <DashboardLayout>
        <p>The page</p>
      </DashboardLayout>
    );

    expect(screen.getByRole('button', { name: 'Toggle mobile menu' })).toBe(toggle());
    expect(toggle()).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('opens as a dialog named Menu, with the focus inside it and the toggle saying so', async () => {
    const { menu } = await openWithTheKeyboard();

    expect(menu).toContainElement(document.activeElement as HTMLElement);
    expect(toggle()).toHaveAttribute('aria-expanded', 'true');
    // Modal: what is behind the menu is hidden from assistive technology, so a screen reader cannot wander out of it.
    expect(screen.queryByRole('button', { name: 'Toggle mobile menu' })).not.toBeInTheDocument();
    expect(screen.queryByText('The page')?.closest('[aria-hidden="true"]')).not.toBeNull();
    expect(within(menu).getAllByRole('link').map(link => link.textContent)).toEqual(['Dashboard', 'Settings', 'Help']);
  });

  it('keeps the focus inside while Tab is pressed, forwards and back', async () => {
    const { user, menu } = await openWithTheKeyboard();

    for (let presses = 0; presses < 8; presses++) {
      await user.tab();
      expect(menu).toContainElement(document.activeElement as HTMLElement);
    }
    for (let presses = 0; presses < 8; presses++) {
      await user.tab({ shift: true });
      expect(menu).toContainElement(document.activeElement as HTMLElement);
    }
  });

  it('closes on Escape and gives the focus back to the toggle', async () => {
    const { user } = await openWithTheKeyboard();

    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(toggle()).toHaveFocus();
    expect(toggle()).toHaveAttribute('aria-expanded', 'false');
  });

  it('closes when a link in it is chosen', async () => {
    const { user, menu } = await openWithTheKeyboard();
    const settings = within(menu).getByRole('link', { name: 'Settings' });
    for (let presses = 0; presses < 8 && document.activeElement !== settings; presses++) {
      await user.tab();
    }
    expect(settings).toHaveFocus();

    await user.keyboard('{Enter}');

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('keeps a 44-pixel touch area on its close button, as the old one had', async () => {
    const { menu } = await openWithTheKeyboard();

    // jsdom does no layout: the class is what can be seen here, and the demo measures it in a browser.
    // A 16-pixel icon and 14 pixels on every side.
    expect(within(menu).getByRole('button', { name: 'Close' }).className).toContain("max-md:before:inset-[-14px]");
  });

  it('has no axe violations when open', async () => {
    await openWithTheKeyboard();

    expect(await axe(document.body)).toHaveNoViolations();
  });
});
