/**
 * The 5 documented AI writing styles (user manual + #55).
 * Shared by draft generation and the settings default-style preference.
 */
export const WRITING_STYLES = [
  { value: 'professional', label: 'Professional' },
  { value: 'conversational', label: 'Conversational' },
  { value: 'academic', label: 'Academic' },
  { value: 'creative', label: 'Creative' },
  { value: 'technical', label: 'Technical' },
] as const;

export type WritingStyle = (typeof WRITING_STYLES)[number]['value'];

export const DEFAULT_WRITING_STYLE: WritingStyle = 'conversational';

export function isWritingStyle(value: unknown): value is WritingStyle {
  return WRITING_STYLES.some((style) => style.value === value);
}
