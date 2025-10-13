import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { LoadingStateManager } from '../LoadingStateManager';

describe('LoadingStateManager', () => {
  // Helper to advance timers
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Basic Rendering', () => {
    it('should not render when isLoading is false', () => {
      const { container } = render(
        <LoadingStateManager isLoading={false} operation="Test Operation" />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should delay rendering for 200ms to avoid flicker', () => {
      render(<LoadingStateManager isLoading={true} operation="Test Operation" />);

      // Should not be visible immediately
      expect(screen.queryByText('Test Operation')).not.toBeInTheDocument();

      // Should be visible after 200ms
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByText('Test Operation')).toBeInTheDocument();
    });

    it('should render operation name', () => {
      render(<LoadingStateManager isLoading={true} operation="Generating TOC" />);

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByText('Generating TOC')).toBeInTheDocument();
    });

    it('should render optional message', () => {
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          message="Processing your request..."
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByText('Processing your request...')).toBeInTheDocument();
    });
  });

  describe('Progress Indicator', () => {
    it('should not render progress bar when progress is undefined', () => {
      render(<LoadingStateManager isLoading={true} operation="Test Operation" />);

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    it('should render progress bar when progress is provided', () => {
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          progress={50}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toBeInTheDocument();
      expect(progressbar).toHaveAttribute('aria-valuenow', '50');
      expect(screen.getByText('50% complete')).toBeInTheDocument();
    });

    it('should clamp progress to 0-100 range', () => {
      const { rerender } = render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          progress={-10}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      let progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '0');

      rerender(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          progress={150}
        />
      );

      progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '100');
    });

    it('should update progress bar width based on progress value', () => {
      const { rerender } = render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          progress={25}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      let progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveStyle({ width: '25%' });

      rerender(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          progress={75}
        />
      );

      progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveStyle({ width: '75%' });
    });
  });

  describe('Time Estimation', () => {
    it('should display estimated time in seconds', () => {
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          estimatedTime={15000} // 15 seconds
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      // Time estimate shown without progress bar
      expect(screen.getByText(/~15 seconds/i)).toBeInTheDocument();
    });

    it('should countdown estimated time', () => {
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          estimatedTime={5000} // 5 seconds
          progress={50}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByText(/~5s remaining/i)).toBeInTheDocument();

      // Advance by 1 second
      act(() => {
        jest.advanceTimersByTime(1000);
      });

      expect(screen.getByText(/~4s remaining/i)).toBeInTheDocument();
    });

    it('should display time estimate without progress bar', () => {
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          estimatedTime={10000}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByText(/~10 seconds/i)).toBeInTheDocument();
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    it('should handle singular "second" correctly', () => {
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          estimatedTime={1000}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByText(/~1 second$/i)).toBeInTheDocument();
    });

    it('should not go below 0 seconds', () => {
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          estimatedTime={500}
          progress={90}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      // Should show initial estimate
      expect(screen.getByText(/~1s remaining/i)).toBeInTheDocument();

      // Advance past the estimated time
      act(() => {
        jest.advanceTimersByTime(1000);
      });

      // Time remaining text should not be present when 0
      expect(screen.queryByText(/remaining/i)).not.toBeInTheDocument();
    });
  });

  describe('Cancel Functionality', () => {
    it('should not render cancel button when onCancel is undefined', () => {
      render(<LoadingStateManager isLoading={true} operation="Test Operation" />);

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
    });

    it('should render cancel button when onCancel is provided', () => {
      const onCancel = jest.fn();
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          onCancel={onCancel}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('should call onCancel when cancel button is clicked', async () => {
      const onCancel = jest.fn();
      const user = userEvent.setup({ delay: null });

      render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          onCancel={onCancel}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      const cancelButton = screen.getByText('Cancel');
      await user.click(cancelButton);

      expect(onCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe('Inline Variant', () => {
    it('should render smaller when inline is true', () => {
      const { container } = render(
        <LoadingStateManager isLoading={true} operation="Test Operation" inline />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      const loaderIcon = container.querySelector('svg');
      expect(loaderIcon).toHaveClass('h-8', 'w-8');
    });

    it('should render larger when inline is false', () => {
      const { container } = render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          inline={false}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      const loaderIcon = container.querySelector('svg');
      expect(loaderIcon).toHaveClass('h-12', 'w-12');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      const { container } = render(
        <LoadingStateManager isLoading={true} operation="Test Operation" />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      const statusContainer = container.querySelector('[role="status"]');
      expect(statusContainer).toBeInTheDocument();
      expect(statusContainer).toHaveAttribute('aria-live', 'polite');
      expect(statusContainer).toHaveAttribute('aria-busy', 'true');
    });

    it('should have aria-label on spinner', () => {
      render(<LoadingStateManager isLoading={true} operation="Generating TOC" />);

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByLabelText('Loading: Generating TOC')).toBeInTheDocument();
    });

    it('should have aria-label on progress bar', () => {
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Generating TOC"
          progress={50}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-label', 'Generating TOC progress');
    });

    it('should have aria-label on cancel button', () => {
      const onCancel = jest.fn();
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Generating TOC"
          onCancel={onCancel}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByLabelText('Cancel Generating TOC')).toBeInTheDocument();
    });
  });

  describe('Custom className', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          className="custom-class"
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(container.firstChild).toHaveClass('custom-class');
    });
  });

  describe('Integration Tests', () => {
    it('should handle complete loading lifecycle', () => {
      const { rerender } = render(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          progress={0}
          estimatedTime={5000}
        />
      );

      // Wait for initial render
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(screen.getByText('Test Operation')).toBeInTheDocument();
      expect(screen.getByText('0% complete')).toBeInTheDocument();

      // Update progress
      rerender(
        <LoadingStateManager
          isLoading={true}
          operation="Test Operation"
          progress={50}
          estimatedTime={2500}
        />
      );

      expect(screen.getByText('50% complete')).toBeInTheDocument();

      // Complete
      rerender(
        <LoadingStateManager
          isLoading={false}
          operation="Test Operation"
          progress={100}
        />
      );

      expect(screen.queryByText('Test Operation')).not.toBeInTheDocument();
    });

    it('should display all features together', () => {
      const onCancel = jest.fn();
      render(
        <LoadingStateManager
          isLoading={true}
          operation="Generating TOC"
          progress={75}
          estimatedTime={5000}
          message="Analyzing your summary and generating chapter structure..."
          onCancel={onCancel}
        />
      );

      act(() => {
        jest.advanceTimersByTime(200);
      });

      // Check all elements are present
      expect(screen.getByText('Generating TOC')).toBeInTheDocument();
      expect(screen.getByText(/Analyzing your summary/i)).toBeInTheDocument();
      expect(screen.getByText('75% complete')).toBeInTheDocument();
      expect(screen.getByText(/5s remaining/i)).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
  });
});
