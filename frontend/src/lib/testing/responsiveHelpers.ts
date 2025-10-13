/**
 * Responsive Design Testing Utilities
 *
 * Provides helpers for testing responsive behavior and WCAG 2.1 compliance
 * in browser environments and testing frameworks.
 *
 * @module responsiveHelpers
 */

/**
 * Standard viewport presets for responsive testing
 */
export const VIEWPORTS = {
  /** iPhone SE - smallest common mobile viewport */
  mobile: { width: 375, height: 667, name: 'iPhone SE' },

  /** iPhone SE (smallest) - test minimum width support */
  mobileSmall: { width: 320, height: 568, name: 'iPhone SE (smallest)' },

  /** iPhone 12/13 - common modern mobile */
  mobileMedium: { width: 390, height: 844, name: 'iPhone 12/13' },

  /** iPhone Plus models - large mobile */
  mobileLarge: { width: 414, height: 896, name: 'iPhone Plus' },

  /** iPad Mini - small tablet */
  tablet: { width: 768, height: 1024, name: 'iPad Mini' },

  /** iPad Pro - large tablet */
  tabletLarge: { width: 1024, height: 1366, name: 'iPad Pro' },

  /** Standard laptop */
  desktop: { width: 1440, height: 900, name: 'Desktop' },

  /** Large desktop */
  desktopLarge: { width: 1920, height: 1080, name: 'Desktop Large' },
} as const;

/**
 * Tailwind breakpoint values (from tailwind.config.js)
 */
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1400,
} as const;

/**
 * WCAG 2.1 touch target requirements
 */
export const TOUCH_TARGET = {
  /** WCAG 2.1 Level AAA minimum (recommended) */
  MIN_SIZE_AAA: 44,

  /** WCAG 2.1 Level AA minimum */
  MIN_SIZE_AA: 24,

  /** Minimum spacing between adjacent touch targets */
  MIN_SPACING: 8,

  /** Recommended size for icon-only buttons */
  RECOMMENDED_ICON_SIZE: 48,
} as const;

/**
 * Touch target validation result
 */
export interface TouchTargetValidation {
  /** Whether the element meets WCAG 2.1 Level AAA requirements */
  isValid: boolean;

  /** Actual width in pixels */
  width: number;

  /** Actual height in pixels */
  height: number;

  /** WCAG compliance level: 'AAA', 'AA', or 'fail' */
  complianceLevel: 'AAA' | 'AA' | 'fail';

  /** Recommendation if not compliant */
  recommendation?: string;

  /** Gap from minimum size (negative if undersized) */
  gap: number;
}

/**
 * Validates touch target size against WCAG 2.1 requirements
 *
 * @param element - HTML element to validate
 * @param level - Target WCAG level ('AAA' recommended, 'AA' minimum)
 * @returns Validation result with compliance status and recommendations
 *
 * @example
 * ```typescript
 * const button = document.querySelector('button');
 * const result = validateTouchTarget(button);
 *
 * if (!result.isValid) {
 *   console.warn(`Touch target too small: ${result.recommendation}`);
 * }
 * ```
 */
export function validateTouchTarget(
  element: HTMLElement,
  level: 'AAA' | 'AA' = 'AAA'
): TouchTargetValidation {
  const rect = element.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;
  const minSize = level === 'AAA' ? TOUCH_TARGET.MIN_SIZE_AAA : TOUCH_TARGET.MIN_SIZE_AA;

  const isValidWidth = width >= minSize;
  const isValidHeight = height >= minSize;
  const isValid = isValidWidth && isValidHeight;

  // Determine compliance level
  let complianceLevel: 'AAA' | 'AA' | 'fail';
  if (width >= TOUCH_TARGET.MIN_SIZE_AAA && height >= TOUCH_TARGET.MIN_SIZE_AAA) {
    complianceLevel = 'AAA';
  } else if (width >= TOUCH_TARGET.MIN_SIZE_AA && height >= TOUCH_TARGET.MIN_SIZE_AA) {
    complianceLevel = 'AA';
  } else {
    complianceLevel = 'fail';
  }

  const gap = Math.min(width - minSize, height - minSize);

  let recommendation: string | undefined;
  if (!isValid) {
    const widthGap = minSize - width;
    const heightGap = minSize - height;

    if (widthGap > 0 && heightGap > 0) {
      recommendation = `Increase size by ${Math.max(widthGap, heightGap)}px to meet ${level} standards. Current: ${width}x${height}px, Required: ${minSize}x${minSize}px`;
    } else if (widthGap > 0) {
      recommendation = `Increase width by ${widthGap}px to meet ${level} standards. Current: ${width}px, Required: ${minSize}px`;
    } else {
      recommendation = `Increase height by ${heightGap}px to meet ${level} standards. Current: ${height}px, Required: ${minSize}px`;
    }
  }

  return {
    isValid,
    width,
    height,
    complianceLevel,
    recommendation,
    gap,
  };
}

