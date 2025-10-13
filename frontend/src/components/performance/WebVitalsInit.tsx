/**
 * Web Vitals Initialization Component
 *
 * Client-side component that initializes Core Web Vitals tracking on mount.
 * Must be used in a Client Component context.
 *
 * @module components/performance/WebVitalsInit
 */

'use client';

import { useEffect } from 'react';
import { initializeWebVitals } from '@/lib/performance/metrics';

/**
 * Web Vitals initialization component
 *
 * Initializes Core Web Vitals tracking when the app loads.
 * Tracks: LCP, FID, INP, CLS, TTFB, FCP
 *
 * Usage:
 * ```tsx
 * // In app layout
 * export default function RootLayout({ children }) {
 *   return (
 *     <html>
 *       <body>
 *         <WebVitalsInit />
 *         {children}
 *       </body>
 *     </html>
 *   );
 * }
 * ```
 */
export function WebVitalsInit() {
  useEffect(() => {
    // Only initialize in browser (not during SSR)
    if (typeof window !== 'undefined') {
      initializeWebVitals();
    }
  }, []);

  // This component doesn't render anything
  return null;
}
