/**
 * The Reference ID a user is shown is the server's id for the request (#810).
 *
 * It was a random value made in the browser, so quoting it to support matched
 * nothing in the server's logs. The backend names every response in
 * `X-Request-ID`; an error built from a failed response now carries it, and
 * the classifiers use it.
 */
import { bookClient } from '@/lib/api/bookClient';
import { handleAIServiceError } from '@/lib/api/aiErrorHandler';
import { classifyError } from '@/lib/errors/classifier';
import * as ErrorNotification from '@/components/errors/ErrorNotification';

jest.mock('@/components/errors/ErrorNotification', () => ({
  showErrorNotification: jest.fn(),
}));

const SERVER_ID = '0f8fad5b-d9cb-469f-a165-70867728950e';

function failed(status: number, body: unknown, headers: Record<string, string> = { 'X-Request-ID': SERVER_ID }) {
  return {
    ok: false,
    status,
    headers: new Headers(headers),
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

async function thrownBy(call: () => Promise<unknown>, response: ReturnType<typeof failed>) {
  (global.fetch as jest.Mock) = jest.fn().mockResolvedValueOnce(response);
  try {
    await call();
  } catch (error) {
    return error as Error & Record<string, unknown>;
  }
  throw new Error('the call did not throw');
}

const SERVER_ERROR = { detail: 'An unexpected error occurred', request_id: SERVER_ID };

describe('an error from a failed response carries the id of the request', () => {
  it.each<[string, () => Promise<unknown>]>([
    ['a call that reports the status and the body', () => bookClient.createBook({ title: 'A' })],
    ['a call that reports the status alone', () => bookClient.getUserBooks()],
    ['an AI call', () => bookClient.generateChapterQuestions('b1', 'c1', { count: 3 })],
    ['an export', () => bookClient.exportPDF('b1')],
  ])('%s', async (_name, call) => {
    const error = await thrownBy(call, failed(500, SERVER_ERROR));

    expect(error.requestId).toBe(SERVER_ID);
  });

  it('keeps the message it had', async () => {
    const error = await thrownBy(() => bookClient.createBook({ title: 'A' }), failed(500, SERVER_ERROR));

    expect(error.message).toBe(`Failed to create book: 500 ${JSON.stringify(SERVER_ERROR)}`);
  });

  it('carries none when the response names none', async () => {
    const error = await thrownBy(() => bookClient.createBook({ title: 'A' }), failed(500, SERVER_ERROR, {}));

    expect(error.requestId).toBeUndefined();
  });
});

describe('the Reference ID', () => {
  it('is the server id when the error carries one', () => {
    const error = Object.assign(new Error('Failed to create book: 500'), { requestId: SERVER_ID });

    expect(classifyError(error).correlationId).toBe(SERVER_ID);
  });

  it('is the server id for an error that also has a status', () => {
    const error = Object.assign(new Error('Server error'), { statusCode: 500, requestId: SERVER_ID });

    expect(classifyError(error).correlationId).toBe(SERVER_ID);
  });

  it('is still made here when no response arrived, since no server id exists', () => {
    const made = classifyError(new TypeError('Failed to fetch')).correlationId;

    expect(made).toMatch(/^[a-z0-9]+-[a-z0-9]+$/);
    expect(made).not.toBe(SERVER_ID);
  });

  it.each([
    ['a refused AI request', 503, { detail: { message: 'The AI service is unavailable.', error_code: 'AI_UNAVAILABLE' } }],
    ['an exhausted allowance', 429, { detail: 'AI usage limit reached (10 generations per day on the free plan).' }],
    ['a plan refusal', 402, { detail: { error: 'Your plan does not include this feature.', error_code: 'ENTITLEMENT_REQUIRED' } }],
  ])('is the server id on the notification for %s', async (_name, status, body) => {
    const show = ErrorNotification.showErrorNotification as jest.Mock;
    show.mockClear();
    const error = await thrownBy(
      () => bookClient.generateChapterQuestions('b1', 'c1', { count: 3 }),
      failed(status, body, { 'X-Request-ID': SERVER_ID, 'X-AI-Quota-Period': 'day' })
    );

    await handleAIServiceError(error);

    expect(show).toHaveBeenCalledWith(expect.objectContaining({ correlationId: SERVER_ID }), expect.anything());
  });

  it('is the server id on the notification that earlier content is being shown instead', async () => {
    const show = ErrorNotification.showErrorNotification as jest.Mock;
    show.mockClear();
    const refused = {
      message: 'AI service unavailable',
      status_code: 503,
      error_type: 'service_unavailable',
      cached_content_available: true,
      cached_content: { questions: ['Q1'] },
    };
    const error = Object.assign(new Error(`Failed to generate: 503 ${JSON.stringify(refused)}`), { requestId: SERVER_ID });

    await handleAIServiceError(error);

    expect(show).toHaveBeenCalledWith(
      expect.objectContaining({ correlationId: SERVER_ID, message: 'Using previously generated content' }),
      expect.anything()
    );
  });
});
