import { SUPPORT_EMAIL, SUPPORT_MAILTO } from '@/lib/constants/contact';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import HelpPage from '../page';

describe('HelpPage', () => {
  it('renders the support email as a mailto: link (#215)', () => {
    render(<HelpPage />);
    const link = screen.getByRole('link', { name: SUPPORT_EMAIL });
    expect(link).toHaveAttribute('href', SUPPORT_MAILTO);
  });
});
