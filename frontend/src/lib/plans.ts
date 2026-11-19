// The plans the public pricing page and landing page describe.
//
// The numbers come from GET /billing/plans, which reads the same settings the
// quota enforcer reads and the same Stripe Price the checkout charges (#766). The
// defaults below are only what the page shows before that answer arrives (and if
// it never does): they mirror the backend's config defaults and the price the
// owner adopted on 2026-10-28. A live answer always wins.

import type { PlanQuota, PlanQuotas } from '@/hooks/useBillingApi';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const EXPORT_FORMATS = ['PDF', 'DOCX', 'EPUB', 'Markdown'] as const;

export type PlanPrice = { amount: string; period: string };

export type PublicPlans = {
  /** Null when Stripe isn't configured or the price couldn't be read just now. */
  pro_price: PlanPrice | null;
  plans: PlanQuotas;
};

export const DEFAULT_PLANS: PublicPlans = {
  pro_price: { amount: '$49', period: 'month' },
  plans: {
    free: { daily: null, monthly: null, total: 30, draft_chapters: 1, export: false },
    pro: { daily: 50, monthly: 500, total: null, draft_chapters: null, export: true },
  },
};

/** "$49.00" reads as "$49" on a pricing card; other amounts are left alone. */
export function displayAmount(amount: string): string {
  return amount.replace(/^\$(\d[\d,]*)\.00$/, '$$$1');
}

function count(n: number, one: string, many: string): string {
  return n === 1 ? `${one}` : `${n} ${many}`;
}

function formatList(items: readonly string[]): string {
  return items.length > 1
    ? `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`
    : (items[0] ?? '');
}

/** "50 AI generations a day (500 a month)", or whichever window is set. */
export function generationWindows(q: PlanQuota): string {
  if (q.daily === null && q.monthly === null) return 'Unlimited AI generations';
  if (q.monthly === null) return `${q.daily} AI generations a day`;
  if (q.daily === null) return `${q.monthly} AI generations a month`;
  return `${q.daily} AI generations a day (${q.monthly} a month)`;
}

/**
 * What the free trial includes. It is a trial of one chapter, never a plan to
 * write a book on (owner decision 2026-10-28), so it says what stops.
 */
export function freeTrialFeatures(q: PlanQuota): string[] {
  const draft =
    q.draft_chapters == null
      ? 'Interview questions and an AI draft for every chapter'
      : q.draft_chapters === 1
        ? "One chapter's interview questions and AI draft"
        : `Interview questions and AI drafts for ${q.draft_chapters} chapters`;
  const lines = [
    'A book summary, typed or dictated',
    'An AI table of contents you edit',
    draft,
    'The full editor',
  ];
  lines.push(
    q.total == null
      ? generationWindows(q)
      : `${count(q.total, 'One AI generation', 'AI generations')} in total, which don't reset`
  );
  lines.push(q.export === false ? 'No export' : `Export to ${formatList(EXPORT_FORMATS)}`);
  return lines;
}

/** What Pro includes. */
export function proFeatures(q: PlanQuota): string[] {
  const lines = [
    q.draft_chapters == null
      ? 'Interview questions and AI drafts for every chapter'
      : `Interview questions and AI drafts for ${count(q.draft_chapters, 'one chapter', 'chapters')}`,
    'The full editor, with AI style changes',
    generationWindows(q),
  ];
  if (q.export !== false) lines.push(`Export to ${formatList(EXPORT_FORMATS)}`);
  lines.push('Cancel anytime');
  return lines;
}

function isQuota(v: unknown): v is PlanQuota {
  if (!v || typeof v !== 'object') return false;
  const q = v as Record<string, unknown>;
  const n = (x: unknown) => x === null || x === undefined || typeof x === 'number';
  return n(q.daily) && n(q.monthly) && n(q.total) && n(q.draft_chapters);
}

/**
 * The live plans, or null if they can't be read. Public: no credentials, so a
 * visitor's cookies never travel with it.
 */
export async function fetchPublicPlans(signal?: AbortSignal): Promise<PublicPlans | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/billing/plans`, { credentials: 'omit', signal });
    if (!res.ok) return null;
    const body = (await res.json()) as Partial<PublicPlans>;
    if (!body?.plans || !isQuota(body.plans.free) || !isQuota(body.plans.pro)) return null;
    const price = body.pro_price;
    const validPrice =
      price && typeof price.amount === 'string' && typeof price.period === 'string' ? price : null;
    return { pro_price: validPrice, plans: body.plans };
  } catch {
    return null;
  }
}
