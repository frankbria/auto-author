/**
 * Data validation layer for localStorage operations
 * Ensures data integrity for chapter backups and prevents corruption
 */

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  data?: unknown;
}

export interface ChapterBackup {
  content: string;
  timestamp: number;
  error?: string;
}

export interface BookData {
  id: string;
  title: string;
  [key: string]: unknown;
}

/**
 * Validates chapter backup data structure
 */
export function validateChapterBackup(data: unknown): ValidationResult {
  const errors: string[] = [];

  if (!data || typeof data !== 'object') {
    errors.push('Backup data must be an object');
    return { isValid: false, errors };
  }

  const backup = data as Record<string, unknown>;

  // Validate content field
  if (!backup.content || typeof backup.content !== 'string') {
    errors.push('Backup must have a valid content string');
  }

  // Validate timestamp field
  if (!backup.timestamp || typeof backup.timestamp !== 'number') {
    errors.push('Backup must have a valid timestamp number');
  } else if (backup.timestamp < 0 || backup.timestamp > Date.now() + 60000) {
    errors.push('Backup timestamp is invalid or in the future');
  }

  // Validate optional error field
  if (backup.error !== undefined && typeof backup.error !== 'string') {
    errors.push('Backup error field must be a string if present');
  }

  return {
    isValid: errors.length === 0,
    errors,
    data: errors.length === 0 ? (data as ChapterBackup) : undefined,
  };
}

/**
 * Validates book data structure
 */
export function validateBookData(data: unknown): ValidationResult {
  const errors: string[] = [];

  if (!data || typeof data !== 'object') {
    errors.push('Book data must be an object');
    return { isValid: false, errors };
  }

  const book = data as Record<string, unknown>;

  // Validate id field
  if (!book.id || typeof book.id !== 'string') {
    errors.push('Book must have a valid id string');
  }

  // Validate title field
  if (!book.title || typeof book.title !== 'string') {
    errors.push('Book must have a valid title string');
  }

  return {
    isValid: errors.length === 0,
    errors,
    data: errors.length === 0 ? (data as BookData) : undefined,
  };
}

/**
 * Validates retrieved localStorage data hasn't been corrupted
 */
export function validateStoredData(key: string, data: unknown): boolean {
  try {
    // Check if key suggests backup data
    if (key.includes('chapter-backup')) {
      const result = validateChapterBackup(data);
      if (!result.isValid) {
        console.warn(`Corrupted chapter backup data for key ${key}:`, result.errors);
        return false;
      }
      return true;
    }

    // Check if key suggests book data
    if (key.includes('book-')) {
      const result = validateBookData(data);
      if (!result.isValid) {
        console.warn(`Corrupted book data for key ${key}:`, result.errors);
        return false;
      }
      return true;
    }

    // Unknown key type, basic validation
    return data !== null && data !== undefined;
  } catch (error) {
    console.error(`Validation error for key ${key}:`, error);
    return false;
  }
}

/**
 * Checks if backup has expired based on TTL
 * Default TTL: 7 days
 */
export function isBackupExpired(timestamp: number, ttlDays: number = 7): boolean {
  const ttlMs = ttlDays * 24 * 60 * 60 * 1000;
  const age = Date.now() - timestamp;
  return age > ttlMs;
}

/**
 * Clean up corrupted or expired data from localStorage
 * Should be called on app mount or periodically
 */
export function cleanupStorage(ttlDays: number = 7): {
  removed: string[];
  errors: string[];
} {
  const removed: string[] = [];
  const errors: string[] = [];

  try {
    // Get all localStorage keys
    const keys = Object.keys(localStorage);

    for (const key of keys) {
      try {
        // Skip non-chapter-backup keys
        if (!key.includes('chapter-backup')) {
          continue;
        }

        const rawData = localStorage.getItem(key);
        if (!rawData) {
          continue;
        }

        // Try to parse data
        let parsedData: unknown;
        try {
          parsedData = JSON.parse(rawData);
        } catch (parseError) {
          console.warn(`Removing corrupted backup (invalid JSON): ${key}`);
          localStorage.removeItem(key);
          removed.push(key);
          continue;
        }

        // Validate structure
        const validation = validateChapterBackup(parsedData);
        if (!validation.isValid) {
          console.warn(`Removing corrupted backup (invalid structure): ${key}`, validation.errors);
          localStorage.removeItem(key);
          removed.push(key);
          continue;
        }

        // Check TTL expiration
        const backup = validation.data as ChapterBackup;
        if (isBackupExpired(backup.timestamp, ttlDays)) {
          console.info(`Removing expired backup: ${key} (age: ${Math.floor((Date.now() - backup.timestamp) / (24 * 60 * 60 * 1000))} days)`);
          localStorage.removeItem(key);
          removed.push(key);
          continue;
        }
      } catch (itemError) {
        const errorMsg = itemError instanceof Error ? itemError.message : String(itemError);
        errors.push(`Error processing ${key}: ${errorMsg}`);
      }
    }
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    errors.push(`Storage cleanup failed: ${errorMsg}`);
  }

  return { removed, errors };
}

/**
 * Safe localStorage getItem with validation
 */
export function getValidatedItem<T = unknown>(
  key: string,
  validator?: (data: unknown) => ValidationResult
): T | null {
  try {
    const rawData = localStorage.getItem(key);
    if (!rawData) {
      return null;
    }

    const parsedData = JSON.parse(rawData);

    // Use provided validator or basic validation
    if (validator) {
      const result = validator(parsedData);
      if (!result.isValid) {
        console.warn(`Validation failed for ${key}:`, result.errors);
        return null;
      }
      return result.data as T;
    } else if (!validateStoredData(key, parsedData)) {
      return null;
    }

    return parsedData as T;
  } catch (error) {
    console.error(`Error retrieving ${key}:`, error);
    return null;
  }
}

/**
 * Safe localStorage setItem with validation
 */
export function setValidatedItem(
  key: string,
  data: unknown,
  validator?: (data: unknown) => ValidationResult
): boolean {
  try {
    // Use provided validator or basic validation
    if (validator) {
      const result = validator(data);
      if (!result.isValid) {
        console.error(`Validation failed before saving ${key}:`, result.errors);
        return false;
      }
    }

    const serialized = JSON.stringify(data);
    localStorage.setItem(key, serialized);
    return true;
  } catch (error) {
    if (error instanceof Error && error.name === 'QuotaExceededError') {
      console.error('localStorage quota exceeded');
    } else {
      console.error(`Error saving ${key}:`, error);
    }
    return false;
  }
}
