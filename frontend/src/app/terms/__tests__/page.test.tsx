import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import TermsPage from '@/app/terms/page';
import { TERMS_VERSION } from '@/lib/constants/legal';

describe('Terms of Service page', () => {
  it('renders the Terms of Service heading', () => {
    render(<TermsPage />);
    expect(
      screen.getByRole('heading', { level: 1, name: /terms of service/i })
    ).toBeInTheDocument();
  });

  it('carries a visible legal-review notice (template copy, not lawyer-reviewed)', () => {
    render(<TermsPage />);
    expect(screen.getByText(/legal review/i)).toBeInTheDocument();
  });

  it('section 6 states auto-renewal and how to cancel (#770)', () => {
    render(<TermsPage />);
    const section = screen
      .getByRole('heading', { level: 2, name: /payment and subscriptions/i })
      .closest('section');
    expect(section).toHaveTextContent(/renew automatically .* until you cancel/i);
    expect(section).toHaveTextContent(/settings → billing → manage billing/i);
    expect(section).toHaveTextContent(/end of the current billing period/i);
  });

  it('section 6 states that prices exclude tax and tax is shown before payment (#783)', () => {
    render(<TermsPage />);
    const section = screen
      .getByRole('heading', { level: 2, name: /payment and subscriptions/i })
      .closest('section');
    expect(section).toHaveTextContent(/prices exclude tax/i);
    expect(section).toHaveTextContent(/based on your billing address/i);
    expect(section).toHaveTextContent(/shown at checkout before you pay/i);
  });

  it('section 7 says deleting deactivates the account and keeps its record 18 months (#954)', () => {
    render(<TermsPage />);
    const section = screen
      .getByRole('heading', { level: 2, name: /termination/i })
      .closest('section');
    expect(section).toHaveTextContent(/deletes your books/i);
    expect(section).toHaveTextContent(/deactivates the account/i);
    expect(section).toHaveTextContent(/for 18 months/i);
    expect(section).toHaveTextContent(/cancels a paid subscription immediately/i);
  });

  // #789: sign-up records TERMS_VERSION, so the date shown here must be it.
  it('shows the recorded Terms version as its last-updated date', () => {
    render(<TermsPage />);
    const shown = screen.getByText(/last updated:/i).textContent!.replace(/last updated:\s*/i, '');
    expect(new Date(`${shown} UTC`).toISOString().slice(0, 10)).toBe(TERMS_VERSION);
  });

  it('provides the #main-content landmark (skip-link target)', () => {
    const { container } = render(<TermsPage />);
    expect(container.querySelector('main#main-content')).toBeInTheDocument();
  });
});
