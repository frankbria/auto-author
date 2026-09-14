import * as authClientModule from '@/lib/auth-client';

jest.mock('@/lib/auth-client', () => ({ marker: 'factory' }));

/**
 * A `jest.mock('@/lib/auth-client', factory)` reaches code that imports it (#713).
 *
 * SWC compiles `import … from '@/lib/auth-client'` to
 * `require('../lib/auth-client')`, following tsconfig paths, while `jest.mock`
 * keeps the alias. The two only resolve to one mock while no manual mock is
 * registered under the aliased name. A root `__mocks__/@/lib/auth-client.ts`
 * did exactly that from #39 until #713: the aliased specifier's module id
 * included the manual mock, the relative one didn't, and every factory for this
 * module (the global one in jest.setup.ts and fourteen per-test ones) silently
 * missed the components under test.
 *
 * This file's own import goes through the same rewrite, so it fails if that
 * happens again.
 */
it('applies the factory to a normal import of the module', () => {
  expect((authClientModule as unknown as { marker?: string }).marker).toBe('factory');
});
