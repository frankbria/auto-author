import { useState } from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VoiceTextInput } from '@/components/chapters/VoiceTextInput';
import { setupSpeechRecognitionMock } from '../mocks/speechRecognition';

// Controlled host: feeds onChange back as value, the way real consumers
// (QuestionDisplay) do. Exposes the accumulated value for assertions.
function ControlledVoiceInput() {
  const [value, setValue] = useState('');
  return (
    <>
      <VoiceTextInput value={value} onChange={setValue} mode="voice" />
      <span data-testid="accumulated-value">{value}</span>
    </>
  );
}

describe('VoiceTextInput Component', () => {
  const mockOnChange = jest.fn();
  const mockOnModeChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    setupSpeechRecognitionMock();
  });

  describe('Mode Toggle', () => {
    it('should toggle between text and voice modes', async () => {
      const user = userEvent.setup();
      render(
        <VoiceTextInput
          value=""
          onChange={mockOnChange}
          onModeChange={mockOnModeChange}
        />
      );

      // Start in text mode
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /start voice recording/i })).not.toBeInTheDocument();

      // Toggle to voice mode
      const toggleButton = screen.getByRole('button', { name: /switch to voice/i });
      await user.click(toggleButton);

      expect(mockOnModeChange).toHaveBeenCalledWith('voice');
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start voice recording/i })).toBeInTheDocument();
    });

    it('should preserve content when switching modes', async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <VoiceTextInput
          value="Existing content"
          mode="text"
          onChange={mockOnChange}
        />
      );

      // Switch to voice mode
      const toggleButton = screen.getByRole('button', { name: /switch to voice/i });
      await user.click(toggleButton);

      // Rerender with voice mode
      rerender(
        <VoiceTextInput
          value="Existing content"
          mode="voice"
          onChange={mockOnChange}
        />
      );

      // Content should be preserved
      expect(screen.getByText(/Existing content/)).toBeInTheDocument();
    });
  });

  describe('Voice Recording', () => {
    it('should handle successful voice recording', async () => {
      const user = userEvent.setup();
      const mockRecognition = setupSpeechRecognitionMock({
        transcript: 'This is a voice test.',
        delay: 300
      });

      render(
        <VoiceTextInput
          value=""
          mode="voice"
          onChange={mockOnChange}
        />
      );

      const recordButton = screen.getByRole('button', { name: /start voice recording/i });

      await act(async () => {
        await user.click(recordButton);
      });

      // Should show recording state
      expect(screen.getByText(/Recording started - speak now/i)).toBeInTheDocument();
      expect(mockRecognition.start).toHaveBeenCalled();

      // Wait for transcription
      await act(async () => {
        await waitFor(() => {
          expect(mockOnChange).toHaveBeenCalledWith('This is a voice test. ');
        }, { timeout: 1000 });
      });
    });

    it('should handle voice recording errors', async () => {
      const user = userEvent.setup();
      const mockRecognition = setupSpeechRecognitionMock({
        shouldError: true,
        delay: 100
      });

      render(
        <VoiceTextInput
          value=""
          mode="voice"
          onChange={mockOnChange}
        />
      );

      const recordButton = screen.getByRole('button', { name: /start voice recording/i });

      await act(async () => {
        await user.click(recordButton);
      });

      // Wait for recognition to start
      expect(mockRecognition.start).toHaveBeenCalled();

      // A real failure still surfaces — but as actionable copy, not the raw
      // code. #348 replaced "Error recording audio: network" because echoing the
      // API's code tells the user nothing about what to do. getAllByText because
      // the message renders in both the banner and the sr-only live region.
      await waitFor(() => {
        expect(
          screen.getAllByText(/needs an internet connection/i).length
        ).toBeGreaterThan(0);
      }, { timeout: 2000 });
      expect(screen.queryByText(/Error recording audio/i)).not.toBeInTheDocument();
    });
  });

  describe('Continuous dictation (accumulation)', () => {
    it('appends every finalized segment instead of overwriting the previous one (#330)', async () => {
      const user = userEvent.setup();
      const mockRecognition = setupSpeechRecognitionMock({ delay: 100 });

      render(<ControlledVoiceInput />);

      await act(async () => {
        await user.click(screen.getByRole('button', { name: /start voice recording/i }));
      });
      expect(mockRecognition.start).toHaveBeenCalled();

      // Two separate finalized segments, as continuous recognition delivers them.
      act(() => {
        mockRecognition.emitResult({ transcript: 'First sentence.', isFinal: true });
      });
      await waitFor(() => {
        expect(screen.getByTestId('accumulated-value')).toHaveTextContent('First sentence.');
      });

      act(() => {
        mockRecognition.emitResult({ transcript: 'Second sentence.', isFinal: true });
      });

      // Both segments must survive — the stale-closure bug kept only the last.
      await waitFor(() => {
        expect(screen.getByTestId('accumulated-value')).toHaveTextContent(
          'First sentence. Second sentence.'
        );
      });
    });

    it('keeps both segments when two finals arrive before React can re-render (#384)', async () => {
      const user = userEvent.setup();
      // A delay far beyond the test's lifetime so the mock's own auto-emit never
      // fires: every result here is driven explicitly, making the test immune to
      // scheduling — which is the whole point of #384.
      const mockRecognition = setupSpeechRecognitionMock({ delay: 1_000_000 });

      render(<ControlledVoiceInput />);

      await act(async () => {
        await user.click(screen.getByRole('button', { name: /start voice recording/i }));
      });

      // Continuous recognition can deliver two finalized segments back-to-back,
      // faster than React commits the first onChange. Emitting both inside ONE
      // act() reproduces that without depending on timer scheduling: the effect
      // that syncs valueRef cannot run between them, so a handler reading only
      // the effect-synced ref sees a stale value and drops the first segment.
      act(() => {
        mockRecognition.emitResult({ transcript: 'First final.', isFinal: true });
        mockRecognition.emitResult({ transcript: 'Second final.', isFinal: true });
      });

      await waitFor(() => {
        expect(screen.getByTestId('accumulated-value')).toHaveTextContent(
          'First final. Second final.'
        );
      });
    });

    it('covers interim + multiple final results via the mock sequence', async () => {
      const user = userEvent.setup();
      const mockRecognition = setupSpeechRecognitionMock({
        delay: 10,
        sequence: [
          { transcript: 'Interim words', isFinal: false },
          { transcript: 'First final.', isFinal: true },
          { transcript: 'Second final.', isFinal: true },
        ],
      });

      render(<ControlledVoiceInput />);

      await act(async () => {
        await user.click(screen.getByRole('button', { name: /start voice recording/i }));
      });
      expect(mockRecognition.start).toHaveBeenCalled();

      await waitFor(() => {
        expect(screen.getByTestId('accumulated-value')).toHaveTextContent(
          'First final. Second final.'
        );
      });
    });
  });

  describe('Voice Content Handling', () => {
    it('should call onChange with transcribed voice content', async () => {
      const user = userEvent.setup();
      const mockRecognition = setupSpeechRecognitionMock({
        transcript: 'Voice transcription test.',
        delay: 100
      });

      render(
        <VoiceTextInput
          value=""
          mode="voice"
          onChange={mockOnChange}
        />
      );

      const recordButton = screen.getByRole('button', { name: /start voice recording/i });

      await act(async () => {
        await user.click(recordButton);
      });

      expect(mockRecognition.start).toHaveBeenCalled();

      // Wait for transcription to complete and onChange to be called
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith('Voice transcription test. ');
      }, { timeout: 1000 });
    });
  });
});
