import Link from 'next/link';

// Public-surface footer carrying the legally-required policy links (#335).
// Plain component (no hooks) so it drops into both server and client pages.
export default function SiteFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="w-full border-t border-border py-6 text-sm text-muted-foreground">
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-3 px-4 sm:flex-row sm:justify-between">
        <p>© {year} Noatak Enterprises, LLC, dba Bria Strategy Group</p>
        <nav aria-label="Legal" className="flex gap-4">
          <Link href="/terms" className="hover:text-foreground hover:underline">
            Terms of Service
          </Link>
          <Link href="/privacy" className="hover:text-foreground hover:underline">
            Privacy Policy
          </Link>
        </nav>
      </div>
    </footer>
  );
}
