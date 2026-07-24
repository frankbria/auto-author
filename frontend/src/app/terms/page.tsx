import Link from 'next/link';
import SiteFooter from '@/components/SiteFooter';

export const metadata = {
  title: 'Terms of Service · Auto Author',
  description: 'The terms governing your use of Auto Author.',
};

// #335: template Terms of Service. Copy is a starting point — flag for legal
// review before public launch. Static server component; owns its own
// <main id="main-content"> so the layout skip-link resolves here.
const LAST_UPDATED = 'July 23, 2026';

export default function TermsPage() {
  return (
    <>
      <main
        id="main-content"
        tabIndex={-1}
        className="container mx-auto max-w-4xl px-4 py-10"
      >
        <div className="mb-6">
          <Link
            href="/"
            className="text-sm text-primary underline-offset-4 hover:underline"
          >
            ← Back to Auto Author
          </Link>
        </div>

        <h1 className="mb-2 text-3xl font-bold">Terms of Service</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Last updated: {LAST_UPDATED}
        </p>

        <div
          role="note"
          className="mb-8 rounded-md border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-300"
        >
          These terms are provided as a template and have not yet been finalized
          by counsel. They are pending legal review and may change before
          general availability.
        </div>

        <div className="space-y-6 text-muted-foreground">
          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              1. Acceptance of Terms
            </h2>
            <p>
              By creating an account or using Auto Author (the &ldquo;Service&rdquo;),
              you agree to be bound by these Terms of Service. If you do not agree,
              do not use the Service. The Service is operated by Noatak
              Enterprises, LLC, dba Bria Strategy Group (&ldquo;we&rdquo;,
              &ldquo;us&rdquo;).
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              2. Description of the Service
            </h2>
            <p>
              Auto Author is an AI-assisted platform that helps you draft
              nonfiction books through guided interviews, table-of-contents
              generation, and AI draft generation. Features may change, and we
              may add or remove functionality over time.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              3. Accounts and Eligibility
            </h2>
            <p>
              You must provide accurate registration information and are
              responsible for maintaining the confidentiality of your
              credentials and for all activity under your account. You must be of
              legal age to form a binding contract to use the Service.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              4. Acceptable Use
            </h2>
            <p>
              You agree not to misuse the Service, including by attempting to
              disrupt it, access it without authorization, or use it to generate
              unlawful, infringing, or harmful content. We may suspend or
              terminate accounts that violate these terms.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              5. Your Content and AI Output
            </h2>
            <p>
              You retain ownership of the content you submit and, as between you
              and us, of the drafts the Service generates from your inputs. You
              are responsible for reviewing AI-generated output for accuracy and
              suitability before relying on or publishing it. The Service is
              provided as a writing aid, not as professional advice.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              6. Payment and Subscriptions
            </h2>
            <p>
              Paid plans, where offered, are billed through our payment processor.
              Fees, billing cycles, and cancellation terms are presented at the
              point of purchase. Except where required by law, fees are
              non-refundable.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              7. Termination
            </h2>
            <p>
              You may stop using the Service and delete your account at any time
              from your{' '}
              <Link
                href="/profile"
                className="text-primary underline-offset-4 hover:underline"
              >
                profile page
              </Link>
              . We may suspend or terminate access for violations of these terms.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              8. Disclaimers and Limitation of Liability
            </h2>
            <p>
              The Service is provided &ldquo;as is&rdquo; without warranties of
              any kind. To the maximum extent permitted by law, we are not liable
              for indirect, incidental, or consequential damages arising from your
              use of the Service.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              9. Changes to These Terms
            </h2>
            <p>
              We may update these terms from time to time. Material changes will
              be reflected by updating the &ldquo;Last updated&rdquo; date above,
              and continued use of the Service constitutes acceptance of the
              revised terms.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              10. Contact
            </h2>
            <p>
              Questions about these terms? Contact us at{' '}
              <a
                href="mailto:support@autoauthor.com"
                className="text-primary underline-offset-4 hover:underline"
              >
                support@autoauthor.com
              </a>
              . See also our{' '}
              <Link
                href="/privacy"
                className="text-primary underline-offset-4 hover:underline"
              >
                Privacy Policy
              </Link>
              .
            </p>
          </section>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
