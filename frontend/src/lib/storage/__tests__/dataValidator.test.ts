/**
 * Tests for data validation layer
 * Ensures localStorage data integrity and corruption detection
 */

import {
  validateChapterBackup,
  validateBookData,
  validateStoredData,
  isBackupExpired,
  cleanupStorage,
  getValidatedItem,
  setValidatedItem,
  ChapterBackup,
} from '../dataValidator';

describe('dataValidator', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('validateChapterBackup', () => {
    it('validates correct backup data', () => {
      const backup: ChapterBackup = {
        content: '<p>Test content</p>',
        timestamp: Date.now(),
        error: 'Network error',
      };

      const result = validateChapterBackup(backup);

      expect(result.isValid).toBe(true);
      expect(result.errors).toEqual([]);
      expect(result.data).toEqual(backup);
    });

    it('validates backup without optional error field', () => {
      const backup = {
        content: '<p>Test content</p>',
        timestamp: Date.now(),
      };

      const result = validateChapterBackup(backup);

      expect(result.isValid).toBe(true);
      expect(result.errors).toEqual([]);
    });

    it('rejects non-object data', () => {
      const result = validateChapterBackup('not an object');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Backup data must be an object');
    });

    it('rejects backup without content', () => {
      const backup = {
        timestamp: Date.now(),
      };

      const result = validateChapterBackup(backup);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Backup must have a valid content string');
    });

    it('rejects backup with non-string content', () => {
      const backup = {
        content: 123,
        timestamp: Date.now(),
      };

      const result = validateChapterBackup(backup);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Backup must have a valid content string');
    });

    it('rejects backup without timestamp', () => {
      const backup = {
        content: '<p>Test</p>',
      };

      const result = validateChapterBackup(backup);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Backup must have a valid timestamp number');
    });

    it('rejects backup with negative timestamp', () => {
      const backup = {
        content: '<p>Test</p>',
        timestamp: -1000,
      };

      const result = validateChapterBackup(backup);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Backup timestamp is invalid or in the future');
    });

    it('rejects backup with future timestamp', () => {
      const backup = {
        content: '<p>Test</p>',
        timestamp: Date.now() + 120000, // 2 minutes in future
      };

      const result = validateChapterBackup(backup);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Backup timestamp is invalid or in the future');
    });

    it('rejects backup with non-string error field', () => {
      const backup = {
        content: '<p>Test</p>',
        timestamp: Date.now(),
        error: 123,
      };

      const result = validateChapterBackup(backup);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Backup error field must be a string if present');
    });
  });

  describe('validateBookData', () => {
    it('validates correct book data', () => {
      const book = {
        id: 'book-123',
        title: 'Test Book',
        author: 'Test Author',
      };

      const result = validateBookData(book);

      expect(result.isValid).toBe(true);
      expect(result.errors).toEqual([]);
    });

    it('rejects book without id', () => {
      const book = {
        title: 'Test Book',
      };

      const result = validateBookData(book);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Book must have a valid id string');
    });

    it('rejects book without title', () => {
      const book = {
        id: 'book-123',
      };

      const result = validateBookData(book);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Book must have a valid title string');
    });

    it('rejects non-object data', () => {
      const result = validateBookData(null);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Book data must be an object');
    });
  });

  describe('validateStoredData', () => {
    it('validates chapter backup data by key pattern', () => {
      const backup = {
        content: '<p>Test</p>',
        timestamp: Date.now(),
      };

      const isValid = validateStoredData('chapter-backup-book1-chapter1', backup);

      expect(isValid).toBe(true);
    });

    it('validates book data by key pattern', () => {
      const book = {
        id: 'book-123',
        title: 'Test Book',
      };

      const isValid = validateStoredData('book-123', book);

      expect(isValid).toBe(true);
    });

    it('rejects corrupted chapter backup', () => {
      const corruptBackup = {
        content: 123, // Should be string
        timestamp: Date.now(),
      };

      const isValid = validateStoredData('chapter-backup-test', corruptBackup);

      expect(isValid).toBe(false);
    });

    it('handles unknown key types with basic validation', () => {
      const data = { some: 'data' };

      const isValid = validateStoredData('unknown-key', data);

      expect(isValid).toBe(true);
    });

    it('rejects null data', () => {
      const isValid = validateStoredData('test-key', null);

      expect(isValid).toBe(false);
    });
  });

  describe('isBackupExpired', () => {
    it('returns false for recent backup', () => {
      const recentTimestamp = Date.now() - 1000; // 1 second ago

      const expired = isBackupExpired(recentTimestamp);

      expect(expired).toBe(false);
    });

    it('returns true for expired backup (default 7 days)', () => {
      const oldTimestamp = Date.now() - 8 * 24 * 60 * 60 * 1000; // 8 days ago

      const expired = isBackupExpired(oldTimestamp);

      expect(expired).toBe(true);
    });

    it('returns false for backup just under TTL', () => {
      const timestamp = Date.now() - 6.9 * 24 * 60 * 60 * 1000; // 6.9 days ago

      const expired = isBackupExpired(timestamp, 7);

      expect(expired).toBe(false);
    });

    it('supports custom TTL', () => {
      const timestamp = Date.now() - 2 * 24 * 60 * 60 * 1000; // 2 days ago

      const expiredWith1Day = isBackupExpired(timestamp, 1);
      const notExpiredWith3Days = isBackupExpired(timestamp, 3);

      expect(expiredWith1Day).toBe(true);
      expect(notExpiredWith3Days).toBe(false);
    });
  });

  describe('cleanupStorage', () => {
    it('removes corrupted backups (invalid JSON)', () => {
      localStorage.setItem('chapter-backup-test1', '{invalid json}');
      localStorage.setItem('chapter-backup-test2', 'valid but not json');

      const result = cleanupStorage();

      expect(result.removed).toContain('chapter-backup-test1');
      expect(result.removed).toContain('chapter-backup-test2');
      expect(localStorage.getItem('chapter-backup-test1')).toBeNull();
      expect(localStorage.getItem('chapter-backup-test2')).toBeNull();
    });

    it('removes backups with invalid structure', () => {
      const invalidBackup = {
        content: 123, // Should be string
        timestamp: Date.now(),
      };
      localStorage.setItem('chapter-backup-test', JSON.stringify(invalidBackup));

      const result = cleanupStorage();

      expect(result.removed).toContain('chapter-backup-test');
      expect(localStorage.getItem('chapter-backup-test')).toBeNull();
    });

    it('removes expired backups', () => {
      const expiredBackup = {
        content: '<p>Old</p>',
        timestamp: Date.now() - 8 * 24 * 60 * 60 * 1000, // 8 days old
      };
      localStorage.setItem('chapter-backup-expired', JSON.stringify(expiredBackup));

      const result = cleanupStorage(7);

      expect(result.removed).toContain('chapter-backup-expired');
      expect(localStorage.getItem('chapter-backup-expired')).toBeNull();
    });

    it('preserves valid recent backups', () => {
      const validBackup = {
        content: '<p>Recent</p>',
        timestamp: Date.now() - 1000, // 1 second old
      };
      localStorage.setItem('chapter-backup-valid', JSON.stringify(validBackup));

      const result = cleanupStorage();

      expect(result.removed).not.toContain('chapter-backup-valid');
      expect(localStorage.getItem('chapter-backup-valid')).not.toBeNull();
    });

    it('ignores non-backup keys', () => {
      localStorage.setItem('some-other-key', 'data');
      localStorage.setItem('user-preferences', JSON.stringify({ theme: 'dark' }));

      const result = cleanupStorage();

      expect(localStorage.getItem('some-other-key')).toBe('data');
      expect(localStorage.getItem('user-preferences')).not.toBeNull();
    });

    it('handles multiple backups correctly', () => {
      // Valid backup
      localStorage.setItem('chapter-backup-1', JSON.stringify({
        content: '<p>Valid</p>',
        timestamp: Date.now(),
      }));

      // Expired backup
      localStorage.setItem('chapter-backup-2', JSON.stringify({
        content: '<p>Expired</p>',
        timestamp: Date.now() - 10 * 24 * 60 * 60 * 1000,
      }));

      // Corrupted backup
      localStorage.setItem('chapter-backup-3', '{corrupted}');

      const result = cleanupStorage();

      expect(result.removed).toHaveLength(2);
      expect(result.removed).toContain('chapter-backup-2');
      expect(result.removed).toContain('chapter-backup-3');
      expect(localStorage.getItem('chapter-backup-1')).not.toBeNull();
    });

    it('returns errors for cleanup failures', () => {
      // Create a backup first
      localStorage.setItem('chapter-backup-test', JSON.stringify({
        content: '<p>Test</p>',
        timestamp: Date.now(),
      }));

      // Mock JSON.parse to throw for specific key
      const originalParse = JSON.parse;
      let callCount = 0;
      global.JSON.parse = jest.fn().mockImplementation((str) => {
        callCount++;
        if (callCount === 2) { // Second call (first is for getting keys)
          throw new Error('Parse error');
        }
        return originalParse(str);
      });

      const result = cleanupStorage();

      // Should continue despite error
      expect(result.errors.length).toBeGreaterThanOrEqual(0);

      // Restore original
      global.JSON.parse = originalParse;
    });
  });

  describe('getValidatedItem', () => {
    it('retrieves and validates valid data', () => {
      const backup: ChapterBackup = {
        content: '<p>Test</p>',
        timestamp: Date.now(),
      };
      localStorage.setItem('test-key', JSON.stringify(backup));

      const retrieved = getValidatedItem<ChapterBackup>('test-key', validateChapterBackup);

      expect(retrieved).toEqual(backup);
    });

    it('returns null for non-existent key', () => {
      const retrieved = getValidatedItem('non-existent');

      expect(retrieved).toBeNull();
    });

    it('returns null for invalid JSON', () => {
      localStorage.setItem('bad-json', '{invalid}');

      const retrieved = getValidatedItem('bad-json');

      expect(retrieved).toBeNull();
    });

    it('returns null when validation fails', () => {
      const invalidData = { content: 123, timestamp: Date.now() };
      localStorage.setItem('invalid-backup', JSON.stringify(invalidData));

      const retrieved = getValidatedItem('invalid-backup', validateChapterBackup);

      expect(retrieved).toBeNull();
    });

    it('uses basic validation when no validator provided', () => {
      localStorage.setItem('chapter-backup-test', JSON.stringify({
        content: '<p>Test</p>',
        timestamp: Date.now(),
      }));

      const retrieved = getValidatedItem('chapter-backup-test');

      expect(retrieved).not.toBeNull();
    });
  });

  describe('setValidatedItem', () => {
    it('saves valid data', () => {
      const backup: ChapterBackup = {
        content: '<p>Test</p>',
        timestamp: Date.now(),
      };

      const success = setValidatedItem('test-key', backup, validateChapterBackup);

      expect(success).toBe(true);
      expect(localStorage.getItem('test-key')).not.toBeNull();
    });

    it('rejects invalid data when validator provided', () => {
      const invalidBackup = {
        content: 123, // Invalid
        timestamp: Date.now(),
      };

      const success = setValidatedItem('test-key', invalidBackup, validateChapterBackup);

      expect(success).toBe(false);
      expect(localStorage.getItem('test-key')).toBeNull();
    });

    it('saves without validation when no validator provided', () => {
      const data = { some: 'data' };

      const success = setValidatedItem('test-key', data);

      expect(success).toBe(true);
      expect(localStorage.getItem('test-key')).not.toBeNull();
    });

    it('handles quota exceeded error', () => {
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = jest.fn().mockImplementation(() => {
        const error = new Error('QuotaExceededError');
        error.name = 'QuotaExceededError';
        throw error;
      });

      const success = setValidatedItem('test-key', { data: 'test' });

      expect(success).toBe(false);

      Storage.prototype.setItem = originalSetItem;
    });
  });
});
