import type { Metadata } from 'next';
import Link from 'next/link';
import SiteFooter from '@/components/SiteFooter';
import MarketingHeader from '@/components/marketing/MarketingHeader';
import PricingPlans from '@/components/marketing/PricingPlans';
import Analytics from '@/components/marketing/Analytics';

export const metadata: Metadata = {
  title: 'Pricing | Auto Author',
  description:
    'Try Auto Author on one chapter, free. Pro is a monthly subscription for the whole book, with export to PDF, DOCX, EPUB and Markdown.',
};

// Public pricing page. The numbers on the cards come from GET /billing/plans
// (the same settings and Stripe price the app enforces and charges); the copy
// follows the positioning adopted on 2026-10-28. No yearly plan, by decision.
export default function PricingPage() {
  return (
    <>
      <MarketingHeader />
      <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 py-12">
        <div className="mx-auto mb-10 max-w-2xl space-y-3 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">Pricing</h1>
          <p className="text-muted-foreground">
            Try Auto Author on one chapter, free. When you&apos;re ready to write the whole book, Pro is
            one monthly price. Cancel when the book is done.
          </p>
        </div>

        <PricingPlans />
        <p className="mt-4 text-center text-sm text-muted-foreground">
          Prices exclude any sales tax, VAT or GST, which is shown at checkout.
        </p>

        <section aria-labelledby="pricing-questions" className="mx-auto mt-14 max-w-2xl space-y-6">
          <h2 id="pricing-questions" className="text-2xl font-semibold text-foreground">
            Questions
          </h2>
          <div className="space-y-2">
            <h3 className="font-semibold text-foreground">What does the free trial let me do?</h3>
            <p className="text-muted-foreground">
              Everything up to one finished chapter draft: describe your book, get and edit a table of
              contents, answer one chapter&apos;s interview questions and have Auto Author draft it. It is a
              way to see whether the drafts work on your own material. It can&apos;t produce a whole book,
              and exporting needs Pro.
            </p>
          </div>
          <div className="space-y-2">
            <h3 className="font-semibold text-foreground">What counts as an AI generation?</h3>
            <p className="text-muted-foreground">
              Each time Auto Author&apos;s AI does something for you: suggesting questions, proposing a
              table of contents, drafting a chapter or changing the style of a passage.
            </p>
          </div>
          <div className="space-y-2">
            <h3 className="font-semibold text-foreground">Can I cancel?</h3>
            <p className="text-muted-foreground">
              Yes, anytime, online under Settings → Billing. Cancelling stops future renewals, and you keep
              Pro until the end of the period you&apos;ve paid for. Your manuscript stays yours either way: you
              keep ownership of what you write and of the drafts made from it, as our{' '}
              <Link href="/terms" className="text-primary underline-offset-4 hover:underline">
                Terms of Service
              </Link>{' '}
              set out.
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
      <Analytics />
    </>
  );
}
