import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import PrivacyPage from '@/app/privacy/page';

describe('Privacy Policy page', () => {
  it('renders the Privacy Policy heading', () => {
    render(<PrivacyPage />);
    expect(
      screen.getByRole('heading', { level: 1, name: /privacy policy/i })
    ).toBeInTheDocument();
  });

  it('documents the account-deletion / cascade-delete path (#179) via the profile page', () => {
    render(<PrivacyPage />);
    // Must tell users how to delete their data and that it cascades to books.
    expect(screen.getByText(/delete your account/i)).toBeInTheDocument();
    const profileLink = screen.getByRole('link', { name: /profile/i });
    expect(profileLink).toHaveAttribute('href', '/profile');
  });

  it('gives a contact address for data requests', () => {
    render(<PrivacyPage />);
    expect(
      screen.getByRole('link', { name: /support@autoauthor\.com/i })
    ).toHaveAttribute('href', 'mailto:support@autoauthor.com');
  });

  it('carries a visible legal-review notice', () => {
    render(<PrivacyPage />);
    expect(screen.getByText(/legal review/i)).toBeInTheDocument();
  });

  it('provides the #main-content landmark (skip-link target)', () => {
    const { container } = render(<PrivacyPage />);
    expect(container.querySelector('main#main-content')).toBeInTheDocument();
  });
});