/**
 * Checks if current viewport matches mobile breakpoint
 *
 * @returns True if viewport width is below tablet breakpoint (768px)
 */
export function isMobileViewport(): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth < BREAKPOINTS.md;
}

/**
 * Checks if current viewport matches tablet breakpoint
 *
 * @returns True if viewport width is between 768px and 1024px
 */
export function isTabletViewport(): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth >= BREAKPOINTS.md && window.innerWidth < BREAKPOINTS.lg;
}

/**
 * Checks if current viewport matches desktop breakpoint
 *
 * @returns True if viewport width is 1024px or larger
 */
export function isDesktopViewport(): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth >= BREAKPOINTS.lg;
}

/**
 * Gets current breakpoint name
 *
 * @returns Current Tailwind breakpoint name or 'xs' for smallest
 */
export function getCurrentBreakpoint(): 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' {
  if (typeof window === 'undefined') return 'md';

  const width = window.innerWidth;

  if (width >= BREAKPOINTS['2xl']) return '2xl';
  if (width >= BREAKPOINTS.xl) return 'xl';
  if (width >= BREAKPOINTS.lg) return 'lg';
  if (width >= BREAKPOINTS.md) return 'md';
  if (width >= BREAKPOINTS.sm) return 'sm';
  return 'xs';
}

/**
 * Detects if device is touch-capable
 *
 * @returns True if device has touch input capability
 */
export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false;

  return (
    'ontouchstart' in window ||
    navigator.maxTouchPoints > 0 ||
    // @ts-expect-error - msMaxTouchPoints is IE-specific
    navigator.msMaxTouchPoints > 0
  );
}

/**
 * Validates spacing between adjacent touch targets
 *
 * @param element1 - First interactive element
 * @param element2 - Second interactive element
 * @returns Distance in pixels between elements
 */
export function validateTouchTargetSpacing(
  element1: HTMLElement,
  element2: HTMLElement
): { distance: number; isValid: boolean; recommendation?: string } {
  const rect1 = element1.getBoundingClientRect();
  const rect2 = element2.getBoundingClientRect();

  // Calculate closest distance between elements
  let distance: number;

  // Check if elements overlap or are adjacent
  const horizontalDistance = Math.max(
    0,
    rect2.left - rect1.right,
    rect1.left - rect2.right
  );

  const verticalDistance = Math.max(0, rect2.top - rect1.bottom, rect1.top - rect2.bottom);

  // Elements are horizontally or vertically adjacent
  if (horizontalDistance > 0 && verticalDistance === 0) {
    distance = horizontalDistance;
  } else if (verticalDistance > 0 && horizontalDistance === 0) {
    distance = verticalDistance;
  } else {
    // Diagonal distance
    distance = Math.sqrt(horizontalDistance ** 2 + verticalDistance ** 2);
  }

  const isValid = distance >= TOUCH_TARGET.MIN_SPACING;

  const recommendation = isValid
    ? undefined
    : `Increase spacing by ${TOUCH_TARGET.MIN_SPACING - distance}px between elements`;

  return { distance, isValid, recommendation };
}

/**
 * Finds all interactive elements on page
 *
 * @returns Array of interactive HTML elements
 */
export function findInteractiveElements(): HTMLElement[] {
  if (typeof document === 'undefined') return [];

  const selectors = [
    'button',
    'a[href]',
    'input',
    'select',
    'textarea',
    '[role="button"]',
    '[role="link"]',
    '[tabindex]:not([tabindex="-1"])',
  ];

  const elements = Array.from(document.querySelectorAll(selectors.join(', ')));

  return elements.filter(
    (el) => el instanceof HTMLElement && isElementVisible(el)
  ) as HTMLElement[];
}

/**
 * Checks if element is visible in viewport
 *
 * @param element - Element to check
 * @returns True if element is visible
 */
export function isElementVisible(element: HTMLElement): boolean {
  if (typeof window === 'undefined') return false;

  const style = window.getComputedStyle(element);
  if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
    return false;
  }

  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

