/**
 * Security utilities test suite
 *
 * Tests sanitization helpers and the RateLimiter class
 * (accessed via the exported loginRateLimiter / apiRateLimiter singletons).
 */

// Mock DOMPurify before any imports so the factory is hoisted correctly.
jest.mock('dompurify', () => ({
  sanitize: jest.fn((html: string) => html),
}));

import DOMPurify from 'dompurify';
import {
  sanitizeHtml,
  sanitizeText,
  sanitizeEmail,
  sanitizeUrl,
  sanitizeFileName,
  loginRateLimiter,
  apiRateLimiter,
} from '@/lib/security';

const mockSanitize = DOMPurify.sanitize as jest.Mock;

// ---------------------------------------------------------------------------
// sanitizeHtml
// ---------------------------------------------------------------------------

describe('sanitizeHtml', () => {
  beforeEach(() => {
    mockSanitize.mockClear();
    mockSanitize.mockImplementation((html: string) => html);
  });

  it('calls DOMPurify.sanitize with the html string', () => {
    sanitizeHtml('<p>Hello</p>');
    expect(mockSanitize).toHaveBeenCalledWith('<p>Hello</p>', expect.any(Object));
  });

  it('returns the value DOMPurify produces', () => {
    mockSanitize.mockReturnValueOnce('<p>safe</p>');
    expect(sanitizeHtml('<p>raw</p>')).toBe('<p>safe</p>');
  });

  it('passes default ALLOWED_TAGS including common safe tags', () => {
    sanitizeHtml('<p>text</p>');
    const config = mockSanitize.mock.calls[0][1] as Record<string, unknown>;
    const allowed = config.ALLOWED_TAGS as string[];
    expect(allowed).toContain('p');
    expect(allowed).toContain('strong');
    expect(allowed).toContain('em');
    expect(allowed).toContain('code');
    expect(allowed).toContain('h1');
    expect(allowed).toContain('ul');
    expect(allowed).toContain('li');
    expect(allowed).toContain('blockquote');
    expect(allowed).toContain('pre');
  });

  it('forbids script, object, embed, form, input tags by default', () => {
    sanitizeHtml('<script>x</script>');
    const config = mockSanitize.mock.calls[0][1] as Record<string, unknown>;
    const forbidden = config.FORBID_TAGS as string[];
    expect(forbidden).toContain('script');
    expect(forbidden).toContain('object');
    expect(forbidden).toContain('embed');
    expect(forbidden).toContain('form');
    expect(forbidden).toContain('input');
  });

  it('forbids dangerous event and style attributes by default', () => {
    sanitizeHtml('<p onclick="x">text</p>');
    const config = mockSanitize.mock.calls[0][1] as Record<string, unknown>;
    const forbidAttr = config.FORBID_ATTR as string[];
    expect(forbidAttr).toContain('onerror');
    expect(forbidAttr).toContain('onload');
    expect(forbidAttr).toContain('onclick');
    expect(forbidAttr).toContain('style');
  });

  it('disables data attributes by default', () => {
    sanitizeHtml('<p data-x="y">text</p>');
    const config = mockSanitize.mock.calls[0][1] as Record<string, unknown>;
    expect(config.ALLOW_DATA_ATTR).toBe(false);
  });

  it('overrides ALLOWED_TAGS when options.allowedTags is provided', () => {
    sanitizeHtml('<span>x</span>', { allowedTags: ['span', 'div'] });
    const config = mockSanitize.mock.calls[0][1] as Record<string, unknown>;
    expect(config.ALLOWED_TAGS).toEqual(['span', 'div']);
  });

  it('overrides ALLOWED_ATTR when options.allowedAttributes is provided', () => {
    sanitizeHtml('<p href="x">text</p>', { allowedAttributes: ['href'] });
    const config = mockSanitize.mock.calls[0][1] as Record<string, unknown>;
    expect(config.ALLOWED_ATTR).toEqual(['href']);
  });

  it('uses default tags when only allowedAttributes is customised', () => {
    sanitizeHtml('<p>text</p>', { allowedAttributes: ['data-id'] });
    const config = mockSanitize.mock.calls[0][1] as Record<string, unknown>;
    expect(config.ALLOWED_TAGS).toContain('p');
  });
});

// ---------------------------------------------------------------------------
// sanitizeText
// ---------------------------------------------------------------------------

