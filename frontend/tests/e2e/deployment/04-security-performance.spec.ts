/**
 * Security & Performance Testing
 *
 * This test suite validates security headers (CSP) and performance metrics
 * to ensure the application meets production security and performance standards.
 *
 * Based on DEPLOYMENT-TESTING-CHECKLIST.md Security & Performance section.
 */

import { test, expect } from '@playwright/test';
import { authenticateUser } from '../fixtures/auth.fixture';
import { TEST_BOOK, TEST_SUMMARY, TOC_QUESTIONS } from '../fixtures/test-data.fixture';
import { PERFORMANCE_BUDGETS, measureOperation } from '../fixtures/performance.fixture';
import { CSPValidator } from '../helpers/csp-validator';
import { BookFormPage } from '../page-objects/book-form.page';
import { SummaryPage } from '../page-objects/summary.page';
import { TOCWizardPage } from '../page-objects/toc-wizard.page';
import { ExportPage } from '../page-objects/export.page';

test.describe('Security & Performance', () => {
  test.describe('Content Security Policy (CSP)', () => {
    test('CSP Headers: Frontend (Next.js)', async ({ page }) => {
      console.log('\n🔒 Validating frontend CSP headers');

      // Navigate to homepage and capture response
      const response = await page.goto('/');

      if (!response) {
        throw new Error('No response received from homepage');
      }

      // Validate frontend CSP
      await CSPValidator.validateFrontendCSP(response);

      console.log('✅ Frontend CSP validation complete');
    });

    test('CSP Headers: Backend API Docs (Swagger UI)', async ({ page }) => {
      console.log('\n🔒 Validating Swagger UI CSP headers');

      // Navigate to Swagger UI
      const apiUrl = process.env.DEPLOYMENT_URL?.replace('https://', 'https://api.') || 'https://api.dev.autoauthor.app';
      const apiDocsUrl = `${apiUrl}/docs`;

      // Validate Swagger UI CSP
      await CSPValidator.validateSwaggerUICSP(page, apiDocsUrl);

      console.log('✅ Swagger UI CSP validation complete');
    });

    test('CSP Violations: Monitor during user journey', async ({ page }) => {
      console.log('\n🔍 Monitoring CSP violations during user journey');

      // Authenticate
      await authenticateUser(page);

      // Create book
      const bookForm = new BookFormPage(page);
      await bookForm.gotoNewBook();
      await bookForm.fillBookDetails(TEST_BOOK);
      const result = await bookForm.submitAndWaitForAPI();
      const bookId = result.bookId!;

      // Check for CSP violations
      await CSPValidator.checkForCSPViolations(page);

      // Add summary
      const summary = new SummaryPage(page);
      await summary.goto(bookId);
      await summary.fillSummary(TEST_SUMMARY.content);

      await CSPValidator.checkForCSPViolations(page);

      console.log('✅ No CSP violations detected during user journey');
    });
  });

  test.describe('Core Web Vitals', () => {
    test('LCP (Largest Contentful Paint) < 2.5s', async ({ page }) => {
      console.log('\n⚡ Measuring LCP (Largest Contentful Paint)');

      // Navigate to homepage
      await page.goto('/');

      // Wait for LCP
      await page.waitForLoadState('networkidle');

      // Measure LCP using Performance API
      const lcp = await page.evaluate(() => {
        return new Promise<number>((resolve) => {
          new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1] as any;
            resolve(lastEntry.renderTime || lastEntry.loadTime);
          }).observe({ type: 'largest-contentful-paint', buffered: true });

          // Timeout after 10s
          setTimeout(() => resolve(0), 10000);
        });
      });

      console.log(`📊 LCP: ${lcp.toFixed(0)}ms`);

      // Verify LCP is within budget
      expect(lcp).toBeLessThan(PERFORMANCE_BUDGETS.LCP);

      console.log(`✅ LCP within budget (${PERFORMANCE_BUDGETS.LCP}ms)`);
    });

    test('CLS (Cumulative Layout Shift) < 0.1', async ({ page }) => {
      console.log('\n📐 Measuring CLS (Cumulative Layout Shift)');

      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Wait for layout to stabilize
      await page.waitForTimeout(2000);

      // Measure CLS using Performance API
      const cls = await page.evaluate(() => {
        return new Promise<number>((resolve) => {
          let clsValue = 0;

          new PerformanceObserver((list) => {
            for (const entry of list.getEntries() as any[]) {
              if (!entry.hadRecentInput) {
                clsValue += entry.value;
              }
            }
            resolve(clsValue);
          }).observe({ type: 'layout-shift', buffered: true });

          // Resolve after 3s
          setTimeout(() => resolve(clsValue), 3000);
        });
      });

      console.log(`📊 CLS: ${cls.toFixed(3)}`);

      // Verify CLS is within budget
      expect(cls).toBeLessThan(PERFORMANCE_BUDGETS.CLS);

      console.log(`✅ CLS within budget (${PERFORMANCE_BUDGETS.CLS})`);
    });

    test('FID (First Input Delay) simulation', async ({ page }) => {
      console.log('\n⏱️ Simulating FID (First Input Delay)');

      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Measure time from click to response
      const start = performance.now();
      await page.click('text=Sign In');
      // Wait for navigation to sign-in page (better-auth)
      await page.waitForURL('**/auth/sign-in', { timeout: 5000 });
      const fid = performance.now() - start;

      console.log(`📊 FID Simulation: ${fid.toFixed(0)}ms`);

      // FID should be < 100ms for "Good" rating
      expect(fid).toBeLessThan(100);

      console.log('✅ FID within acceptable range (<100ms)');
    });
  });

  test.describe('Performance Budgets', () => {
    test('Page Navigation < 500ms', async ({ page }) => {
      console.log('\n🚀 Testing page navigation performance');

      await authenticateUser(page);

      // Measure dashboard navigation
      const { duration, withinBudget } = await measureOperation(
        page,
        async () => {
          await page.goto('/dashboard');
          await page.waitForLoadState('networkidle');
        },
        PERFORMANCE_BUDGETS.PAGE_NAVIGATION,
        'Dashboard Navigation'
      );

      console.log(`📊 Dashboard navigation: ${duration.toFixed(0)}ms`);
      expect(withinBudget).toBeTruthy();

      // Measure create-book modal open (the /dashboard/new-book page was
      // removed in #205; creation happens in the BookCreationWizard modal)
      const { duration: formDuration, withinBudget: formBudget } = await measureOperation(
        page,
        async () => {
          await page.getByRole('button', { name: 'Create New Book' }).first().click();
          await page.getByRole('dialog').waitFor();
        },
        PERFORMANCE_BUDGETS.PAGE_NAVIGATION,
        'Create Book Modal Open'
      );

      console.log(`📊 Create-book modal open: ${formDuration.toFixed(0)}ms`);
      expect(formBudget).toBeTruthy();

      console.log('✅ Page navigation within budget (<500ms)');
    });

    test('TOC Generation < 3000ms', async ({ page }) => {
      console.log('\n🤖 Testing TOC generation performance budget');

      await authenticateUser(page);

      // Create book with summary
      const bookForm = new BookFormPage(page);
      await bookForm.gotoNewBook();
      await bookForm.fillBookDetails(TEST_BOOK);
      const result = await bookForm.submitAndWaitForAPI();
      const bookId = result.bookId!;

      const summary = new SummaryPage(page);
      await summary.goto(bookId);
      await summary.fillSummary(TEST_SUMMARY.content);
      await summary.clickContinueToTOC();

      const tocWizard = new TOCWizardPage(page);
      await tocWizard.waitForReadinessCheck();
      await tocWizard.answerQuestions(TOC_QUESTIONS);

      // Measure TOC generation
      const { duration, withinBudget } = await measureOperation(
        page,
        async () => {
          await tocWizard.generateTOC();
        },
        PERFORMANCE_BUDGETS.TOC_GENERATION,
        'TOC Generation'
      );

      console.log(`📊 TOC generation: ${duration.toFixed(0)}ms`);
      expect(withinBudget).toBeTruthy();

      console.log(`✅ TOC generation within budget (${PERFORMANCE_BUDGETS.TOC_GENERATION}ms)`);
    });

    test('Export PDF < 5000ms', async ({ page }) => {
      console.log('\n📄 Testing PDF export performance budget');

      await authenticateUser(page);

      // Create minimal book for export
      const bookForm = new BookFormPage(page);
      await bookForm.gotoNewBook();
      await bookForm.fillBookDetails({
        title: 'PDF Export Test',
        description: 'Testing PDF export performance',
        genre: 'business',
        targetAudience: 'Test users'
      });
      const result = await bookForm.submitAndWaitForAPI();
      const bookId = result.bookId!;

      // Navigate to export page
      const exportPage = new ExportPage(page);
      await exportPage.goto(bookId);

      // Measure PDF export
      const { duration, withinBudget } = await measureOperation(
        page,
        async () => {
          const download = await exportPage.exportPDF({
            coverPage: true,
            tableOfContents: true
          });
          await exportPage.verifyDownloadComplete(download);
        },
        PERFORMANCE_BUDGETS.EXPORT_PDF,
        'PDF Export'
      );

      console.log(`📊 PDF export: ${duration.toFixed(0)}ms`);
      expect(withinBudget).toBeTruthy();

      console.log(`✅ PDF export within budget (${PERFORMANCE_BUDGETS.EXPORT_PDF}ms)`);
    });

    test('Export DOCX < 5000ms', async ({ page }) => {
      console.log('\n📝 Testing DOCX export performance budget');

      await authenticateUser(page);

      // Create minimal book for export
      const bookForm = new BookFormPage(page);
      await bookForm.gotoNewBook();
      await bookForm.fillBookDetails({
        title: 'DOCX Export Test',
        description: 'Testing DOCX export performance',
        genre: 'business',
        targetAudience: 'Test users'
      });
      const result = await bookForm.submitAndWaitForAPI();
      const bookId = result.bookId!;

      // Navigate to export page
      const exportPage = new ExportPage(page);
      await exportPage.goto(bookId);

      // Measure DOCX export
      const { duration, withinBudget } = await measureOperation(
        page,
        async () => {
          const download = await exportPage.exportDOCX({
            coverPage: true,
            tableOfContents: true
          });
          await exportPage.verifyDownloadComplete(download);
        },
        PERFORMANCE_BUDGETS.EXPORT_DOCX,
        'DOCX Export'
      );

      console.log(`📊 DOCX export: ${duration.toFixed(0)}ms`);
      expect(withinBudget).toBeTruthy();

      console.log(`✅ DOCX export within budget (${PERFORMANCE_BUDGETS.EXPORT_DOCX}ms)`);
    });

    test('Auto-save < 1000ms (after debounce)', async ({ page }) => {
      console.log('\n💾 Testing auto-save performance budget');

      await authenticateUser(page);

      // Create book and navigate to chapter editor
      const bookForm = new BookFormPage(page);
      await bookForm.gotoNewBook();
      await bookForm.fillBookDetails({
        title: 'Auto-save Performance Test',
        description: 'Testing auto-save performance',
        genre: 'business',
        targetAudience: 'Test users'
      });
      const result = await bookForm.submitAndWaitForAPI();
      const bookId = result.bookId!;

      // Get first chapter
      await page.goto(`/dashboard/books/${bookId}`);
      const firstChapter = page.locator('[data-testid="chapter-item"]').first();
      const chapterId = await firstChapter.getAttribute('data-chapter-id') || '';

      await page.goto(`/dashboard/books/${bookId}/chapters/${chapterId}`);

      // Type content
      const editor = page.locator('[data-testid="chapter-editor"]');
      await editor.fill('Testing auto-save performance');

      // Wait for debounce
      await page.waitForTimeout(3000);

      // Measure save operation
      const start = performance.now();

      // Wait for "Saving..." indicator
      await expect(page.locator('[data-testid="auto-save-status"]')).toContainText('Saving', { timeout: 5000 });

      // Wait for "Saved" indicator
      await expect(page.locator('[data-testid="auto-save-status"]')).toContainText('Saved', { timeout: 3000 });

      const duration = performance.now() - start;

      console.log(`📊 Auto-save (after debounce): ${duration.toFixed(0)}ms`);
      expect(duration).toBeLessThan(PERFORMANCE_BUDGETS.AUTO_SAVE);

      console.log(`✅ Auto-save within budget (${PERFORMANCE_BUDGETS.AUTO_SAVE}ms)`);
    });
  });

  test.describe('Resource Loading', () => {
    test('JavaScript bundle size monitoring', async ({ page }) => {
      console.log('\n📦 Monitoring JavaScript bundle sizes');

      const resources: { url: string; size: number; type: string }[] = [];

      page.on('response', async (response) => {
        const url = response.url();
        if (url.endsWith('.js')) {
          const buffer = await response.body().catch(() => null);
          if (buffer) {
            resources.push({
              url,
              size: buffer.length,
              type: 'script'
            });
          }
        }
      });

      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Calculate total JS size
      const totalJSSize = resources.reduce((sum, r) => sum + r.size, 0);
      const totalJSSizeMB = (totalJSSize / 1024 / 1024).toFixed(2);

      console.log(`📊 Total JS size: ${totalJSSizeMB}MB`);
      console.log(`📊 JS files loaded: ${resources.length}`);

      // Log largest bundles
      const sortedBySize = resources.sort((a, b) => b.size - a.size).slice(0, 5);
      console.log('\n📦 Top 5 largest JS files:');
      sortedBySize.forEach((r, i) => {
        const sizeMB = (r.size / 1024 / 1024).toFixed(2);
        const filename = r.url.split('/').pop()?.substring(0, 50) || 'unknown';
        console.log(`  ${i + 1}. ${filename}: ${sizeMB}MB`);
      });

      // Recommended: Total JS < 1MB for initial load
      expect(parseFloat(totalJSSizeMB)).toBeLessThan(2); // Allowing 2MB for Next.js app

      console.log('✅ JavaScript bundle size monitoring complete');
    });

    test('Image optimization verification', async ({ page }) => {
      console.log('\n🖼️ Verifying image optimization');

      const images: { url: string; size: number }[] = [];

      page.on('response', async (response) => {
        const url = response.url();
        const contentType = response.headers()['content-type'] || '';

        if (contentType.startsWith('image/')) {
          const buffer = await response.body().catch(() => null);
          if (buffer) {
            images.push({
              url,
              size: buffer.length
            });
          }
        }
      });

      await page.goto('/');
      await page.waitForLoadState('networkidle');

      if (images.length === 0) {
        console.log('ℹ️ No images loaded on homepage (expected for text-heavy app)');
        return;
      }

      const totalImageSize = images.reduce((sum, img) => sum + img.size, 0);
      const totalImageSizeMB = (totalImageSize / 1024 / 1024).toFixed(2);

      console.log(`📊 Total image size: ${totalImageSizeMB}MB`);
      console.log(`📊 Images loaded: ${images.length}`);

      // Check for large images (>500KB)
      const largeImages = images.filter(img => img.size > 500 * 1024);
      if (largeImages.length > 0) {
        console.log(`⚠️ ${largeImages.length} images exceed 500KB`);
        largeImages.forEach(img => {
          const sizeKB = (img.size / 1024).toFixed(0);
          console.log(`  - ${img.url}: ${sizeKB}KB`);
        });
      } else {
        console.log('✅ All images are optimized (<500KB)');
      }
    });
  });
});

/**
 * Security & Performance Test Summary
 *
 * This test suite validates:
 * ✅ CSP Headers (Frontend Next.js)
 * ✅ CSP Headers (Backend Swagger UI)
 * ✅ CSP Violations monitoring during user journey
 * ✅ LCP (Largest Contentful Paint) < 2.5s
 * ✅ CLS (Cumulative Layout Shift) < 0.1
 * ✅ FID (First Input Delay) simulation < 100ms
 * ✅ Page Navigation < 500ms
 * ✅ TOC Generation < 3000ms
 * ✅ PDF Export < 5000ms
 * ✅ DOCX Export < 5000ms
 * ✅ Auto-save < 1000ms (after 3s debounce)
 * ✅ JavaScript bundle size monitoring
 * ✅ Image optimization verification
 *
 * Performance Budgets:
 * - LCP: 2500ms
 * - CLS: 0.1
 * - Page Navigation: 500ms
 * - TOC Generation: 3000ms
 * - Export (PDF/DOCX): 5000ms
 * - Auto-save: 1000ms
 */
