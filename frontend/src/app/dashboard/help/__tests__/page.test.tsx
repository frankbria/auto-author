import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import HelpPage from '../page';

describe('HelpPage', () => {
  it('renders the support email as a mailto: link (#215)', () => {
    render(<HelpPage />);
    const link = screen.getByRole('link', { name: 'support@autoauthor.com' });
    expect(link).toHaveAttribute('href', 'mailto:support@autoauthor.com');
  });
});