describe('sanitizeText', () => {
  it('strips HTML tags from the string', () => {
    expect(sanitizeText('<p>Hello</p>')).toBe('Hello');
    expect(sanitizeText('<b>bold</b>')).toBe('bold');
  });

  it('strips nested / complex tags', () => {
    expect(sanitizeText('<div class="x"><span>inner</span></div>')).toBe('inner');
  });

  it('removes script content', () => {
    const result = sanitizeText('<script>alert(1)</script>');
    expect(result).not.toContain('<script>');
    expect(result).not.toContain('</script>');
  });

  it('removes angle bracket characters', () => {
    const result = sanitizeText('a < b > c');
    expect(result).not.toContain('<');
    expect(result).not.toContain('>');
  });

  it('removes double-quote characters', () => {
    expect(sanitizeText('say "hello"')).not.toContain('"');
  });

  it('removes single-quote characters', () => {
    expect(sanitizeText("it's fine")).not.toContain("'");
  });

  it('strips javascript: protocol (case-insensitive)', () => {
    expect(sanitizeText('javascript:alert(1)')).not.toMatch(/javascript:/i);
    expect(sanitizeText('JAVASCRIPT:void(0)')).not.toMatch(/javascript:/i);
  });

  it('strips data: protocol (case-insensitive)', () => {
    expect(sanitizeText('data:text/html,<h1>x</h1>')).not.toMatch(/data:/i);
    expect(sanitizeText('DATA:image/png;base64,abc')).not.toMatch(/data:/i);
  });

  it('strips vbscript: protocol (case-insensitive)', () => {
    expect(sanitizeText('vbscript:msgbox(1)')).not.toMatch(/vbscript:/i);
  });

  it('trims surrounding whitespace', () => {
    expect(sanitizeText('  hello  ')).toBe('hello');
  });

  it('returns empty string for non-string input', () => {
    expect(sanitizeText(null as unknown as string)).toBe('');
    expect(sanitizeText(undefined as unknown as string)).toBe('');
    expect(sanitizeText(42 as unknown as string)).toBe('');
    expect(sanitizeText({} as unknown as string)).toBe('');
  });

  it('returns empty string for empty input', () => {
    expect(sanitizeText('')).toBe('');
  });

  it('passes clean plain text through unchanged (modulo trim)', () => {
    expect(sanitizeText('Hello, world!')).toBe('Hello, world!');
  });
});

// ---------------------------------------------------------------------------
// sanitizeEmail
// ---------------------------------------------------------------------------

describe('sanitizeEmail', () => {
  it('returns a valid email in lowercase', () => {
    expect(sanitizeEmail('User@Example.com')).toBe('user@example.com');
  });

  it('trims surrounding whitespace', () => {
    expect(sanitizeEmail('  user@example.com  ')).toBe('user@example.com');
  });

  it('converts to lowercase', () => {
    expect(sanitizeEmail('ADMIN@DOMAIN.ORG')).toBe('admin@domain.org');
  });

  it('returns empty string when format is invalid after sanitization', () => {
    expect(sanitizeEmail('not-an-email')).toBe('');
    expect(sanitizeEmail('@missing-local')).toBe('');
    expect(sanitizeEmail('missing-at.com')).toBe('');
    expect(sanitizeEmail('two@@symbols.com')).toBe('');
  });

  it('returns empty string for non-string input', () => {
    expect(sanitizeEmail(null as unknown as string)).toBe('');
    expect(sanitizeEmail(undefined as unknown as string)).toBe('');
  });

  it('removes characters outside [a-z0-9.@_+-]', () => {
    // '!' is stripped; result 'username@example.com' is a valid email
    expect(sanitizeEmail('user!name@example.com')).toBe('username@example.com');
  });

  it('allows plus-sign addressing', () => {
    expect(sanitizeEmail('user+tag@example.com')).toBe('user+tag@example.com');
  });

  it('allows underscores and hyphens in local part', () => {
    expect(sanitizeEmail('first.last_name-01@example.com')).toBe(
      'first.last_name-01@example.com'
    );
  });

  it('returns empty string for an empty input', () => {
    expect(sanitizeEmail('')).toBe('');
  });
});

// ---------------------------------------------------------------------------
// sanitizeUrl
// ---------------------------------------------------------------------------

