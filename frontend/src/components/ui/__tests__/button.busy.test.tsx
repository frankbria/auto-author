import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import { Button } from '../button';

/**
 * `<Button busy>` (#642).
 *
 * `busy-button-contrast.test.ts` measures the colours and sweeps the call sites;
 * this covers the behaviour those two assume — that `busy` actually reaches the
 * DOM, actually cancels `disabled:opacity-50`, and actually still blocks the
 * click. A guard that measures a class name nothing renders proves nothing.
 */
describe('Button busy state (#642)', () => {
  it('marks itself busy and disabled without an explicit disabled prop', () => {
    render(<Button busy>Saving...</Button>);
    const button = screen.getByRole('button', { name: 'Saving...' });

    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveAttribute('data-busy', 'true');
    expect(button).toBeDisabled();
  });

  it('cancels the greyed-out treatment that makes the label unreadable', () => {
    render(<Button busy>Saving...</Button>);
    const className = screen.getByRole('button').className;

    // The whole point: the label must not be flattened to 2.29:1 while it is
    // the only signal the action is running.
    expect(className).not.toMatch(/(^|\s|:)disabled:opacity-50(\s|$)/);
    expect(className).toMatch(/disabled:opacity-100(\s|$)/);
  });

  it('still refuses the click', async () => {
    const onClick = jest.fn();
    render(
      <Button busy onClick={onClick}>
        Saving...
      </Button>
    );

    await userEvent.click(screen.getByRole('button')).catch(() => {
      // userEvent refuses to click a pointer-events-none element; either way the
      // handler must not fire.
    });
    expect(onClick).not.toHaveBeenCalled();
  });

  it('leaves an ordinary disabled button exactly as it was', () => {
    render(<Button disabled>Unavailable</Button>);
    const button = screen.getByRole('button');

    expect(button).toBeDisabled();
    expect(button).not.toHaveAttribute('aria-busy');
    expect(button).not.toHaveAttribute('data-busy');
    // The greyed affordance is correct here — WCAG 1.4.3 exempts inactive
    // components, and #642 deliberately does not change this state.
    expect(button.className).toMatch(/disabled:opacity-50(\s|$)/);
  });

  it('lets an explicit disabled prop win over the implication', () => {
    // A button that is busy *and* would be disabled anyway must stay disabled;
    // one explicitly enabled stays clickable, which is how a call site keeps a
    // cancel affordance live while work runs.
    render(
      <Button busy disabled={false}>
        Saving...
      </Button>
    );
    expect(screen.getByRole('button')).toBeEnabled();
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });

  it('makes a non-button child inert without the disabled attribute', () => {
    // `asChild` renders someone else's element — an anchor has no `disabled`
    // attribute, and React would warn about an unknown prop on a DOM node.
    //
    // The first cut stopped there, and the pre-PR reviewer caught what that
    // leaves: every class in BUSY_CLASSES is `disabled:`-prefixed, so with no
    // `disabled` attribute **none of them applies** and the "busy" link stayed
    // fully clickable — the opposite of the contract this prop advertises.
    render(
      <Button asChild busy>
        <a href="/somewhere">Saving...</a>
      </Button>
    );
    const link = screen.getByRole('link', { name: 'Saving...' });

    expect(link).not.toHaveAttribute('disabled');
    expect(link).toHaveAttribute('aria-busy', 'true');
    expect(link).toHaveAttribute('aria-disabled', 'true');
    // Unprefixed, because there is no `disabled:` state to hang them on.
    expect(link.className).toMatch(/(^|\s)pointer-events-none(\s|$)/);
  });

  it('leaves an explicitly-enabled asChild button interactive', () => {
    render(
      <Button asChild busy disabled={false}>
        <a href="/somewhere">Saving...</a>
      </Button>
    );
    const link = screen.getByRole('link', { name: 'Saving...' });

    expect(link).toHaveAttribute('aria-busy', 'true');
    expect(link).not.toHaveAttribute('aria-disabled');
  });
});
