/**
 * #836: the export page with a keyboard and nothing else.
 *
 * The format cards were `div onClick`, with no role, no tab stop and no key
 * handling, so a format could only be chosen with a mouse. And when the page's
 * data failed to load, a toast went by and an empty form was left, with no
 * formats to choose and nothing to press to try again.
 *
 * No test here clicks: every interaction is Tab, an arrow key, Space or Enter.
 */
import React, { Suspense } from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import ExportBookPage from '../page';
import { useSession } from '@/lib/auth-client';
import bookClient from '@/lib/api/bookClient';

expect.extend(toHaveNoViolations);

jest.mock('@/lib/auth-client');
jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), { success: jest.fn(), error: jest.fn(), warning: jest.fn(), info: jest.fn() }),
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

const format = (id: string, name: string, available = true) => ({
  format: id,
  name,
  description: `${name} for the test`,
  mime_type: 'application/octet-stream',
  extension: `.${id}`,
  available,
});

// EPUB is the one the server says it cannot make.
const FORMATS = {
  formats: [format('pdf', 'PDF'), format('docx', 'Word'), format('epub', 'EPUB', false), format('markdown', 'Markdown')],
};

// React's use(params) reads a pre-fulfilled thenable synchronously in jest (#194).
function fulfilledParams<T>(value: T): Promise<T> {
  const p = Promise.resolve(value) as Promise<T> & { status: string; value: T };
  p.status = 'fulfilled';
  p.value = value;
  return p;
}

function renderPage() {
  return render(
    <Suspense fallback={null}>
      <ExportBookPage params={fulfilledParams({ bookId: 'book-1' })} />
    </Suspense>
  );
}

async function tabTo(user: ReturnType<typeof userEvent.setup>, element: HTMLElement) {
  for (let presses = 0; presses < 20 && document.activeElement !== element; presses++) {
    await user.tab();
  }
  expect(element).toHaveFocus();
}

// The page-size radios are radios too: these are the ones in the format group.
const formatRadios = () => within(screen.getByRole('radiogroup', { name: /choose export format/i })).getAllByRole('radio');
const checked = () => formatRadios().filter(radio => radio.getAttribute('aria-checked') === 'true');

// The group moves focus a tick after the key goes down and chooses the radio only if the key is
// still down then, as a key under a finger is. user-event lets go at once, so the key is held here.
async function arrow(user: ReturnType<typeof userEvent.setup>, key: 'ArrowRight' | 'ArrowLeft', landsOn: string) {
  await user.keyboard(`{${key}>}`);
  await waitFor(() => expect(screen.getByRole('radio', { name: landsOn })).toHaveFocus());
  await user.keyboard(`{/${key}}`);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
  mockBookClient.getBook.mockResolvedValue({ id: 'book-1', title: 'Small Changes' } as never);
  mockBookClient.getExportFormats.mockResolvedValue(FORMATS as never);
  mockBookClient.getChaptersMetadata.mockResolvedValue({
    chapters: [{ id: 'c1', title: 'Why Habits Stick', status: 'draft', word_count: 1200 }],
  } as never);
  mockBookClient.exportDOCX.mockResolvedValue(new Blob(['docx']) as never);
});

describe('choosing an export format with the keyboard (#836)', () => {
  it('offers the formats as one group of radios, one checked, the unavailable one disabled', async () => {
    renderPage();

    const group = await screen.findByRole('radiogroup', { name: /choose export format/i });
    const radios = formatRadios();

    expect(radios.map(radio => radio.getAttribute('aria-checked'))).toEqual(['true', 'false', 'false', 'false']);
    expect(radios.map(radio => radio.getAttribute('aria-disabled'))).toEqual(['false', 'false', 'true', 'false']);
    radios.forEach(radio => expect(group).toContainElement(radio));
    expect(screen.getByRole('radio', { name: 'Word' })).toHaveAccessibleDescription('Word for the test');
  });

  it('is one tab stop, and the arrow keys choose', async () => {
    const user = userEvent.setup();
    renderPage();
    await tabTo(user, await screen.findByRole('radio', { name: 'PDF' }));

    await arrow(user, 'ArrowRight', 'Word');

    expect(checked()).toEqual([screen.getByRole('radio', { name: 'Word' })]);

    await user.tab();
    expect(screen.getByRole('radio', { name: 'Markdown' })).not.toHaveFocus();
  });

  it('passes over the format that is not available', async () => {
    const user = userEvent.setup();
    renderPage();
    await tabTo(user, await screen.findByRole('radio', { name: 'PDF' }));

    await arrow(user, 'ArrowRight', 'Word');
    await arrow(user, 'ArrowRight', 'Markdown');

    expect(checked()).toEqual([screen.getByRole('radio', { name: 'Markdown' })]);
    await arrow(user, 'ArrowLeft', 'Word');
    expect(checked()).toEqual([screen.getByRole('radio', { name: 'Word' })]);
  });

  it('exports the format chosen that way, with no click anywhere', async () => {
    const user = userEvent.setup();
    renderPage();
    await tabTo(user, await screen.findByRole('radio', { name: 'PDF' }));
    await arrow(user, 'ArrowRight', 'Word');

    await tabTo(user, screen.getByRole('button', { name: 'Export Book' }));
    await user.keyboard('{Enter}');

    await waitFor(() => expect(mockBookClient.exportDOCX).toHaveBeenCalledWith('book-1', { includeEmptyChapters: false }));
    expect(mockBookClient.exportPDF).not.toHaveBeenCalled();
  });

  it('has no axe violations', async () => {
    const { container } = renderPage();
    await screen.findByRole('radiogroup');

    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('when the export page cannot load (#836)', () => {
  it('says so in the page, and shows no form to fill in', async () => {
    mockBookClient.getExportFormats.mockRejectedValue(new Error('boom'));
    renderPage();

    const alert = await screen.findByRole('alert');

    expect(alert).toHaveTextContent(/could not load the export options/i);
    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Export Book' })).not.toBeInTheDocument();
  });

  it('loads again when Retry is pressed, from the keyboard', async () => {
    mockBookClient.getExportFormats.mockRejectedValueOnce(new Error('boom'));
    const user = userEvent.setup();
    renderPage();
    await tabTo(user, await screen.findByRole('button', { name: 'Retry' }));

    await user.keyboard('{Enter}');

    expect(await screen.findByRole('radiogroup')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(mockBookClient.getExportFormats).toHaveBeenCalledTimes(2);
  });

  it('shows that it is loading while the retry is under way, not an empty form', async () => {
    mockBookClient.getExportFormats.mockRejectedValueOnce(new Error('boom')).mockReturnValueOnce(new Promise(() => {}) as never);
    const user = userEvent.setup();
    renderPage();
    await tabTo(user, await screen.findByRole('button', { name: 'Retry' }));

    await user.keyboard('{Enter}');

    expect(await screen.findByText('Loading export options...')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Export Book' })).not.toBeInTheDocument();
  });

  it('shows the alert again when the retry fails too', async () => {
    mockBookClient.getExportFormats.mockRejectedValue(new Error('boom'));
    const user = userEvent.setup();
    renderPage();
    await tabTo(user, await screen.findByRole('button', { name: 'Retry' }));

    await user.keyboard('{Enter}');

    await waitFor(() => expect(mockBookClient.getExportFormats).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    mockBookClient.getExportFormats.mockRejectedValue(new Error('boom'));
    const { container } = renderPage();
    await screen.findByRole('alert');

    expect(await axe(container)).toHaveNoViolations();
  });
});
