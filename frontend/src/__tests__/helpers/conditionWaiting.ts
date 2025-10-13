/**
 * Condition-based waiting utility for reliable async testing
 *
 * Replaces arbitrary timeouts with condition polling, making tests:
 * - More reliable (no race conditions)
 * - Faster (returns as soon as condition is met)
 * - More maintainable (clear intent)
 *
 * @example
 * // Instead of: await page.waitForTimeout(3000);
 * // Use: await waitForCondition(() => element.isVisible());
 */

export interface WaitOptions {
  /**
   * Maximum time to wait in milliseconds
   * @default 5000
   */
  timeout?: number;

  /**
   * Interval between condition checks in milliseconds
   * @default 100
   */
  interval?: number;

  /**
   * Custom error message when timeout occurs
   * @default 'Condition timeout'
   */
  timeoutMessage?: string;
}

/**
 * Wait for a condition to become true, polling at regular intervals
 *
 * @param condition - Synchronous or async function returning boolean
 * @param options - Configuration options for timeout, interval, and error message
 * @returns Promise that resolves when condition becomes true
 * @throws Error when timeout is reached before condition becomes true
 */
export async function waitForCondition(
  condition: () => boolean | Promise<boolean>,
  options: WaitOptions = {}
): Promise<void> {
  const {
    timeout = 5000,
    interval = 100,
    timeoutMessage = 'Condition timeout'
  } = options;

  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    // Support both sync and async condition functions
    const result = await Promise.resolve(condition());

    if (result) {
      return; // Condition met, exit immediately
    }

    // Wait for next polling interval
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  // Timeout reached without condition becoming true
  throw new Error(timeoutMessage);
}
