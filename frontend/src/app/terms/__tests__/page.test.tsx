import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import TermsPage from '@/app/terms/page';

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

  it('provides the #main-content landmark (skip-link target)', () => {
    const { container } = render(<TermsPage />);
    expect(container.querySelector('main#main-content')).toBeInTheDocument();
  });
});
