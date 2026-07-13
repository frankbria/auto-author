/**
 * Tests for TocGenerating — the wizard's generation-in-progress step.
 * Rehomed from src/__tests__/TocGenerationWizard.test.tsx (issue #200) and
 * strengthened: renders the real LoadingStateManager and progress tracker
 * instead of mocking them.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import TocGenerating from '../TocGenerating';

describe('TocGenerating', () => {
  it('shows the generation loading state with all processing steps', async () => {
    render(<TocGenerating />);

    // LoadingStateManager delays rendering 200ms to avoid flicker
    expect(
      await screen.findByText(/Generating Your Table of Contents/i)
    ).toBeInTheDocument();
    expect(screen.getByText('AI Processing Steps')).toBeInTheDocument();

    // All six step labels render (the current step also appears in the banner)
    for (const step of [
      'Analyzing your responses...',
      'Identifying key themes and topics...',
      'Structuring chapters and sections...',
      'Creating subchapter hierarchies...',
      'Optimizing content flow...',
      'Finalizing table of contents...',
    ]) {
      expect(screen.getAllByText(step).length).toBeGreaterThanOrEqual(1);
    }
  });
});
