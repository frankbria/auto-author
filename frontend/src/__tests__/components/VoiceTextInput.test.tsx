import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VoiceTextInput } from '@/components/chapters/VoiceTextInput';
import { setupSpeechRecognitionMock } from '../mocks/speechRecognition';

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
      
      // Wait for error to appear
      await waitFor(() => {
        expect(screen.getByText('Error recording audio: network')).toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });
  
  describe('Auto-save Integration', () => {
    it('should auto-save voice transcriptions', async () => {
      jest.useFakeTimers();
      const user = userEvent.setup({ delay: null });
      const mockSave = jest.fn();
      
      setupSpeechRecognitionMock({
        transcript: 'Auto-save voice content.',
        delay: 100
      });
      
      const { rerender } = render(
        <VoiceTextInput 
          value=""
          mode="voice"
          onChange={mockOnChange}
          onAutoSave={mockSave}
        />
      );
      
      const recordButton = screen.getByRole('button', { name: /start voice recording/i });
      
      await act(async () => {
        await user.click(recordButton);
      });
      
      // Wait for transcription
      await act(async () => {
        jest.advanceTimersByTime(200);
      });
      
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith('Auto-save voice content. ');
      });
      
      // Rerender with the new value to trigger auto-save effect
      rerender(
        <VoiceTextInput 
          value="Auto-save voice content. "
          mode="voice"
          onChange={mockOnChange}
          onAutoSave={mockSave}
        />
      );
      
      // Auto-save should trigger after delay
      await act(async () => {
        jest.advanceTimersByTime(3000);
      });
      
      expect(mockSave).toHaveBeenCalledWith('Auto-save voice content. ');
      
      jest.useRealTimers();
    });
  });
});
