import { logger } from '../logger';

describe('logger.debug', () => {
  const originalNodeEnv = process.env.NODE_ENV;
  let logSpy: jest.SpyInstance;

  beforeEach(() => {
    logSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    logSpy.mockRestore();
    process.env.NODE_ENV = originalNodeEnv;
  });

  it('does not call console.log in production', () => {
    process.env.NODE_ENV = 'production';
    logger.debug('internal state', { foo: 1 });
    expect(logSpy).not.toHaveBeenCalled();
  });

  it('calls console.log with all args outside production', () => {
    process.env.NODE_ENV = 'development';
    logger.debug('loaded state', { foo: 1 });
    expect(logSpy).toHaveBeenCalledWith('loaded state', { foo: 1 });
  });

  it('also logs under test env (non-production)', () => {
    process.env.NODE_ENV = 'test';
    logger.debug('hi');
    expect(logSpy).toHaveBeenCalledWith('hi');
  });
});
