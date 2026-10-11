import Link from 'next/link';
import SiteFooter from '@/components/SiteFooter';
import { SUPPORT_EMAIL, SUPPORT_MAILTO } from '@/lib/constants/contact';
import { SUBPROCESSORS } from '@/lib/constants/subprocessors';

export const metadata = {
  title: 'Privacy Policy · Auto Author',
  description: 'How Auto Author collects, uses, and protects your data.',
};

// #335: template Privacy Policy. Copy is a starting point — flag for legal
// review before public launch. References the account-deletion / cascade-delete
// path (#179) and the 18-month deactivated record (#954): deleting your account
// deletes your books at once and keeps the account and billing record.
const LAST_UPDATED = 'October 11, 2026';

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
                and profile details you provide, and a record of which version
                of our Terms of Service you accepted and when.
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
              3. How We Use Your Information and Our Lawful Bases
            </h2>
            <p>
              We use your information to provide and improve the Service,
              authenticate you, generate AI drafts from your inputs, process
              payments, and communicate with you about your account. We do not
              sell your personal data.
            </p>
            <p className="mt-3">
              Where data-protection law requires a lawful basis, we rely on:
            </p>
            <ul className="mt-2 list-inside list-disc space-y-1">
              <li>
                <strong>Contract</strong> — to run your account, store your
                content, provide the AI features you invoke, and take payment
                for a paid plan.
              </li>
              <li>
                <strong>Legitimate interests</strong> — to keep the Service
                secure, prevent abuse, keep the audit log described below,
                diagnose errors, and handle complaints and payment disputes
                after an account is closed (section 8).
              </li>
              <li>
                <strong>Legal obligation</strong> — to keep billing and tax
                records and the record of your agreement to automatic renewal.
              </li>
              <li>
                <strong>Consent</strong> — for voice input, which uses your
                microphone only after you allow it in your browser. You can
                withdraw consent at any time by revoking that permission.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              4. AI Processing and Training Use
            </h2>
            <p>
              To generate tables of contents, questions, and drafts, the content
              you submit is sent to our AI provider for processing on your behalf.
              Review AI-generated output for accuracy before relying on it.
            </p>
            <p className="mt-3">
              We do not use your content to train AI models. Our AI provider
              receives it through its API only to produce the output you asked
              for; under its API terms, content submitted that way is not used
              to train its models by default. The provider may keep it for a
              limited period to monitor for abuse, as described in its own
              policies.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              5. Who We Share Your Data With
            </h2>
            <p>
              We share personal data only with the service providers
              (subprocessors) below, and only as far as each needs it to do its
              job. Where two providers are listed for the same purpose, one is
              in use at a time.
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <caption className="sr-only">Subprocessors</caption>
                <thead>
                  <tr className="border-b border-border text-foreground">
                    <th scope="col" className="py-2 pr-4 font-semibold">
                      Provider
                    </th>
                    <th scope="col" className="py-2 pr-4 font-semibold">
                      Purpose
                    </th>
                    <th scope="col" className="py-2 font-semibold">
                      Data it receives
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {SUBPROCESSORS.map(({ name, purpose, data }) => (
                    <tr key={name} className="border-b border-border align-top">
                      <th
                        scope="row"
                        className="py-2 pr-4 font-medium text-foreground"
                      >
                        {name}
                      </th>
                      <td className="py-2 pr-4">{purpose}</td>
                      <td className="py-2">{data}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              6. International Transfers
            </h2>
            <p>
              We are based in the United States, and the providers listed above
              process data in the United States and in other countries where
              they operate. If you use the Service from elsewhere, your data is
              transferred to and processed in those countries, whose
              data-protection laws may differ from yours. Where the law
              requires a safeguard for such a transfer (for example from the
              EEA, the United Kingdom or Switzerland), we rely on the Standard
              Contractual Clauses or an equivalent mechanism in our
              providers&rsquo; data processing terms.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              7. Cookies and Local Storage
            </h2>
            <p>
              We use only cookies that are strictly necessary: the cookies our
              sign-in system sets to keep you signed in (a session cookie and
              short-lived companions that cache your session) and, if you
              choose to trust a device during two-factor sign-in, a cookie that
              remembers that device. We do not use advertising or analytics
              cookies.
            </p>
            <p className="mt-3">
              The Service also keeps some data in your browser&rsquo;s local
              and session storage: your theme, which chapter tabs and views you
              have open, and backup copies of text you are editing (chapter
              text and book summaries) so that work is not lost if a save
              fails. Local storage stays on your device until you clear it in
              your browser settings, and session storage until you close the
              tab; signing out removes neither.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              8. Data Retention and Deletion
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
              (Delete Account). Deleting your account{' '}
              <strong>
                deletes all of your books and their associated content at once —
                chapters, questions, responses, and ratings
              </strong>
              , along with your profile picture, bio and preferences. They
              cannot be recovered. It also signs you out on every device and
              removes your password and other sign-in details, so the account
              can no longer be used.
            </p>
            <p className="mt-3">
              The account itself is deactivated rather than erased at once. We
              keep a record of it for 18 months so that we can answer a
              complaint or a payment dispute: an internal account identifier,
              your name, your email address, the dates the account was created
              and deleted, which version of our Terms of Service you accepted
              and when, your plan, the reference that links the account to
              our payment processor, and the reference, plan and status of any
              subscription that was cancelled when you deleted the account.
              After 18 months the record is erased automatically, down to the
              account identifier and the date of deletion. You can ask us to
              erase it sooner by
              contacting us using the details below. You can sign up again with
              the same email address at any time; a new account is not connected
              to the old record.
            </p>
            <p className="mt-3">
              Deleting your account also cancels any active subscription.
              Records of past payments (invoices, and the email address, billing
              address and any tax ID attached to them) stay with our payment
              processor, which keeps them to meet its own legal obligations.
            </p>
            <p className="mt-3">
              We keep an audit log of actions taken on your account (for example
              creating, updating or deleting a book), which can include the IP
              address and browser user-agent of the request. Audit log entries are deleted
              automatically 90 days after they are written; deleting your account
              does not remove them sooner. The one exception is the record of your
              agreement to the automatic-renewal terms when you subscribe, which we
              keep for as long as we need to demonstrate that agreement.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              9. Your Rights
            </h2>
            <p>
              Depending on your jurisdiction (for example, under GDPR or CCPA),
              you may have the right to:
            </p>
            <ul
              aria-label="Your rights"
              className="mt-2 list-inside list-disc space-y-1"
            >
              <li>access the personal data we hold about you;</li>
              <li>correct data that is inaccurate or incomplete;</li>
              <li>delete your data;</li>
              <li>receive a copy of your data in a portable format;</li>
              <li>restrict how we process your data;</li>
              <li>
                object to processing that we base on our legitimate interests;
              </li>
              <li>withdraw consent where we rely on it; and</li>
              <li>
                complain to the data-protection authority where you live or
                work.
              </li>
            </ul>
            <p className="mt-3">
              You can download a copy of your profile, your books and the
              questions, answers and ratings in them as a JSON file (Download
              my data), delete your content and close your account directly
              from your profile page. The download does not include uploaded
              images, activity and security logs, or payment records held by
              our payment processor. To get those, to have the account record
              we keep for 18 months (section 8) erased sooner, or for any other
              request, contact us using the details below. We do not
              charge for a request and will not treat you differently for
              making one.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              10. Children
            </h2>
            <p>
              The Service is not directed to children under 16, and we do not
              knowingly collect personal data from them. If you believe a child
              has given us personal data, contact us and we will delete it.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              11. Security
            </h2>
            <p>
              We use reasonable technical and organizational measures to protect
              your data. No method of transmission or storage is completely
              secure, so we cannot guarantee absolute security.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              12. Changes to This Policy
            </h2>
            <p>
              We may update this policy from time to time. Material changes will
              be reflected by updating the &ldquo;Last updated&rdquo; date above.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-xl font-semibold text-foreground">
              13. Contact
            </h2>
            <p>
              For privacy questions or data requests, contact us at{' '}
              <a
                href={SUPPORT_MAILTO}
                className="text-primary underline-offset-4 hover:underline"
              >
                {SUPPORT_EMAIL}
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
