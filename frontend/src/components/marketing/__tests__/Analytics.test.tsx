/**
 * @jest-environment node
 */
import Analytics from '../Analytics';

jest.mock('next/headers', () => ({
  headers: jest.fn(async () => new Headers({ 'x-nonce': 'abc123' })),
}));

describe('Analytics', () => {
  const saved = process.env.GOATCOUNTER_URL;
  afterEach(() => {
    if (saved === undefined) delete process.env.GOATCOUNTER_URL;
    else process.env.GOATCOUNTER_URL = saved;
  });

  it('renders nothing while GOATCOUNTER_URL is unset', async () => {
    delete process.env.GOATCOUNTER_URL;
    expect(await Analytics()).toBeNull();
  });

  it('renders nothing for a value it will not trust', async () => {
    process.env.GOATCOUNTER_URL = 'http://stats.autoauthor.app';
    expect(await Analytics()).toBeNull();
  });

  it("renders GoatCounter's script from the configured site, with the CSP nonce", async () => {
    process.env.GOATCOUNTER_URL = 'https://stats.autoauthor.app';
    const el = await Analytics();
    expect(el).not.toBeNull();
    expect(el!.type).toBe('script');
    expect(el!.props).toMatchObject({
      'data-goatcounter': 'https://stats.autoauthor.app/count',
      src: 'https://stats.autoauthor.app/count.js',
      async: true,
      nonce: 'abc123',
    });
  });
});
