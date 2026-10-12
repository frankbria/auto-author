export interface WordCounts {
  before?: number;
  after?: number;
}

/**
 * Word counts before and after a rewrite, shown in the preview so a result
 * that lost text is visible before it is applied (#983). The change is given
 * in words, not colour.
 */
export function RewriteWordCounts({ before, after }: WordCounts) {
  if (before === undefined || after === undefined) return null;

  const change = before > 0 ? Math.round(((after - before) / before) * 100) : 0;

  return (
    <p className="text-sm text-muted-foreground" data-slot="rewrite-word-counts">
      {before.toLocaleString('en-US')} words before, {after.toLocaleString('en-US')} after
      {change !== 0 && ` (${Math.abs(change)}% ${change < 0 ? 'shorter' : 'longer'})`}
    </p>
  );
}
