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

  it('provides the #main-content landmark (skip-link target)', () => {
    const { container } = render(<TermsPage />);
    expect(container.querySelector('main#main-content')).toBeInTheDocument();
  });
});