/**
 * Audits all interactive elements for touch target compliance
 *
 * @param level - Target WCAG level ('AAA' or 'AA')
 * @returns Array of violations with element details
 *
 * @example
 * ```typescript
 * const violations = auditTouchTargets('AAA');
 * console.log(`Found ${violations.length} touch target violations`);
 *
 * violations.forEach(v => {
 *   console.warn(v.element.tagName, v.validation.recommendation);
 * });
 * ```
 */
export function auditTouchTargets(level: 'AAA' | 'AA' = 'AAA'): Array<{
  element: HTMLElement;
  validation: TouchTargetValidation;
  selector: string;
}> {
  const interactiveElements = findInteractiveElements();
  const violations: Array<{
    element: HTMLElement;
    validation: TouchTargetValidation;
    selector: string;
  }> = [];

  interactiveElements.forEach((element) => {
    const validation = validateTouchTarget(element, level);

    if (!validation.isValid) {
      // Generate CSS selector for element
      const selector = getElementSelector(element);

      violations.push({
        element,
        validation,
        selector,
      });
    }
  });

  return violations;
}

/**
 * Generates CSS selector for element
 *
 * @param element - Element to generate selector for
 * @returns CSS selector string
 */
function getElementSelector(element: HTMLElement): string {
  if (element.id) {
    return `#${element.id}`;
  }

  if (element.className) {
    const classes = element.className.split(' ').filter(Boolean);
    if (classes.length > 0) {
      return `${element.tagName.toLowerCase()}.${classes.join('.')}`;
    }
  }

  return element.tagName.toLowerCase();
}

/**
 * Generates responsive design report
 *
 * @returns Object with compliance metrics and violations
 */
export function generateResponsiveReport(): {
  viewport: { width: number; height: number; breakpoint: string };
  touchTargets: {
    total: number;
    compliant: number;
    violations: number;
    complianceRate: number;
  };
  violations: ReturnType<typeof auditTouchTargets>;
} {
  const violations = auditTouchTargets('AAA');
  const total = findInteractiveElements().length;
  const violationCount = violations.length;
  const compliant = total - violationCount;
  const complianceRate = total > 0 ? (compliant / total) * 100 : 100;

  return {
    viewport: {
      width: typeof window !== 'undefined' ? window.innerWidth : 0,
      height: typeof window !== 'undefined' ? window.innerHeight : 0,
      breakpoint: getCurrentBreakpoint(),
    },
    touchTargets: {
      total,
      compliant,
      violations: violationCount,
      complianceRate: Math.round(complianceRate * 100) / 100,
    },
    violations,
  };
}

/**
 * React hook for responsive viewport detection
 *
 * @returns Current viewport state
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const viewport = useResponsiveViewport();
 *
 *   return (
 *     <div>
 *       {viewport.isMobile && <MobileNav />}
 *       {viewport.isDesktop && <DesktopNav />}
 *     </div>
 *   );
 * }
 * ```
 */
export function useResponsiveViewport() {
  if (typeof window === 'undefined') {
    return {
      isMobile: false,
      isTablet: false,
      isDesktop: true,
      breakpoint: 'md' as const,
      width: 1024,
      height: 768,
    };
  }

  const [viewport, setViewport] = useState({
    isMobile: isMobileViewport(),
    isTablet: isTabletViewport(),
    isDesktop: isDesktopViewport(),
    breakpoint: getCurrentBreakpoint(),
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    function handleResize() {
      setViewport({
        isMobile: isMobileViewport(),
        isTablet: isTabletViewport(),
        isDesktop: isDesktopViewport(),
        breakpoint: getCurrentBreakpoint(),
        width: window.innerWidth,
        height: window.innerHeight,
      });
    }

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return viewport;
}

// Export for testing and debugging
import { useState, useEffect } from 'react';

/**
 * Log responsive audit to console (dev mode only)
 */
export function logResponsiveAudit(): void {
  if (process.env.NODE_ENV !== 'development') return;

  const report = generateResponsiveReport();

  console.group('📱 Responsive Design Audit');
  console.log(`Viewport: ${report.viewport.width}x${report.viewport.height} (${report.viewport.breakpoint})`);
  console.log(
    `Touch Targets: ${report.touchTargets.compliant}/${report.touchTargets.total} compliant (${report.touchTargets.complianceRate}%)`
  );

  if (report.violations.length > 0) {
    console.group(`⚠️ ${report.violations.length} violations found:`);
    report.violations.forEach((v) => {
      console.warn(
        `${v.selector}: ${v.validation.width}x${v.validation.height}px (${v.validation.complianceLevel}) - ${v.validation.recommendation}`
      );
    });
    console.groupEnd();
  } else {
    console.log('✅ No violations found');
  }

  console.groupEnd();
}