describe('sanitizeUrl', () => {
  it('allows http:// URLs', () => {
    expect(sanitizeUrl('http://example.com')).toBe('http://example.com');
  });

  it('allows https:// URLs', () => {
    expect(sanitizeUrl('https://example.com/path?q=1#hash')).toBe(
      'https://example.com/path?q=1#hash'
    );
  });

  it('allows root-relative URLs (start with /)', () => {
    expect(sanitizeUrl('/api/v1/books')).toBe('/api/v1/books');
    expect(sanitizeUrl('/path/to/page')).toBe('/path/to/page');
  });

  it('allows protocol-relative URLs (start with //)', () => {
    expect(sanitizeUrl('//cdn.example.com/asset.js')).toBe(
      '//cdn.example.com/asset.js'
    );
  });

  it('allows relative paths with no protocol colon', () => {
    expect(sanitizeUrl('relative/path')).toBe('relative/path');
    expect(sanitizeUrl('images/logo.png')).toBe('images/logo.png');
  });

  it('blocks javascript: protocol (case-insensitive)', () => {
    expect(sanitizeUrl('javascript:alert(1)')).toBe('');
    expect(sanitizeUrl('JAVASCRIPT:void(0)')).toBe('');
    expect(sanitizeUrl('JavaScript:evil()')).toBe('');
  });

  it('blocks data: protocol (case-insensitive)', () => {
    expect(sanitizeUrl('data:text/html,<h1>x</h1>')).toBe('');
    expect(sanitizeUrl('DATA:image/png;base64,abc')).toBe('');
  });

  it('blocks vbscript: protocol', () => {
    expect(sanitizeUrl('vbscript:msgbox(1)')).toBe('');
  });

  it('blocks file: protocol', () => {
    expect(sanitizeUrl('file:///etc/passwd')).toBe('');
    expect(sanitizeUrl('FILE:///C:/Windows/System32')).toBe('');
  });

  it('blocks ftp: protocol', () => {
    expect(sanitizeUrl('ftp://files.example.com/pub')).toBe('');
  });

  it('returns empty string for an unknown scheme with colon', () => {
    // e.g. 'custom:something' — has a colon but is not http/https/relative
    expect(sanitizeUrl('custom:something')).toBe('');
  });

  it('returns empty string for non-string input', () => {
    expect(sanitizeUrl(null as unknown as string)).toBe('');
    expect(sanitizeUrl(undefined as unknown as string)).toBe('');
  });

  it('returns empty string for empty input', () => {
    expect(sanitizeUrl('')).toBe('');
  });

  it('trims whitespace around the URL', () => {
    expect(sanitizeUrl('  https://example.com  ')).toBe('https://example.com');
  });
});

// ---------------------------------------------------------------------------
// sanitizeFileName
// ---------------------------------------------------------------------------

describe('sanitizeFileName', () => {
  it('preserves alphanumeric characters and dots', () => {
    expect(sanitizeFileName('file.txt')).toBe('file.txt');
    expect(sanitizeFileName('document123.pdf')).toBe('document123.pdf');
  });

  it('replaces spaces with underscore', () => {
    expect(sanitizeFileName('my file.txt')).toBe('my_file.txt');
    expect(sanitizeFileName('hello world')).toBe('hello_world');
  });

  it('replaces unsafe punctuation with underscore', () => {
    const result = sanitizeFileName('file!#$.txt');
    expect(result).not.toContain('!');
    expect(result).not.toContain('#');
    expect(result).not.toContain('$');
  });

  it('replaces path-traversal/dangerous characters with underscore', () => {
    // Regression: the hyphen in the regex char class used to form a range
    // (46–95) so '/', ':', '\\', '@' slipped through. Hyphen is now escaped.
    expect(sanitizeFileName('a/b.txt')).toBe('a_b.txt');
    expect(sanitizeFileName('a:b.txt')).toBe('a_b.txt');
    expect(sanitizeFileName('a\\b.txt')).toBe('a_b.txt');
    expect(sanitizeFileName('a@b.txt')).toBe('a_b.txt');
  });

  it('preserves hyphens (a valid filename character)', () => {
    expect(sanitizeFileName('my-file-name.txt')).toBe('my-file-name.txt');
  });

  it('removes leading dots (path-traversal prevention)', () => {
    expect(sanitizeFileName('.hidden')).toBe('hidden');
    expect(sanitizeFileName('...dotdot')).toBe('dotdot');
  });

  it('removes trailing dots', () => {
    expect(sanitizeFileName('file.')).toBe('file');
    expect(sanitizeFileName('file...')).toBe('file');
  });

  it('limits the output to 255 characters', () => {
    const longName = 'a'.repeat(300) + '.txt';
    const result = sanitizeFileName(longName);
    expect(result.length).toBeLessThanOrEqual(255);
  });

  it('returns empty string for non-string input', () => {
    expect(sanitizeFileName(null as unknown as string)).toBe('');
    expect(sanitizeFileName(undefined as unknown as string)).toBe('');
    expect(sanitizeFileName(42 as unknown as string)).toBe('');
  });

  it('returns empty string (or just dots removed) for empty input', () => {
    expect(sanitizeFileName('')).toBe('');
  });

  it('handles a filename that is only dots', () => {
    const result = sanitizeFileName('...');
    // Leading and trailing dots are removed, nothing left
    expect(result).toBe('');
  });
});

