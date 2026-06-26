/**
 * Tests for src/components/ui/sheet.tsx
 * Exercises all 8 exported wrappers: Sheet, SheetTrigger, SheetClose,
 * SheetContent (all 4 side variants), SheetHeader, SheetFooter, SheetTitle,
 * SheetDescription.
 *
 * Note: @radix-ui/react-dialog Portal is mocked globally in jest.setup.ts
 * to render children inline (no createPortal), so SheetContent renders
 * directly into the container.
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'

describe('Sheet — exported wrapper components', () => {
  describe('Sheet (Root) and basic children', () => {
    it('renders an open sheet with all main sub-components', () => {
      render(
        <Sheet open>
          <SheetTrigger>Open</SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Sheet Title</SheetTitle>
              <SheetDescription>Sheet description text</SheetDescription>
            </SheetHeader>
            <p>Body content</p>
            <SheetFooter>
              {/* Use "Dismiss" to avoid collision with the built-in sr-only "Close" span in SheetContent */}
              <SheetClose>Dismiss</SheetClose>
            </SheetFooter>
          </SheetContent>
        </Sheet>
      )

      expect(screen.getByText('Sheet Title')).toBeInTheDocument()
      expect(screen.getByText('Sheet description text')).toBeInTheDocument()
      expect(screen.getByText('Body content')).toBeInTheDocument()
      expect(screen.getByText('Dismiss')).toBeInTheDocument()
    })

    it('applies data-slot attributes to content and structural components', () => {
      render(
        <Sheet open>
          <SheetTrigger>Trigger</SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Title</SheetTitle>
              <SheetDescription>Desc</SheetDescription>
            </SheetHeader>
            <SheetFooter>
              <SheetClose>X</SheetClose>
            </SheetFooter>
          </SheetContent>
        </Sheet>
      )

      // Note: SheetPrimitive.Root is a context provider and does NOT render a
      // DOM element — data-slot="sheet" therefore does not appear in the DOM.
      expect(document.querySelector('[data-slot="sheet-trigger"]')).toBeInTheDocument()
      expect(document.querySelector('[data-slot="sheet-content"]')).toBeInTheDocument()
      expect(document.querySelector('[data-slot="sheet-header"]')).toBeInTheDocument()
      expect(document.querySelector('[data-slot="sheet-footer"]')).toBeInTheDocument()
      expect(document.querySelector('[data-slot="sheet-title"]')).toBeInTheDocument()
      expect(document.querySelector('[data-slot="sheet-description"]')).toBeInTheDocument()
    })
  })

  describe('SheetTrigger', () => {
    it('opens the sheet when clicked', () => {
      render(
        <Sheet>
          <SheetTrigger>Open Sheet</SheetTrigger>
          <SheetContent>
            <SheetTitle>Opened</SheetTitle>
          </SheetContent>
        </Sheet>
      )

      expect(screen.queryByText('Opened')).not.toBeInTheDocument()
      fireEvent.click(screen.getByText('Open Sheet'))
      expect(screen.getByText('Opened')).toBeInTheDocument()
    })
  })

  describe('SheetClose', () => {
    it('renders a close button inside open sheet', () => {
      render(
        <Sheet open>
          <SheetContent>
            <SheetTitle>Title</SheetTitle>
            <SheetClose>Dismiss</SheetClose>
          </SheetContent>
        </Sheet>
      )

      expect(screen.getByText('Dismiss')).toBeInTheDocument()
    })
  })

  describe('SheetContent — side variants', () => {
    it('renders with side="right" (default)', () => {
      render(
        <Sheet open>
          <SheetContent side="right">
            <SheetTitle>Right</SheetTitle>
          </SheetContent>
        </Sheet>
      )
      const content = document.querySelector('[data-slot="sheet-content"]')
      expect(content).toBeInTheDocument()
      expect(content?.className).toMatch(/slide-in-from-right/)
    })

    it('renders with side="left"', () => {
      render(
        <Sheet open>
          <SheetContent side="left">
            <SheetTitle>Left</SheetTitle>
          </SheetContent>
        </Sheet>
      )
      const content = document.querySelector('[data-slot="sheet-content"]')
      expect(content?.className).toMatch(/slide-in-from-left/)
    })

    it('renders with side="top"', () => {
      render(
        <Sheet open>
          <SheetContent side="top">
            <SheetTitle>Top</SheetTitle>
          </SheetContent>
        </Sheet>
      )
      const content = document.querySelector('[data-slot="sheet-content"]')
      expect(content?.className).toMatch(/slide-in-from-top/)
    })

    it('renders with side="bottom"', () => {
      render(
        <Sheet open>
          <SheetContent side="bottom">
            <SheetTitle>Bottom</SheetTitle>
          </SheetContent>
        </Sheet>
      )
      const content = document.querySelector('[data-slot="sheet-content"]')
      expect(content?.className).toMatch(/slide-in-from-bottom/)
    })

    it('accepts a custom className', () => {
      render(
        <Sheet open>
          <SheetContent className="my-custom-class">
            <SheetTitle>Custom</SheetTitle>
          </SheetContent>
        </Sheet>
      )
      const content = document.querySelector('[data-slot="sheet-content"]')
      expect(content?.className).toMatch(/my-custom-class/)
    })
  })

  describe('SheetHeader', () => {
    it('renders children in a flex column', () => {
      const { container } = render(
        <SheetHeader>
          <span>Header child</span>
        </SheetHeader>
      )
      const header = container.querySelector('[data-slot="sheet-header"]')
      expect(header).toBeInTheDocument()
      expect(header?.className).toMatch(/flex/)
      expect(screen.getByText('Header child')).toBeInTheDocument()
    })

    it('merges a custom className', () => {
      const { container } = render(<SheetHeader className="extra">content</SheetHeader>)
      expect(container.querySelector('[data-slot="sheet-header"]')?.className).toMatch(/extra/)
    })
  })

  describe('SheetFooter', () => {
    it('renders children', () => {
      const { container } = render(
        <SheetFooter>
          <button>Save</button>
        </SheetFooter>
      )
      const footer = container.querySelector('[data-slot="sheet-footer"]')
      expect(footer).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
    })

    it('merges a custom className', () => {
      const { container } = render(<SheetFooter className="footer-extra">x</SheetFooter>)
      expect(container.querySelector('[data-slot="sheet-footer"]')?.className).toMatch(/footer-extra/)
    })
  })

  describe('SheetTitle', () => {
    it('renders text content', () => {
      render(
        <Sheet open>
          <SheetContent>
            <SheetTitle>My Title</SheetTitle>
          </SheetContent>
        </Sheet>
      )
      expect(screen.getByText('My Title')).toBeInTheDocument()
    })

    it('applies font-semibold class', () => {
      render(
        <Sheet open>
          <SheetContent>
            <SheetTitle className="extra-class">Title</SheetTitle>
          </SheetContent>
        </Sheet>
      )
      const el = document.querySelector('[data-slot="sheet-title"]')
      expect(el?.className).toMatch(/font-semibold/)
      expect(el?.className).toMatch(/extra-class/)
    })
  })

  describe('SheetDescription', () => {
    it('renders text content', () => {
      render(
        <Sheet open>
          <SheetContent>
            <SheetTitle>Title</SheetTitle>
            <SheetDescription>My description</SheetDescription>
          </SheetContent>
        </Sheet>
      )
      expect(screen.getByText('My description')).toBeInTheDocument()
    })

    it('applies muted text class', () => {
      render(
        <Sheet open>
          <SheetContent>
            <SheetTitle>T</SheetTitle>
            <SheetDescription className="custom-desc">Desc</SheetDescription>
          </SheetContent>
        </Sheet>
      )
      const el = document.querySelector('[data-slot="sheet-description"]')
      expect(el?.className).toMatch(/text-muted-foreground/)
      expect(el?.className).toMatch(/custom-desc/)
    })
  })
})
