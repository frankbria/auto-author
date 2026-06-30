// Single <main> landmark + skip-link target for every /auth/* route and all of
// their render/Suspense-fallback states, so the global "Skip to main content"
// link (app/layout.tsx) always resolves here. tabIndex={-1} lets focus move to
// it on activation in browsers that don't focus non-interactive fragment targets.
interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <main id="main-content" tabIndex={-1}>
      {children}
    </main>
  );
}
