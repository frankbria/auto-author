/**
 * Tests for src/components/chapters/TabOverflowMenu.tsx
 * Covers the component's 3 code paths:
 *  1. Returns null when not visible
 *  2. Returns null when chapters array is empty
 *  3. Renders the overflow dropdown with chapter items and handles selection
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { TabOverflowMenu } from '@/components/chapters/TabOverflowMenu'
import { ChapterTabMetadata, ChapterStatus } from '@/types/chapter-tabs'

// Build a minimal ChapterTabMetadata fixture
const makeChapter = (overrides: Partial<ChapterTabMetadata> = {}): ChapterTabMetadata => ({
  id: 'ch-1',
  title: 'Chapter One',
  status: ChapterStatus.DRAFT,
  word_count: 100,
  last_modified: '2024-01-01T00:00:00Z',
  estimated_reading_time: 1,
  order: 0,
  level: 1,
  has_content: true,
  ...overrides,
})

const defaultProps = {
  chapters: [makeChapter()],
  activeChapterId: null,
  onTabSelect: jest.fn(),
  visible: true,
  onVisibilityChange: jest.fn(),
}

beforeEach(() => {
  jest.clearAllMocks()
})

describe('TabOverflowMenu', () => {
  describe('null return paths', () => {
    it('renders nothing when visible=false', () => {
      const { container } = render(
        <TabOverflowMenu {...defaultProps} visible={false} />
      )
      expect(container).toBeEmptyDOMElement()
    })

    it('renders nothing when chapters is empty', () => {
      const { container } = render(
        <TabOverflowMenu {...defaultProps} chapters={[]} />
      )
      expect(container).toBeEmptyDOMElement()
    })

    it('renders nothing when both visible=false and chapters is empty', () => {
      const { container } = render(
        <TabOverflowMenu {...defaultProps} visible={false} chapters={[]} />
      )
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('visible with chapters', () => {
    it('renders the trigger button when visible with chapters', () => {
      render(<TabOverflowMenu {...defaultProps} />)
      // With DropdownMenuTrigger asChild + Button, Radix Slot merges data-slot
      // so the rendered element carries data-slot="dropdown-menu-trigger".
      // When the menu is open Radix also sets aria-hidden on the trigger (focus
      // trap), so we bypass the accessible tree filter with { hidden: true }.
      expect(screen.getAllByRole('button', { hidden: true }).length).toBeGreaterThan(0)
    })

    it('renders chapter items in the dropdown (menu is open via visible=true)', () => {
      const chapters = [
        makeChapter({ id: 'ch-1', title: 'Intro', order: 0 }),
        makeChapter({ id: 'ch-2', title: 'Chapter Two', order: 1 }),
      ]
      render(<TabOverflowMenu {...defaultProps} chapters={chapters} />)

      // The DropdownMenu is controlled open via `open={visible}` (visible=true)
      expect(screen.getByText('Intro')).toBeInTheDocument()
      expect(screen.getByText('Chapter Two')).toBeInTheDocument()
    })

    it('calls onTabSelect with the chapter id when an item is clicked', () => {
      const onTabSelect = jest.fn()
      const chapters = [makeChapter({ id: 'ch-42', title: 'The Answer' })]
      render(
        <TabOverflowMenu
          {...defaultProps}
          chapters={chapters}
          onTabSelect={onTabSelect}
        />
      )

      fireEvent.click(screen.getByText('The Answer'))
      expect(onTabSelect).toHaveBeenCalledWith('ch-42')
      expect(onTabSelect).toHaveBeenCalledTimes(1)
    })

    it('passes onVisibilityChange as the dropdown onOpenChange prop', () => {
      // The component renders a controlled DropdownMenu (open={visible}).
      // We verify it renders at all with a custom handler assigned.
      const onVisibilityChange = jest.fn()
      const { container } = render(
        <TabOverflowMenu {...defaultProps} onVisibilityChange={onVisibilityChange} />
      )
      // The dropdown is open and content is rendered (menu is visible)
      expect(container.firstChild).not.toBeNull()
      expect(screen.getByText('Chapter One')).toBeInTheDocument()
    })

    it('renders multiple chapters as separate items', () => {
      const chapters = [
        makeChapter({ id: 'a', title: 'Alpha' }),
        makeChapter({ id: 'b', title: 'Beta' }),
        makeChapter({ id: 'c', title: 'Gamma' }),
      ]
      render(<TabOverflowMenu {...defaultProps} chapters={chapters} />)

      expect(screen.getByText('Alpha')).toBeInTheDocument()
      expect(screen.getByText('Beta')).toBeInTheDocument()
      expect(screen.getByText('Gamma')).toBeInTheDocument()
    })

    it('applies accent background class to the active chapter item', () => {
      const chapters = [
        makeChapter({ id: 'active-ch', title: 'Active Chapter' }),
        makeChapter({ id: 'other-ch', title: 'Other Chapter' }),
      ]
      render(
        <TabOverflowMenu
          {...defaultProps}
          chapters={chapters}
          activeChapterId="active-ch"
        />
      )

      const activeItem = screen.getByText('Active Chapter').closest('[data-slot="dropdown-menu-item"]')
      // Split on whitespace so 'bg-accent' is checked as an exact token
      // (not matching 'focus:bg-accent' which is in every item's base classes)
      const activeClasses = (activeItem?.className ?? '').split(/\s+/)
      expect(activeClasses).toContain('bg-accent')

      const otherItem = screen.getByText('Other Chapter').closest('[data-slot="dropdown-menu-item"]')
      const otherClasses = (otherItem?.className ?? '').split(/\s+/)
      expect(otherClasses).not.toContain('bg-accent')
    })

    it('calls correct onTabSelect for each individual chapter when clicked', () => {
      const onTabSelect = jest.fn()
      const chapters = [
        makeChapter({ id: 'ch-x', title: 'Chapter X' }),
        makeChapter({ id: 'ch-y', title: 'Chapter Y' }),
      ]
      render(
        <TabOverflowMenu
          {...defaultProps}
          chapters={chapters}
          onTabSelect={onTabSelect}
        />
      )

      fireEvent.click(screen.getByText('Chapter Y'))
      expect(onTabSelect).toHaveBeenCalledWith('ch-y')

      fireEvent.click(screen.getByText('Chapter X'))
      expect(onTabSelect).toHaveBeenCalledWith('ch-x')

      expect(onTabSelect).toHaveBeenCalledTimes(2)
    })
  })
})
