/**
 * @jest-environment node
 */
import { analyticsOrigin } from '../analytics';

describe('analyticsOrigin', () => {
  const saved = process.env.GOATCOUNTER_URL;
  afterEach(() => {
    if (saved === undefined) delete process.env.GOATCOUNTER_URL;
    else process.env.GOATCOUNTER_URL = saved;
  });

  it('is off when GOATCOUNTER_URL is unset or blank', () => {
    delete process.env.GOATCOUNTER_URL;
    expect(analyticsOrigin()).toBeNull();
    expect(analyticsOrigin('')).toBeNull();
    expect(analyticsOrigin('   ')).toBeNull();
  });

  it('reads GOATCOUNTER_URL by default and reduces it to an origin', () => {
    process.env.GOATCOUNTER_URL = 'https://stats.autoauthor.app/';
    expect(analyticsOrigin()).toBe('https://stats.autoauthor.app');
    expect(analyticsOrigin('https://stats.example.com/count?x=1')).toBe('https://stats.example.com');
  });

  it('refuses plain http, except on localhost for testing', () => {
    expect(analyticsOrigin('http://stats.autoauthor.app')).toBeNull();
    expect(analyticsOrigin('http://localhost:8081')).toBe('http://localhost:8081');
    expect(analyticsOrigin('http://127.0.0.1:8081')).toBe('http://127.0.0.1:8081');
  });

  it('refuses values that are not URLs or not web URLs', () => {
    expect(analyticsOrigin('stats.autoauthor.app')).toBeNull();
    expect(analyticsOrigin('javascript:alert(1)')).toBeNull();
    expect(analyticsOrigin('ftp://stats.autoauthor.app')).toBeNull();
  });
});
