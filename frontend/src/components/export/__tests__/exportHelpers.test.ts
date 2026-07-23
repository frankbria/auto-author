import {
  downloadBlob,
  estimateExportTime,
  formatFileSize,
  generateFilename,
  validateExportOptions,
} from '../exportHelpers';

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

  it('rejects a whitespace-only book title', () => {
    expect(validateExportOptions('pdf', '   ').isValid).toBe(false);
  });
});

describe('formatFileSize', () => {
  it('returns "0 B" for zero bytes', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('formats bytes, KB, MB and GB with one decimal', () => {
    expect(formatFileSize(512)).toBe('512.0 B');
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(2_500_000)).toBe('2.4 MB');
    expect(formatFileSize(3 * 1024 ** 3)).toBe('3.0 GB');
  });
});

describe('estimateExportTime', () => {
  it('enforces a 2-second floor for small books', () => {
    expect(estimateExportTime(100, 'pdf')).toBe(2);
    expect(estimateExportTime(0, 'docx')).toBe(2);
  });

  it('scales by word count and charges PDF a higher rate than other formats', () => {
    // 100k words: pdf 0.5/1000 -> 50s ; docx 0.3/1000 -> 30s
    expect(estimateExportTime(100_000, 'pdf')).toBe(50);
    expect(estimateExportTime(100_000, 'docx')).toBe(30);
    expect(estimateExportTime(100_000, 'docx')).toBeLessThan(
      estimateExportTime(100_000, 'pdf')
    );
  });
});

describe('downloadBlob', () => {
  it('creates a temporary anchor, triggers the download, and cleans up', () => {
    const clickSpy = jest.fn();
    const createObjectURL = jest.fn(() => 'blob:mock-url');
    const revokeObjectURL = jest.fn();
    // jsdom does not implement the URL blob API.
    Object.assign(window.URL, { createObjectURL, revokeObjectURL });

    const realCreate = document.createElement.bind(document);
    const createSpy = jest
      .spyOn(document, 'createElement')
      .mockImplementation((tag: string) => {
        const el = realCreate(tag) as HTMLElement;
        if (tag === 'a') (el as HTMLAnchorElement).click = clickSpy;
        return el;
      });
    const appendSpy = jest.spyOn(document.body, 'appendChild');
    const removeSpy = jest.spyOn(document.body, 'removeChild');

    const blob = new Blob(['data'], { type: 'application/pdf' });
    downloadBlob(blob, 'my-book.pdf');

    expect(createObjectURL).toHaveBeenCalledWith(blob);
    const anchor = createSpy.mock.results[0].value as HTMLAnchorElement;
    expect(anchor.download).toBe('my-book.pdf');
    expect(anchor.href).toContain('blob:mock-url');
    expect(appendSpy).toHaveBeenCalledWith(anchor);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(removeSpy).toHaveBeenCalledWith(anchor);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');

    createSpy.mockRestore();
    appendSpy.mockRestore();
    removeSpy.mockRestore();
  });
});
