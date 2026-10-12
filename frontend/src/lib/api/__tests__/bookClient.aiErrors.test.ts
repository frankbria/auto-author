/**
 * What the five AI client methods throw when the backend refuses (#803).
 *
 * They used to throw `new Error("... <status> <raw body>")`: the page showed
 * JSON, and the status never reached the classifier, so a quota or an upgrade
 * state could not render. They now go through `aiError()`, like the other AI
 * methods: a readable message, the status, and what the response headers say.
 */
import { bookClient } from '@/lib/api/bookClient';

type Refusal = { status: number; body: unknown; headers?: Record<string, string> };

function refusal({ status, body, headers = {} }: Refusal) {
  return {
    ok: false,
    status,
    headers: new Headers(headers),
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

const METHODS: Array<[string, () => Promise<unknown>]> = [
  ['transformChapterStyle', () => bookClient.transformChapterStyle('b1', 'c1', { content: 'x', target_style: 'formal' })],
  ['enhanceChapterText', () => bookClient.enhanceChapterText('b1', 'c1', { content: 'x', enhancement_type: 'clarity' })],
  ['enhanceVoiceTranscription', () => bookClient.enhanceVoiceTranscription('b1', 'c1', { content: 'x' })],
  ['generateChapterQuestions', () => bookClient.generateChapterQuestions('b1', 'c1', { count: 3 })],
  ['regenerateChapterQuestions', () => bookClient.regenerateChapterQuestions('b1', 'c1', {})],
];

const QUOTA =
  'AI usage limit reached (10 generations per day on the free plan). It resets at midnight UTC.';

async function thrownBy(call: () => Promise<unknown>, response: Refusal) {
  (global.fetch as jest.Mock) = jest.fn().mockResolvedValueOnce(refusal(response));
  try {
    await call();
  } catch (error) {
    return error as Error & Record<string, unknown>;
  }
  throw new Error('the call did not throw');
}

describe.each(METHODS)('%s', (_name, call) => {
  it('reports an exhausted allowance as a 429 with its period and the backend message', async () => {
    const error = await thrownBy(call, {
      status: 429,
      body: { detail: QUOTA },
      headers: { 'X-AI-Quota-Period': 'day', 'X-AI-Quota-Limit': '10' },
    });

    expect(error.message).toBe(QUOTA);
    expect(error.statusCode).toBe(429);
    expect(error.quotaPeriod).toBe('day');
  });

  it('reports a plan refusal as a 402 with a message and no JSON', async () => {
    const error = await thrownBy(call, {
      status: 402,
      body: { detail: { error: 'Your plan does not include this feature.', error_code: 'ENTITLEMENT_REQUIRED' } },
    });

    expect(error.statusCode).toBe(402);
    expect(error.message).toBe('Your plan does not include this feature.');
    expect(error.message).not.toMatch(/[{}]/);
  });

  it('reports a provider rate limit with the time to retry', async () => {
    const error = await thrownBy(call, {
      status: 429,
      body: { detail: { message: 'AI service rate limit exceeded', error_code: 'AI_RATE_LIMIT', retry_after: 4 } },
      headers: { 'Retry-After': '4' },
    });

    expect(error.message).toBe('AI service rate limit exceeded');
    expect(error.statusCode).toBe(429);
    expect(error.quotaPeriod).toBeUndefined();
    expect(error.retryAfter).toBe(4);
    expect(error.errorCode).toBe('AI_RATE_LIMIT');
  });

  it('says how long a text may be when the backend refuses it for length', async () => {
    const error = await thrownBy(call, {
      status: 422,
      body: {
        detail: 'Validation error',
        errors: [{ type: 'string_too_long', loc: ['body', 'content'], msg: 'String should have at most 32000 characters', ctx: { max_length: 32000 } }],
        error_summary: 'body -> content: String should have at most 32000 characters',
      },
    });

    expect(error.statusCode).toBe(422);
    expect(error.message).toBe('This text is longer than the limit of 32,000 characters. Try a shorter section.');
  });

  it('falls back to a plain sentence when the body is not JSON', async () => {
    (global.fetch as jest.Mock) = jest.fn().mockResolvedValueOnce({
      ok: false,
      status: 502,
      headers: new Headers(),
      json: async () => {
        throw new SyntaxError('Unexpected token <');
      },
      text: async () => '<html>Bad Gateway</html>',
    });

    // One call, and the error it threw: a second call would get no response at all.
    const error = await call().then(
      () => {
        throw new Error('the call did not throw');
      },
      (thrown: Error & { statusCode?: number }) => thrown
    );

    expect(error.statusCode).toBe(502);
    expect(error.message).toMatch(/^Failed to .+\. Please try again\.$/);
    expect(error.message).not.toMatch(/[<{]|502|Bad Gateway/);
  });
});
