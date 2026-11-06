import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ExportProgressModal } from '../ExportProgressModal';

/**
 * Export is part of Pro; the free trial is one chapter (owner decision
 * 2026-10-28). A refused export says why and links to the upgrade: retrying
 * the same export cannot succeed.
 */
describe('ExportProgressModal after a plan refusal', () => {
  const reason = 'Exporting your book is part of Pro.';

  it('offers the upgrade, not a retry', () => {
    render(
      <ExportProgressModal
        isOpen
        status="failed"
        error={reason}
        upgradeRequired
        onCancel={jest.fn()}
        onClose={jest.fn()}
      />
    );

    expect(screen.getByText(reason)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Upgrade to Pro' })).toHaveAttribute(
      'href',
      '/dashboard/settings?tab=billing'
    );
    expect(screen.queryByRole('button', { name: 'Retry Export' })).not.toBeInTheDocument();
  });

  it('still offers a retry for any other failure', () => {
    render(
      <ExportProgressModal
        isOpen
        status="failed"
        error="The export timed out."
        onCancel={jest.fn()}
        onClose={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: 'Retry Export' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
  });
});