// ---------------------------------------------------------------------------
// RateLimiter — tested through loginRateLimiter
// ---------------------------------------------------------------------------

describe('RateLimiter via loginRateLimiter', () => {
  let dateSpy: jest.SpyInstance;
  let currentTime: number;
  let uniqueId: string;
  const extraIds: string[] = [];

  beforeEach(() => {
    currentTime = 1_000_000;
    dateSpy = jest.spyOn(Date, 'now').mockImplementation(() => currentTime);
    // Use a per-test unique identifier so tests don't share state.
    uniqueId = `test-${Math.random().toString(36).slice(2)}`;
    extraIds.length = 0;
  });

  afterEach(() => {
    dateSpy.mockRestore();
    loginRateLimiter.reset(uniqueId);
    extraIds.forEach((id) => loginRateLimiter.reset(id));
  });

  it('allows the very first request', () => {
    expect(loginRateLimiter.isAllowed(uniqueId)).toBe(true);
  });

  it('allows exactly 5 requests within the window', () => {
    for (let i = 0; i < 5; i++) {
      expect(loginRateLimiter.isAllowed(uniqueId)).toBe(true);
    }
  });

  it('blocks the 6th request (exceeds maxAttempts = 5)', () => {
    for (let i = 0; i < 5; i++) {
      loginRateLimiter.isAllowed(uniqueId);
    }
    expect(loginRateLimiter.isAllowed(uniqueId)).toBe(false);
  });

  it('allows requests again once the 15-minute window has expired', () => {
    for (let i = 0; i < 5; i++) {
      loginRateLimiter.isAllowed(uniqueId);
    }
    expect(loginRateLimiter.isAllowed(uniqueId)).toBe(false);

    // Advance past the 15-minute window (900 000 ms)
    currentTime += 15 * 60 * 1000 + 1;

    expect(loginRateLimiter.isAllowed(uniqueId)).toBe(true);
  });

  it('reset() clears the attempt count for an identifier', () => {
    for (let i = 0; i < 5; i++) {
      loginRateLimiter.isAllowed(uniqueId);
    }
    expect(loginRateLimiter.isAllowed(uniqueId)).toBe(false);

    loginRateLimiter.reset(uniqueId);

    expect(loginRateLimiter.isAllowed(uniqueId)).toBe(true);
  });

  it('tracks separate identifiers independently', () => {
    const id1 = `${uniqueId}-a`;
    const id2 = `${uniqueId}-b`;
    extraIds.push(id1, id2);

    for (let i = 0; i < 5; i++) {
      loginRateLimiter.isAllowed(id1);
    }

    // id1 exhausted, id2 untouched
    expect(loginRateLimiter.isAllowed(id1)).toBe(false);
    expect(loginRateLimiter.isAllowed(id2)).toBe(true);
  });

  it('counts the first successful call in the new window after reset-by-time', () => {
    // Saturate window
    for (let i = 0; i < 5; i++) {
      loginRateLimiter.isAllowed(uniqueId);
    }
    // Advance past window
    currentTime += 15 * 60 * 1000 + 1;
    // First call in new window starts the new window counter at 1
    expect(loginRateLimiter.isAllowed(uniqueId)).toBe(true);
    // Should still allow 4 more (total 5 in new window)
    for (let i = 0; i < 4; i++) {
      expect(loginRateLimiter.isAllowed(uniqueId)).toBe(true);
    }
    // 6th in new window is blocked
    expect(loginRateLimiter.isAllowed(uniqueId)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Exported instance shape checks
// ---------------------------------------------------------------------------

describe('loginRateLimiter export', () => {
  it('exposes isAllowed and reset methods', () => {
    expect(typeof loginRateLimiter.isAllowed).toBe('function');
    expect(typeof loginRateLimiter.reset).toBe('function');
  });
});

describe('apiRateLimiter export', () => {
  it('exposes isAllowed and reset methods', () => {
    expect(typeof apiRateLimiter.isAllowed).toBe('function');
    expect(typeof apiRateLimiter.reset).toBe('function');
  });

  it('allows 100 requests before blocking (configured limit)', () => {
    const id = `api-limit-test-${Math.random().toString(36).slice(2)}`;
    try {
      let allowed = 0;
      for (let i = 0; i < 100; i++) {
        if (apiRateLimiter.isAllowed(id)) allowed++;
      }
      expect(allowed).toBe(100);
      // 101st call should be blocked
      expect(apiRateLimiter.isAllowed(id)).toBe(false);
    } finally {
      apiRateLimiter.reset(id);
    }
  });
});
