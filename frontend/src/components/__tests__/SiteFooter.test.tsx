import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SiteFooter from '@/components/SiteFooter';

describe('SiteFooter', () => {
  it('links to the Terms of Service and Privacy Policy pages', () => {
    render(<SiteFooter />);

    const terms = screen.getByRole('link', { name: /terms of service/i });
    const privacy = screen.getByRole('link', { name: /privacy policy/i });

    expect(terms).toHaveAttribute('href', '/terms');
    expect(privacy).toHaveAttribute('href', '/privacy');
  });

  it('links to the notices for the third-party software the site is built with (#825)', () => {
    render(<SiteFooter />);

    // A file in public/, written at build time: not a page, so not a client-side route.
    expect(screen.getByRole('link', { name: /third-party notices/i })).toHaveAttribute('href', '/third-party-notices.txt');
  });

  it('renders inside a contentinfo landmark', () => {
    render(<SiteFooter />);
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });
});
