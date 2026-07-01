import { generateFilename, validateExportOptions } from '../exportHelpers';

describe('generateFilename', () => {
  it('sanitizes the title and appends the format extension', () => {
    expect(generateFilename('My Book: A Story', 'pdf')).toBe('my-book-a-story.pdf');
  });

  it('maps the markdown format to the conventional .md extension', () => {
    expect(generateFilename('My Book', 'markdown')).toBe('my-book.md');
  });

  it('uses an explicit extension override (multi-file markdown -> .zip)', () => {
    expect(generateFilename('My Book', 'markdown', 'zip')).toBe('my-book.zip');
  });
});

describe('validateExportOptions', () => {
  it.each(['pdf', 'docx', 'epub', 'markdown'] as const)(
    'accepts the %s format',
    (format) => {
      expect(validateExportOptions(format).isValid).toBe(true);
    }
  );

  it('rejects an unknown format', () => {
    // @ts-expect-error deliberately invalid format
    expect(validateExportOptions('rtf').isValid).toBe(false);
  });
});
