// localStorage throws when the browser is full or set to keep nothing (#832).
// None of these lets that stop a page; writeStored says whether the text was kept.

export function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStored(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

export function removeStored(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Nothing was stored, so there is nothing to remove.
  }
}
