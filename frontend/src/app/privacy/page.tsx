import Link from 'next/link';
import SiteFooter from '@/components/SiteFooter';

export const metadata = {
  title: 'Privacy Policy · Auto Author',
  description: 'How Auto Author collects, uses, and protects your data.',
};

// #335: template Privacy Policy. Copy is a starting point — flag for legal
// review before public launch. References the account-deletion / cascade-delete
// path (#179): deleting your account permanently removes it and all your books.
const LAST_UPDATED = 'July 23, 2026';

export default function PrivacyPage() {
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

        <h1 className="mb-2 text-3xl font-bold">Privacy Policy</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Last updated: {LAST_UPDATED}
        </p>

        <div
          role="note"
          className="mb-8 rounded-md border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-300"
        >
          This policy is provided as a template and has not yet been finalized by
          counsel. It is pending legal review and may change before general
          availability.
        </div>

        <div className="space-y-6 text-muted-foreground">
          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              1. Who We Are
            </h2>
            <p>
              Auto Author is operated by Noatak Enterprises, LLC, dba Bria
              Strategy Group. This policy explains what personal data the Service
              collects, how we use it, and the choices you have.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              2. Information We Collect
            </h2>
            <ul className="list-inside list-disc space-y-1">
              <li>
                <strong>Account information</strong> — your name, email address,
                and profile details you provide.
              </li>
              <li>
                <strong>Your content</strong> — book summaries, interview answers,
                chapter drafts, and other material you create in the Service.
              </li>
              <li>
                <strong>Billing information</strong> — where you subscribe to a
                paid plan, payment details are handled by our payment processor;
                we do not store full card numbers.
              </li>
              <li>
                <strong>Usage data</strong> — basic technical and diagnostic
                information needed to operate and secure the Service.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              3. How We Use Your Information
            </h2>
            <p>
              We use your information to provide and improve the Service,
              authenticate you, generate AI drafts from your inputs, process
              payments, and communicate with you about your account. We do not
              sell your personal data.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              4. AI Processing
            </h2>
            <p>
              To generate tables of contents, questions, and drafts, the content
              you submit is sent to our AI provider for processing on your behalf.
              Review AI-generated output for accuracy before relying on it.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              5. Data Retention and Deletion
            </h2>
            <p>
              We retain your data for as long as your account is active. You can
              delete your account at any time from your{' '}
              <Link
                href="/profile"
                className="text-primary underline-offset-4 hover:underline"
              >
                profile page
              </Link>{' '}
              (Delete Account). Deleting your account is permanent and{' '}
              <strong>
                cascades to all of your books and their associated content —
                chapters, questions, responses, and ratings are removed along with
                the account
              </strong>
              . This action cannot be undone.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              6. Your Rights
            </h2>
            <p>
              Depending on your jurisdiction (for example, under GDPR or CCPA),
              you may have rights to access, correct, export, or delete your
              personal data. You can exercise deletion directly from your profile
              page, or contact us for other requests using the details below.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              7. Security
            </h2>
            <p>
              We use reasonable technical and organizational measures to protect
              your data. No method of transmission or storage is completely
              secure, so we cannot guarantee absolute security.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              8. Changes to This Policy
            </h2>
            <p>
              We may update this policy from time to time. Material changes will
              be reflected by updating the &ldquo;Last updated&rdquo; date above.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              9. Contact
            </h2>
            <p>
              For privacy questions or data requests, contact us at{' '}
              <a
                href="mailto:support@autoauthor.com"
                className="text-primary underline-offset-4 hover:underline"
              >
                support@autoauthor.com
              </a>
              . See also our{' '}
              <Link
                href="/terms"
                className="text-primary underline-offset-4 hover:underline"
              >
                Terms of Service
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
