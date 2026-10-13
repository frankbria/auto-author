/**
 * Third-party notices (#825).
 *
 * The frontend image ships about four hundred packages under licences that ask
 * for their notice to travel with them, and one, libvips (through sharp), under
 * the LGPL, which asks for the licence text itself. Next's standalone output
 * copies none of those files. `scripts/third-party-notices.mjs` writes them
 * into one file under `public/` before each build, and the LGPL and GPL texts
 * are kept beside it.
 *
 * This runs the script against the packages installed here.
 */
import { execFileSync } from 'child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const FRONTEND_ROOT = join(__dirname, '..', '..');

describe('third-party notices', () => {
  let notices = '';
  let entries: string[] = [];

  beforeAll(() => {
    const dir = mkdtempSync(join(tmpdir(), 'notices-'));
    try {
      const out = join(dir, 'notices.txt');
      execFileSync('node', ['scripts/third-party-notices.mjs', out], { cwd: FRONTEND_ROOT });
      notices = readFileSync(out, 'utf8');
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
    // Each package's part starts with a rule and then "name@version".
    entries = notices.split(/^={20,}\n/m).slice(1);
  });

  const entryFor = (name: string) => entries.find((entry) => entry.startsWith(`${name}@`));

  it('covers the packages that ship, and is not close to empty', () => {
    expect(entries.length).toBeGreaterThan(250);
    for (const name of ['react', 'next', 'sharp', 'better-auth']) {
      expect(entryFor(name)).toBeDefined();
    }
  });

  it('gives each package its licence and the text of its licence file', () => {
    const react = entryFor('react')!;
    expect(react).toMatch(/^react@\d+\.\d+\.\d+\nLicence: MIT\n/);
    expect(react).toContain('Permission is hereby granted, free of charge');
    expect(react).toContain('Copyright (c) Meta Platforms');
  });

  it('leaves out what is only used to build and test', () => {
    // What the lockfile marks as dev. Playwright is not among them: it is an optional
    // peer of next, which npm keeps under --omit=dev, so it is listed.
    for (const name of ['jest', 'eslint', 'typescript', '@testing-library/react']) {
      expect(existsSync(join(FRONTEND_ROOT, 'node_modules', name, 'package.json'))).toBe(true);
      expect(entryFor(name)).toBeUndefined();
    }
  });

  it('names libvips as LGPL, says what is inside it, and where the licence texts and its source are', () => {
    const libvips = entries.find((entry) => entry.startsWith('@img/sharp-libvips-'))!;
    expect(libvips).toBeDefined();
    expect(libvips).toContain('Licence: LGPL-3.0-or-later');
    // It ships no licence file. Its README lists the libraries built into it.
    expect(libvips).toMatch(/glib\s+\|\s+LGPLv3/);
    // On its own line: the address also appears in the README's text.
    expect(libvips).toMatch(/^Source: \S*github\.com\/lovell\/sharp-libvips/m);
    expect(notices).toContain('/licenses/LGPL-3.0.txt');
    expect(notices).toContain('/licenses/GPL-3.0.txt');
  });

  it('has no entry for a package that is not installed here', () => {
    // The lockfile lists a libvips build for every platform; one is installed.
    expect(entries.filter((entry) => entry.startsWith('@img/sharp-libvips-')).length).toBeLessThan(3);
  });

  it('keeps the LGPL and the GPL, which the LGPL is written on top of, as files the image serves', () => {
    const lgpl = join(FRONTEND_ROOT, 'public', 'licenses', 'LGPL-3.0.txt');
    const gpl = join(FRONTEND_ROOT, 'public', 'licenses', 'GPL-3.0.txt');
    expect(existsSync(lgpl) && existsSync(gpl)).toBe(true);
    expect(readFileSync(lgpl, 'utf8')).toMatch(/^\s*GNU LESSER GENERAL PUBLIC LICENSE\s+Version 3, 29 June 2007/);
    expect(readFileSync(gpl, 'utf8')).toMatch(/^\s*GNU GENERAL PUBLIC LICENSE\s+Version 3, 29 June 2007/);
    expect(readFileSync(gpl, 'utf8')).toContain('END OF TERMS AND CONDITIONS');
  });

  it('is written before every build', () => {
    const scripts = JSON.parse(readFileSync(join(FRONTEND_ROOT, 'package.json'), 'utf8')).scripts;
    expect(scripts.prebuild).toBe('node scripts/third-party-notices.mjs');
  });
});
