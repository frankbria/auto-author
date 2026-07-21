/**
 * Canonical genre / target-audience option lists for book creation and
 * metadata editing (#205). Single source of truth shared by
 * BookCreationWizard and BookMetadataForm — the two previously carried
 * divergent hardcoded lists.
 *
 * Nonfiction-only (#215): Auto Author positions itself for nonfiction books
 * (landing page), so the fiction-only genres (Fiction/Sci-Fi/Fantasy/Mystery/
 * Romance) were removed. Values are persisted as free-text strings
 * (bookCreationSchema / backend accept ≤100-char free text); consistency is
 * enforced here at the UI layer.
 */
export const GENRE_OPTIONS = [
  { label: 'Non-Fiction', value: 'non-fiction' },
  { label: 'Business', value: 'business' },
  { label: 'Self-Help', value: 'self-help' },
  { label: 'Personal Development', value: 'personal-development' },
  { label: 'Health & Wellness', value: 'health-wellness' },
  { label: 'How-To / Guide', value: 'how-to' },
  { label: 'Historical', value: 'historical' },
  { label: 'Biography', value: 'biography' },
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
