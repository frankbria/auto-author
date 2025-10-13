import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ProgressIndicator } from '../ProgressIndicator';

describe('ProgressIndicator', () => {
  describe('Basic Rendering', () => {
    it('should render with current and total counts', () => {
      render(<ProgressIndicator current={5} total={10} unit="chapters" />);

      expect(screen.getByText('Processing 5 of 10 chapters')).toBeInTheDocument();
      expect(screen.getByText('5 / 10')).toBeInTheDocument();
    });

    it('should render with different units', () => {
      const { rerender } = render(
        <ProgressIndicator current={3} total={8} unit="pages" />
      );

      expect(screen.getByText('Processing 3 of 8 pages')).toBeInTheDocument();

      rerender(<ProgressIndicator current={15} total={20} unit="items" />);

      expect(screen.getByText('Processing 15 of 20 items')).toBeInTheDocument();
    });

    it('should render custom message when provided', () => {
      render(
        <ProgressIndicator
          current={3}
          total={10}
          unit="chapters"
          message="Analyzing chapter 3 of 10"
        />
      );

      expect(screen.getByText('Analyzing chapter 3 of 10')).toBeInTheDocument();
      expect(screen.queryByText('Processing')).not.toBeInTheDocument();
    });
  });

  describe('Progress Calculation', () => {
    it('should calculate percentage correctly', () => {
      render(<ProgressIndicator current={5} total={10} unit="chapters" />);

      expect(screen.getByText('50%')).toBeInTheDocument();

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '50');
    });

    it('should round percentage to nearest integer', () => {
      render(<ProgressIndicator current={1} total={3} unit="items" />);

      // 1/3 = 33.333... should round to 33
      expect(screen.getByText('33%')).toBeInTheDocument();
    });

    it('should handle 0% progress', () => {
      render(<ProgressIndicator current={0} total={10} unit="chapters" />);

      expect(screen.getByText('0%')).toBeInTheDocument();

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '0');
    });

    it('should handle 100% progress', () => {
      render(<ProgressIndicator current={10} total={10} unit="chapters" />);

      expect(screen.getByText('100%')).toBeInTheDocument();

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '100');
    });

    it('should handle total of 0 gracefully', () => {
      render(<ProgressIndicator current={0} total={0} unit="items" />);

      expect(screen.getByText('0%')).toBeInTheDocument();
      expect(screen.getByText('0 / 0')).toBeInTheDocument();
    });

    it('should clamp percentage to 0-100 range', () => {
      const { rerender } = render(
        <ProgressIndicator current={15} total={10} unit="items" />
      );

      // Over 100% should clamp to 100%
      expect(screen.getByText('100%')).toBeInTheDocument();

      rerender(<ProgressIndicator current={-5} total={10} unit="items" />);

      // Negative should clamp to 0%
      expect(screen.getByText('0%')).toBeInTheDocument();
    });
  });

  describe('Show Percentage Option', () => {
    it('should show percentage by default', () => {
      render(<ProgressIndicator current={5} total={10} unit="chapters" />);

      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('should hide percentage when showPercentage is false', () => {
      render(
        <ProgressIndicator
          current={5}
          total={10}
          unit="chapters"
          showPercentage={false}
        />
      );

      expect(screen.queryByText('50%')).not.toBeInTheDocument();
      expect(screen.getByText('Processing 5 of 10 chapters')).toBeInTheDocument();
    });
  });

  describe('Size Variants', () => {
    it('should render default size by default', () => {
      const { container } = render(
        <ProgressIndicator current={5} total={10} unit="chapters" />
      );

      const progressBar = container.querySelector('.h-2');
      expect(progressBar).toBeInTheDocument();
    });

    it('should render small size when size is "sm"', () => {
      const { container } = render(
        <ProgressIndicator current={5} total={10} unit="chapters" size="sm" />
      );

      const progressBar = container.querySelector('.h-1');
      expect(progressBar).toBeInTheDocument();
    });

    it('should render large size when size is "lg"', () => {
      const { container } = render(
        <ProgressIndicator current={5} total={10} unit="chapters" size="lg" />
      );

      const progressBar = container.querySelector('.h-3');
      expect(progressBar).toBeInTheDocument();
    });
  });

  describe('Progress Bar Styling', () => {
    it('should update progress bar width based on percentage', () => {
      const { rerender } = render(
        <ProgressIndicator current={2} total={10} unit="items" />
      );

      let progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveStyle({ width: '20%' });

      rerender(<ProgressIndicator current={8} total={10} unit="items" />);

      progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveStyle({ width: '80%' });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      const { container } = render(
        <ProgressIndicator current={5} total={10} unit="chapters" />
      );

      const statusContainer = container.querySelector('[role="status"]');
      expect(statusContainer).toBeInTheDocument();
      expect(statusContainer).toHaveAttribute('aria-live', 'polite');
    });

    it('should have progressbar role with correct attributes', () => {
      render(<ProgressIndicator current={7} total={10} unit="items" />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '70');
      expect(progressbar).toHaveAttribute('aria-valuemin', '0');
      expect(progressbar).toHaveAttribute('aria-valuemax', '100');
    });

    it('should have descriptive aria-label', () => {
      render(<ProgressIndicator current={3} total={10} unit="chapters" />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute(
        'aria-label',
        'Processing 3 of 10 chapters - 30% complete'
      );
    });

    it('should update aria-label with custom message', () => {
      render(
        <ProgressIndicator
          current={5}
          total={10}
          unit="pages"
          message="Analyzing page 5 of 10"
        />
      );

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute(
        'aria-label',
        'Analyzing page 5 of 10 - 50% complete'
      );
    });
  });

  describe('Custom className', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <ProgressIndicator
          current={5}
          total={10}
          unit="chapters"
          className="custom-class"
        />
      );

      expect(container.firstChild).toHaveClass('custom-class');
    });
  });

  describe('Compact Variant', () => {
    it('should render compact variant with reduced content', () => {
      render(
        <ProgressIndicator.Compact current={5} total={10} unit="chapters" />
      );

      // Should show progress bar and count
      expect(screen.getByText('5/10')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();

      // Should NOT show full message
      expect(screen.queryByText('Processing')).not.toBeInTheDocument();
    });

    it('should have proper accessibility in compact mode', () => {
      render(
        <ProgressIndicator.Compact current={3} total={10} unit="items" />
      );

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute(
        'aria-label',
        'Processing 3 of 10 items - 30% complete'
      );
    });

    it('should calculate progress correctly in compact mode', () => {
      render(
        <ProgressIndicator.Compact current={7} total={10} unit="pages" />
      );

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '70');
      expect(progressbar).toHaveStyle({ width: '70%' });
    });
  });

  describe('Edge Cases', () => {
    it('should handle very large numbers', () => {
      render(<ProgressIndicator current={999} total={1000} unit="items" />);

      expect(screen.getByText('Processing 999 of 1000 items')).toBeInTheDocument();
      expect(screen.getByText('999 / 1000')).toBeInTheDocument();
    });

    it('should handle decimal current values', () => {
      render(<ProgressIndicator current={5.7} total={10} unit="items" />);

      // Should calculate percentage from decimal
      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '57');
    });

    it('should handle different unit capitalizations', () => {
      render(<ProgressIndicator current={1} total={5} unit="Chapters" />);

      expect(screen.getByText('Processing 1 of 5 Chapters')).toBeInTheDocument();
    });
  });

  describe('Integration Tests', () => {
    it('should update smoothly when progress changes', () => {
      const { rerender } = render(
        <ProgressIndicator current={0} total={10} unit="chapters" />
      );

      expect(screen.getByText('0%')).toBeInTheDocument();

      rerender(<ProgressIndicator current={3} total={10} unit="chapters" />);
      expect(screen.getByText('30%')).toBeInTheDocument();

      rerender(<ProgressIndicator current={7} total={10} unit="chapters" />);
      expect(screen.getByText('70%')).toBeInTheDocument();

      rerender(<ProgressIndicator current={10} total={10} unit="chapters" />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('should display all features together', () => {
      const { container } = render(
        <ProgressIndicator
          current={5}
          total={10}
          unit="chapters"
          showPercentage={true}
          message="Analyzing chapter content"
          size="lg"
          className="custom-progress"
        />
      );

      expect(screen.getByText('Analyzing chapter content')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(screen.getByText('5 / 10')).toBeInTheDocument();

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '50');

      // The custom class is on the root element
      expect(container.firstChild).toHaveClass('custom-progress');
    });
  });
});
