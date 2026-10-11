import { SUPPORT_EMAIL, SUPPORT_MAILTO } from '@/lib/constants/contact';
import { SUBPROCESSORS } from '@/lib/constants/subprocessors';
import { render, screen, within } from '@testing-library/react';
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
      screen.getByRole('link', { name: SUPPORT_EMAIL })
    ).toHaveAttribute('href', SUPPORT_MAILTO);
  });

  it('carries a visible legal-review notice', () => {
    render(<PrivacyPage />);
    expect(screen.getByText(/legal review/i)).toBeInTheDocument();
  });

  it('provides the #main-content landmark (skip-link target)', () => {
    const { container } = render(<PrivacyPage />);
    expect(container.querySelector('main#main-content')).toBeInTheDocument();
  });

  it('states the 90-day audit log retention and the renewal-consent exception (#787)', () => {
    render(<PrivacyPage />);
    expect(screen.getByText(/audit log.*90 days/i)).toBeInTheDocument();
    expect(screen.getByText(/automatic-renewal terms/i)).toBeInTheDocument();
  });

  it('names every subprocessor in a table row with its purpose and data (#788)', () => {
    render(<PrivacyPage />);
    const table = screen.getByRole('table', { name: /subprocessors/i });
    expect(within(table).getAllByRole('row')).toHaveLength(SUBPROCESSORS.length + 1);
    for (const s of SUBPROCESSORS) {
      const row = within(table).getByRole('rowheader', { name: s.name }).closest('tr')!;
      expect(within(row).getByText(s.purpose)).toBeInTheDocument();
      expect(within(row).getByText(s.data)).toBeInTheDocument();
    }
  });

  it.each([
    /lawful bas/i,
    /international transfers/i,
    /training/i,
    /cookies and local storage/i,
    /children/i,
    /your rights/i,
  ])('has a section headed %s (#788)', (name) => {
    render(<PrivacyPage />);
    expect(screen.getByRole('heading', { level: 2, name })).toBeInTheDocument();
  });

  it('lists the objection, restriction and complaint rights (#788)', () => {
    render(<PrivacyPage />);
    const rights = screen.getByRole('list', { name: /your rights/i });
    for (const right of [/access/i, /correct/i, /delete/i, /restrict/i, /object/i, /complain/i]) {
      expect(within(rights).getByText(right)).toBeInTheDocument();
    }
  });

  const section = (name: RegExp) =>
    screen.getByRole('heading', { level: 2, name }).closest('section');

  it('says deletion deactivates the account and keeps its record for 18 months (#954)', () => {
    render(<PrivacyPage />);
    const retention = section(/data retention and deletion/i);
    expect(retention).toHaveTextContent(/deactivated/i);
    expect(retention).toHaveTextContent(/for 18 months/i);
    expect(retention).toHaveTextContent(/erased automatically/i);
    expect(retention).toHaveTextContent(/erase it sooner/i);
    expect(retention).not.toHaveTextContent(/permanent|cannot be undone/i);
    expect(section(/lawful bas/i)).toHaveTextContent(/complaints and payment disputes/i);
    expect(section(/your rights/i)).toHaveTextContent(/erased sooner/i);
  });

  it('says billing records stay with the payment processor after deletion (#784)', () => {
    render(<PrivacyPage />);
    expect(screen.getByText(/records of past payments.*stay with our payment processor/i)).toBeInTheDocument();
  });

  it('says content is not used to train AI models (#788)', () => {
    render(<PrivacyPage />);
    expect(screen.getByText(/do not use your content to train/i)).toBeInTheDocument();
  });
});
