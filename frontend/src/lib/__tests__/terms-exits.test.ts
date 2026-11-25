import { closeTermsExits, openTermsExits, termsExitOpen } from '@/lib/terms-exits';
import { signOutOrNotify } from '@/lib/sign-out';

jest.mock('@/lib/auth-client', () => ({
  authClient: { signOut: jest.fn().mockResolvedValue({ error: null }) },
}));
jest.mock('@/lib/toast', () => ({ toast: jest.fn() }));

// The exits a declining account can reach from the acceptance screen (#961).
describe('terms exits', () => {
  beforeEach(() => {
    closeTermsExits();
    sessionStorage.clear();
  });
  afterEach(() => jest.restoreAllMocks());

  it('opens Settings and Profile, and their subpages, for the account that chose them', () => {
    openTermsExits('u1');
    expect(termsExitOpen('/dashboard/settings', 'u1')).toBe(true);
    expect(termsExitOpen('/profile', 'u1')).toBe(true);
    expect(termsExitOpen('/profile/x', 'u1')).toBe(true);
    expect(termsExitOpen('/profile', 'u2')).toBe(false);
  });

  it('never opens another page', () => {
    openTermsExits('u1');
    expect(termsExitOpen('/dashboard', 'u1')).toBe(false);
    expect(termsExitOpen('/profiles', 'u1')).toBe(false);
    expect(termsExitOpen(null, 'u1')).toBe(false);
  });

  it('survives a reload in the same tab', () => {
    // A reload starts with no grant in memory; the tab's storage still has it.
    sessionStorage.setItem('terms-exits-open', 'u1');
    expect(termsExitOpen('/profile', 'u1')).toBe(true);
  });

  // Section 7's cancel-online promise must hold in a browser that blocks storage.
  it('still opens the exits when storage is blocked', () => {
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    jest.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(termsExitOpen('/profile', 'u1')).toBe(false);
    expect(() => openTermsExits('u1')).not.toThrow();
    expect(termsExitOpen('/profile', 'u1')).toBe(true);
    expect(() => closeTermsExits()).not.toThrow();
    expect(termsExitOpen('/profile', 'u1')).toBe(false);
  });

  it('closes them at sign-out, so the next sign-in in this tab is asked', async () => {
    openTermsExits('u1');
    expect(await signOutOrNotify()).toBe(true);
    expect(termsExitOpen('/dashboard/settings', 'u1')).toBe(false);
    expect(sessionStorage.getItem('terms-exits-open')).toBeNull();
  });
});
