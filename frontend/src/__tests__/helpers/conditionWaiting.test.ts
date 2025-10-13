/**
 * Test suite for condition-based waiting utility
 *
 * Following TDD: These tests define the expected behavior before implementation
 */

import { waitForCondition } from './conditionWaiting';

describe('waitForCondition', () => {
  it('should resolve when condition becomes true', async () => {
    let value = false;
    setTimeout(() => { value = true; }, 100);

    await waitForCondition(() => value, { timeout: 1000, interval: 50 });
    expect(value).toBe(true);
  });

  it('should timeout if condition never becomes true', async () => {
    await expect(
      waitForCondition(() => false, { timeout: 100, interval: 20 })
    ).rejects.toThrow('Condition timeout');
  });

  it('should support async condition functions', async () => {
    let value = false;
    setTimeout(() => { value = true; }, 100);

    await waitForCondition(async () => value, { timeout: 1000, interval: 50 });
    expect(value).toBe(true);
  });

  it('should use default timeout and interval', async () => {
    let value = false;
    setTimeout(() => { value = true; }, 100);

    await waitForCondition(() => value);
    expect(value).toBe(true);
  });

  it('should include custom timeout message', async () => {
    await expect(
      waitForCondition(() => false, {
        timeout: 100,
        interval: 20,
        timeoutMessage: 'Custom timeout message'
      })
    ).rejects.toThrow('Custom timeout message');
  });

  it('should poll at specified interval', async () => {
    let callCount = 0;
    const condition = () => {
      callCount++;
      return callCount >= 5;
    };

    const startTime = Date.now();
    await waitForCondition(condition, { timeout: 1000, interval: 100 });
    const duration = Date.now() - startTime;

    expect(callCount).toBe(5);
    // Should take approximately 400ms (4 intervals of 100ms)
    expect(duration).toBeGreaterThanOrEqual(350);
    expect(duration).toBeLessThan(600);
  });

  it('should immediately resolve if condition is already true', async () => {
    const startTime = Date.now();
    await waitForCondition(() => true, { timeout: 1000, interval: 100 });
    const duration = Date.now() - startTime;

    // Should resolve almost immediately
    expect(duration).toBeLessThan(50);
  });
});
