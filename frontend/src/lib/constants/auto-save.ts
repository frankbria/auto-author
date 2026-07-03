/**
 * Auto-save interval bounds (seconds) shared by the settings form and the
 * chapter editor. 3s is the historical shipped default.
 */
export const AUTO_SAVE_MIN_SECONDS = 3;
export const AUTO_SAVE_MAX_SECONDS = 30;
export const AUTO_SAVE_DEFAULT_SECONDS = 3;

export function isValidAutoSaveInterval(value: number | undefined | null): value is number {
  return (
    typeof value === 'number' &&
    Number.isInteger(value) &&
    value >= AUTO_SAVE_MIN_SECONDS &&
    value <= AUTO_SAVE_MAX_SECONDS
  );
}
