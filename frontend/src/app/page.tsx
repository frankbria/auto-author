import type { Metadata } from 'next';
import Link from 'next/link';
import SiteFooter from '@/components/SiteFooter';
import MarketingHeader from '@/components/marketing/MarketingHeader';
import Analytics from '@/components/marketing/Analytics';

export const metadata: Metadata = {
  title: 'Auto Author: your book is already in your head',
  description:
    'Auto Author interviews you chapter by chapter and turns your answers into a book draft you edit and own.',
};

// The public landing page. Copy follows the positioning Frank adopted on
// 2026-10-28 (Dropbox /Ideation/Auto_Author/auto-author-positioning-pricing.md,
// sections 5 to 7). Every claim here is one the app backs; that doc's
// "Do not claim" list (voice cloning, a talking interviewer, publishing,
// human editing, speed or revenue promises, a "free plan") stays off this page,
// and src/__tests__/HomePage.test.tsx checks it.

const PROOF_POINTS = [
  {
    title: 'It interviews you',
    body: 'Questions for every chapter, not one prompt for the whole book.',
  },
  {
    title: 'Talk or type',
    body: 'Answer by typing or by speaking.',
  },
  {
    title: 'You stay in control',
    body: 'A real editor, and your manuscript exports as DOCX, EPUB, PDF or Markdown (on Pro).',
  },
];

const STEPS = [
  'Describe your book in a few paragraphs, typed or dictated.',
  'Answer a handful of questions Auto Author asks about the book as a whole.',
  'Get a proposed table of contents, and edit it until it is the book you mean.',
  'For each chapter, answer the interview questions Auto Author asks, by typing or speaking.',
  'Auto Author drafts the chapter from your answers, so the stories and examples are yours.',
  'Edit the draft in a full editor, with AI help to change the style of a passage.',
  'Export your manuscript as PDF, DOCX, EPUB or Markdown (Pro).',
];

const COMPARISONS = [
  {
    against: 'A general AI chat',
    body: 'Not a blank chat box. A book structure and an interview for every chapter, with drafts built from your answers.',
  },
  {
    against: 'One-shot AI book generators',
    body: 'They write a book about your topic from a few questions. Auto Author asks for every chapter, and drafts from what you said.',
  },
  {
    against: 'A ghostwriter',
    body: "The ghostwriter's interview process, at a self-serve price. You keep editorial control.",
  },
];

export default function Home() {
  return (
    <>
      <MarketingHeader />
      <main id="main-content" tabIndex={-1} className="w-full flex-1">
        <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:py-24">
          <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
            Your book is already in your head.{' '}
            <span className="text-primary">Auto Author asks the questions that get it out.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            You already know what your book should say. You say it to clients every week. Auto Author
            asks the right questions for each chapter, lets you answer by typing or talking, and drafts
            the chapter from what you said. Then you edit it in a real editor and export it as DOCX, EPUB
            or PDF.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/auth/sign-up"
              data-goatcounter-click="cta-hero-trial"
              className="rounded-md bg-primary px-6 py-3 font-semibold text-primary-foreground hover:bg-primary/90"
            >
              Try Auto Author on one chapter, free
            </Link>
            <Link
              href="/pricing"
              className="rounded-md border border-border px-6 py-3 font-semibold text-foreground hover:bg-accent"
            >
              See pricing
            </Link>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            For consultants, coaches and experts writing the book their work is built on.
          </p>
        </section>

        <section aria-labelledby="proof" className="border-t border-border bg-card">
          <div className="mx-auto max-w-5xl px-4 py-14">
            <h2 id="proof" className="sr-only">
              What makes it different
            </h2>
            <div className="grid gap-8 md:grid-cols-3">
              {PROOF_POINTS.map((p) => (
                <div key={p.title} className="space-y-2">
                  <h3 className="text-lg font-semibold text-card-foreground">{p.title}</h3>
                  <p className="text-muted-foreground">{p.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section aria-labelledby="how" className="mx-auto max-w-3xl px-4 py-14">
          <h2 id="how" className="text-2xl font-bold text-foreground">
            How it works
          </h2>
          <ol className="mt-6 space-y-4">
            {STEPS.map((step, i) => (
              <li key={step} className="flex gap-4">
                <span
                  aria-hidden="true"
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground"
                >
                  {i + 1}
                </span>
                <span className="pt-1 text-foreground">{step}</span>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="compare" className="border-t border-border bg-card">
          <div className="mx-auto max-w-5xl px-4 py-14">
            <h2 id="compare" className="text-2xl font-bold text-card-foreground">
              How it compares
            </h2>
            <dl className="mt-6 grid gap-8 md:grid-cols-3">
              {COMPARISONS.map((c) => (
                <div key={c.against} className="space-y-2">
                  <dt className="font-semibold text-card-foreground">Compared with {c.against.toLowerCase()}</dt>
                  <dd className="text-muted-foreground">{c.body}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section className="mx-auto max-w-3xl px-4 py-16 text-center">
          <h2 className="text-2xl font-bold text-foreground">See it work on your own material</h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            The free trial takes one chapter from questions to draft, so you can judge the result before
            you pay. No card needed.
          </p>
          <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/auth/sign-up"
              data-goatcounter-click="cta-footer-trial"
              className="rounded-md bg-primary px-6 py-3 font-semibold text-primary-foreground hover:bg-primary/90"
            >
              Start free trial
            </Link>
            <Link href="/pricing" className="text-primary underline-offset-4 hover:underline">
              Compare the free trial and Pro
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
      <Analytics />
    </>
  );
}
