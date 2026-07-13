/**
 * Canonical genre / target-audience option lists for book creation and
 * metadata editing (#205). Single source of truth shared by
 * BookCreationWizard and BookMetadataForm — the two previously carried
 * divergent hardcoded lists.
 *
 * Values are persisted as free-text strings (bookCreationSchema / backend
 * accept ≤100-char free text); consistency is enforced here at the UI layer.
 */
export const GENRE_OPTIONS = [
  { label: 'Fiction', value: 'fiction' },
  { label: 'Non-Fiction', value: 'non-fiction' },
  { label: 'Science Fiction', value: 'sci-fi' },
  { label: 'Fantasy', value: 'fantasy' },
  { label: 'Mystery', value: 'mystery' },
  { label: 'Romance', value: 'romance' },
  { label: 'Historical', value: 'historical' },
  { label: 'Biography', value: 'biography' },
  { label: 'Self-Help', value: 'self-help' },
  { label: 'Business', value: 'business' },
  { label: 'Other', value: 'other' },
] as const;

export type Genre = (typeof GENRE_OPTIONS)[number]['value'];

export const TARGET_AUDIENCE_OPTIONS = [
  { label: 'Children', value: 'children' },
  { label: 'Young Adult', value: 'young-adult' },
  { label: 'Adult', value: 'adult' },
  { label: 'General', value: 'general' },
  { label: 'Academic', value: 'academic' },
  { label: 'Professional', value: 'professional' },
] as const;

export type TargetAudience = (typeof TARGET_AUDIENCE_OPTIONS)[number]['value'];
