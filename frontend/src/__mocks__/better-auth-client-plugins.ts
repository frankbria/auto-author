// Mock for better-auth/client/plugins (ESM-only in node_modules; see
// jest.config.cjs moduleNameMapper). The plugin factory just needs to be a
// callable that createAuthClient accepts.
export const twoFactorClient = jest.fn(() => ({ id: 'two-factor' }));

export default { twoFactorClient };
