/**
 * Tests for src/components/ui/dropdown-menu.tsx
 * Exercises all 15 exported wrapper components.
 *
 * Note: Radix UI DropdownMenu renders Content via a Portal (appended to
 * document.body). RTL's screen.* queries search the full document, so
 * portal content is always queryable. We use open={true} on Root (and
 * open={true} on Sub) to force content into the DOM without pointer events.
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import {
  DropdownMenu,
  DropdownMenuPortal,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from '@/components/ui/dropdown-menu'

// DropdownMenuPortal uses @radix-ui/react-dropdown-menu's Portal which is
// NOT globally mocked (only @radix-ui/react-dialog is). It renders to
// document.body — perfectly accessible via screen queries.

describe('DropdownMenu — exported wrapper components', () => {
  describe('DropdownMenu (Root) + Trigger + Content open via prop', () => {
    it('renders trigger button and content when open=true', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open Menu</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Item One</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )

      expect(screen.getByText('Open Menu')).toBeInTheDocument()
      expect(screen.getByText('Item One')).toBeInTheDocument()
    })

    it('renders the trigger with data-slot attribute', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Trigger</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>X</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(document.querySelector('[data-slot="dropdown-menu-trigger"]')).toBeInTheDocument()
    })

    it('does not render content when closed (uncontrolled default)', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Toggle</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Hidden Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      // Content is not in DOM when closed
      expect(screen.queryByText('Hidden Item')).not.toBeInTheDocument()
      // But the trigger is always rendered
      expect(screen.getByText('Toggle')).toBeInTheDocument()
    })
  })

  describe('DropdownMenuContent', () => {
    it('renders with data-slot="dropdown-menu-content" when open', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Content child</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(document.querySelector('[data-slot="dropdown-menu-content"]')).toBeInTheDocument()
    })

    it('accepts a custom className', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent className="my-menu-class">
            <DropdownMenuItem>item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      const el = document.querySelector('[data-slot="dropdown-menu-content"]')
      expect(el?.className).toMatch(/my-menu-class/)
    })
  })

  describe('DropdownMenuGroup', () => {
    it('renders children with data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuGroup>
              <DropdownMenuItem>Grouped Item</DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(document.querySelector('[data-slot="dropdown-menu-group"]')).toBeInTheDocument()
      expect(screen.getByText('Grouped Item')).toBeInTheDocument()
    })
  })

  describe('DropdownMenuLabel', () => {
    it('renders label text with data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuLabel>My Label</DropdownMenuLabel>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(screen.getByText('My Label')).toBeInTheDocument()
      expect(document.querySelector('[data-slot="dropdown-menu-label"]')).toBeInTheDocument()
    })

    it('applies inset data attribute when inset=true', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuLabel inset>Inset Label</DropdownMenuLabel>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      const el = document.querySelector('[data-slot="dropdown-menu-label"]')
      expect(el?.getAttribute('data-inset')).toBe('true')
    })
  })

  describe('DropdownMenuItem', () => {
    it('renders with default variant', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Click me</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      const item = document.querySelector('[data-slot="dropdown-menu-item"]')
      expect(item).toBeInTheDocument()
      expect(item?.getAttribute('data-variant')).toBe('default')
    })

    it('renders with destructive variant', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem variant="destructive">Delete</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      const item = document.querySelector('[data-slot="dropdown-menu-item"]')
      expect(item?.getAttribute('data-variant')).toBe('destructive')
    })

    it('applies inset when inset=true', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem inset>Inset</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      const item = document.querySelector('[data-slot="dropdown-menu-item"]')
      expect(item?.getAttribute('data-inset')).toBe('true')
    })

    it('fires onClick when clicked', () => {
      const onClick = jest.fn()
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={onClick}>Clickable</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      fireEvent.click(screen.getByText('Clickable'))
      expect(onClick).toHaveBeenCalled()
    })
  })

  describe('DropdownMenuCheckboxItem', () => {
    it('renders with checked state', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuCheckboxItem checked>Checked Option</DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(screen.getByText('Checked Option')).toBeInTheDocument()
      const item = document.querySelector('[data-slot="dropdown-menu-checkbox-item"]')
      expect(item).toBeInTheDocument()
    })

    it('renders unchecked state', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuCheckboxItem checked={false}>Unchecked</DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(screen.getByText('Unchecked')).toBeInTheDocument()
    })
  })

  describe('DropdownMenuRadioGroup + DropdownMenuRadioItem', () => {
    it('renders radio options with a selected value', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup value="a">
              <DropdownMenuRadioItem value="a">Option A</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="b">Option B</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(screen.getByText('Option A')).toBeInTheDocument()
      expect(screen.getByText('Option B')).toBeInTheDocument()
      expect(document.querySelector('[data-slot="dropdown-menu-radio-group"]')).toBeInTheDocument()
      expect(document.querySelectorAll('[data-slot="dropdown-menu-radio-item"]').length).toBe(2)
    })

    it('calls onValueChange when a radio item is selected', () => {
      const onValueChange = jest.fn()
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup value="a" onValueChange={onValueChange}>
              <DropdownMenuRadioItem value="b">Option B</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      fireEvent.click(screen.getByText('Option B'))
      expect(onValueChange).toHaveBeenCalledWith('b')
    })
  })

  describe('DropdownMenuSeparator', () => {
    it('renders a separator element', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Above</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Below</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(document.querySelector('[data-slot="dropdown-menu-separator"]')).toBeInTheDocument()
    })

    it('accepts a custom className', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSeparator className="custom-sep" />
          </DropdownMenuContent>
        </DropdownMenu>
      )
      const sep = document.querySelector('[data-slot="dropdown-menu-separator"]')
      expect(sep?.className).toMatch(/custom-sep/)
    })
  })

  describe('DropdownMenuShortcut', () => {
    it('renders shortcut text as a span', () => {
      const { container } = render(<DropdownMenuShortcut>⌘K</DropdownMenuShortcut>)
      const span = container.querySelector('[data-slot="dropdown-menu-shortcut"]')
      expect(span).toBeInTheDocument()
      expect(span?.textContent).toBe('⌘K')
    })

    it('accepts a custom className', () => {
      const { container } = render(<DropdownMenuShortcut className="shortcut-extra">⇧S</DropdownMenuShortcut>)
      const span = container.querySelector('[data-slot="dropdown-menu-shortcut"]')
      expect(span?.className).toMatch(/shortcut-extra/)
    })

    it('renders inline within a DropdownMenuItem', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>
              Save
              <DropdownMenuShortcut>⌘S</DropdownMenuShortcut>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(screen.getByText('⌘S')).toBeInTheDocument()
    })
  })

  describe('DropdownMenuSub + SubTrigger + SubContent', () => {
    it('renders the sub-menu trigger and content when sub is open', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub open>
              <DropdownMenuSubTrigger>More Options</DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem>Sub Item</DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      expect(screen.getByText('More Options')).toBeInTheDocument()
      expect(document.querySelector('[data-slot="dropdown-menu-sub-trigger"]')).toBeInTheDocument()
      // SubContent is rendered when Sub is open
      expect(document.querySelector('[data-slot="dropdown-menu-sub-content"]')).toBeInTheDocument()
      expect(screen.getByText('Sub Item')).toBeInTheDocument()
    })

    it('renders SubTrigger with inset', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub open>
              <DropdownMenuSubTrigger inset>Inset Sub</DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem>x</DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      )
      const trigger = document.querySelector('[data-slot="dropdown-menu-sub-trigger"]')
      expect(trigger?.getAttribute('data-inset')).toBe('true')
    })
  })

  describe('DropdownMenuPortal', () => {
    it('renders children into the document when inside a DropdownMenu context', () => {
      // DropdownMenuPortal wraps @radix-ui/react-menu MenuPortal which requires
      // a Menu context — it must be rendered inside a DropdownMenu root.
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>T</DropdownMenuTrigger>
          <DropdownMenuPortal>
            <div data-testid="portal-child">Portal content</div>
          </DropdownMenuPortal>
        </DropdownMenu>
      )
      expect(screen.getByTestId('portal-child')).toBeInTheDocument()
    })
  })

  describe('comprehensive composition', () => {
    it('renders a full menu with every component type', () => {
      const onSelect = jest.fn()
      const onCheckedChange = jest.fn()
      const onValueChange = jest.fn()

      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuGroup>
              <DropdownMenuItem onClick={onSelect}>
                Edit
                <DropdownMenuShortcut>⌘E</DropdownMenuShortcut>
              </DropdownMenuItem>
              <DropdownMenuItem variant="destructive">Delete</DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuCheckboxItem checked onCheckedChange={onCheckedChange}>
              Show labels
            </DropdownMenuCheckboxItem>
            <DropdownMenuSeparator />
            <DropdownMenuRadioGroup value="sm" onValueChange={onValueChange}>
              <DropdownMenuRadioItem value="sm">Small</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="lg">Large</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
            <DropdownMenuSub open>
              <DropdownMenuSubTrigger>More</DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem>Sub action</DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      )

      expect(screen.getByText('Actions')).toBeInTheDocument()
      expect(screen.getByText('Edit')).toBeInTheDocument()
      expect(screen.getByText('Delete')).toBeInTheDocument()
      expect(screen.getByText('Show labels')).toBeInTheDocument()
      expect(screen.getByText('Small')).toBeInTheDocument()
      expect(screen.getByText('Large')).toBeInTheDocument()
      expect(screen.getByText('More')).toBeInTheDocument()
      expect(screen.getByText('Sub action')).toBeInTheDocument()
      expect(screen.getByText('⌘E')).toBeInTheDocument()
    })
  })
})
