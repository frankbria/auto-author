import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  // ponytail: max-md:min-h-11/min-w-11 gives every button a 44px WCAG touch target on
  // mobile (<768px) without touching call sites; desktop keeps the compact h-9 sizes below.
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive max-md:min-h-11 max-md:min-w-11",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive-surface text-white hover:bg-destructive-surface/90 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40",
        outline:
          "border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost:
          "hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-10 rounded-md px-6 has-[>svg]:px-4",
        icon: "size-9",
        "icon-sm": "size-8",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

/**
 * The busy state, kept apart from the disabled state (#642).
 *
 * `disabled:opacity-50` in the base string is right for a button that is simply
 * unavailable — WCAG 1.4.3 exempts inactive components, and the greyed look is
 * the affordance. It is wrong for a button that disables itself *while working*
 * and renders its own status text ("Saving...", "Generating..."): CSS `opacity`
 * groups the element, so the fill and the label are each blended 50% with the
 * page behind the button rather than composited against each other. The default
 * variant's label falls from 6.29:1 to **2.29:1** in light — the hardest text on
 * screen to read, at the moment the user most needs to read it.
 *
 * `busy` restores full opacity and marks the state for assistive technology,
 * while keeping the button unclickable. It does not change how an unavailable
 * button looks anywhere.
 */
const BUSY_CLASSES = "disabled:opacity-100 disabled:pointer-events-none cursor-progress"

/**
 * The same intent for `asChild`, where the child may be an anchor and cannot
 * take `disabled` at all. Every class above is `disabled:`-prefixed, so without
 * that attribute none of them applies and the "busy" link stays fully clickable
 * — which the pre-PR reviewer caught, and which is the opposite of the contract.
 * These are unprefixed, and `aria-disabled` carries the state to assistive
 * technology in place of the attribute the element cannot have.
 */
const BUSY_CLASSES_AS_CHILD = "opacity-100 pointer-events-none cursor-progress"

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  busy = false,
  disabled,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
    /**
     * The action is running. Implies `disabled` unless one is passed
     * explicitly, sets `aria-busy`, and keeps the label legible.
     */
    busy?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      data-busy={busy ? "true" : undefined}
      aria-busy={busy || undefined}
      // `asChild` renders someone else's element, which may not accept
      // `disabled` at all — an anchor, say. Only the real button gets it.
      disabled={asChild ? undefined : (disabled ?? busy)}
      aria-disabled={asChild && busy && disabled !== false ? true : undefined}
      className={cn(
        buttonVariants({ variant, size, className }),
        busy && (asChild ? BUSY_CLASSES_AS_CHILD : BUSY_CLASSES)
      )}
      {...props}
    />
  )
}

export { Button, buttonVariants, BUSY_CLASSES, BUSY_CLASSES_AS_CHILD }
