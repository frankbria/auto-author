#!/usr/bin/env node
/**
 * Writes the notices of the third-party packages this app ships (#825).
 *
 * Most of them are under licences that ask for their copyright notice to travel
 * with the software, and Next's standalone output copies none of those files.
 * This puts them in one file under public/, which the image serves and the
 * footer links to. It runs before every build (`prebuild` in package.json), in
 * the image build too, so it lists what that build installed.
 *
 *   node scripts/third-party-notices.mjs [out]    default: public/third-party-notices.txt
 */
import { existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = process.argv[2] ?? join(root, 'public', 'third-party-notices.txt');
const lock = JSON.parse(readFileSync(join(root, 'package-lock.json'), 'utf8'));

const entries = new Map();
const copyleft = [];
for (const [path, locked] of Object.entries(lock.packages)) {
  const dir = join(root, path);
  // '' is this app. Dev packages build and test it and are not shipped. The
  // lockfile lists optional builds for every platform; the installed one is here.
  if (!path || locked.dev || locked.link || !existsSync(join(dir, 'package.json'))) continue;

  const pkg = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8'));
  const licence = pkg.license ?? locked.license ?? 'not stated';
  let text = readdirSync(dir, { withFileTypes: true })
    .filter((file) => file.isFile() && /^(licen[cs]e|copying|notice)/i.test(file.name))
    .map((file) => readFileSync(join(dir, file.name), 'utf8').trim())
    .join('\n\n');
  if (!text && existsSync(join(dir, 'README.md'))) {
    // No licence file. libvips says it in its README, with the libraries built into it.
    const section = readFileSync(join(dir, 'README.md'), 'utf8').split(/^## /m).find((part) => /^licen[cs]/i.test(part));
    text = section ? section.trim() : '';
  }
  const source = typeof pkg.repository === 'string' ? pkg.repository : pkg.repository?.url;

  const name = `${pkg.name}@${pkg.version}`;
  if (/GPL/.test(licence)) copyleft.push(name);
  entries.set(
    name,
    [name, `Licence: ${licence}`, ...(source ? [`Source: ${source}`] : []), '', text || '(This package ships no licence file.)'].join('\n'),
  );
}

const header = [
  'Third-party software notices',
  '',
  `This web application is built with the ${entries.size} third-party packages listed below. Each entry gives`,
  'the package and version, its licence, where its source is, and the licence text the package ships.',
  ...(copyleft.length
    ? [
        '',
        'Under a GNU licence, which the entry names:',
        ...copyleft.map((name) => `  ${name}`),
        'The full text of the GNU Lesser General Public License, version 3, and of the GNU General Public',
        'License, version 3, which it adds to, are at /licenses/LGPL-3.0.txt and /licenses/GPL-3.0.txt.',
        'The source is at the address in the entry.',
      ]
    : []),
  '',
].join('\n');

const rule = '='.repeat(72);
const sorted = [...entries.keys()].sort((a, b) => a.localeCompare(b)).map((name) => entries.get(name));
writeFileSync(out, [header, ...sorted].join(`\n${rule}\n`) + '\n');
console.log(`third-party notices: ${entries.size} packages -> ${out}`);
