import { openTermsExits, termsExitOpen } from '@/lib/terms-exits';

// The exits a declining account can reach from the acceptance screen (#961).
describe('terms exits', () => {
  beforeEach(() => sessionStorage.clear());
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

  it('stays closed when storage is blocked', () => {
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(() => openTermsExits('u1')).not.toThrow();
    expect(termsExitOpen('/profile', 'u1')).toBe(false);
  });
});
