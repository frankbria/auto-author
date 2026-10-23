/**
 * Test-only MongoDB fault injection for the real-auth frontend (#972).
 *
 * Loaded into `next dev` through NODE_OPTIONS by playwright.real-auth.config.ts,
 * never by the app. Each line of the file named by E2E_MONGO_FAULTS is
 * "<collection> <text>": a deleteMany on that collection whose filter contains
 * the text rejects, as a dropped connection would. mongodb is one of Next's
 * server-external packages, so this patches the driver the auth server uses.
 * Local and CI MongoDB run without test commands, so server fail points are
 * not available.
 */
const fs = require('fs');
const { Collection } = require('mongodb');

const file = process.env.E2E_MONGO_FAULTS;
const deleteMany = Collection.prototype.deleteMany;

Collection.prototype.deleteMany = function (filter, ...rest) {
  const faults = file && fs.existsSync(file) ? fs.readFileSync(file, 'utf8').split('\n') : [];
  const text = JSON.stringify(filter);
  const hit = faults.some((line) => {
    const [collection, needle] = line.split(' ');
    return collection === this.collectionName && needle && text.includes(needle);
  });
  if (hit) return Promise.reject(new Error(`injected fault: ${this.collectionName}.deleteMany`));
  return deleteMany.call(this, filter, ...rest);
};
