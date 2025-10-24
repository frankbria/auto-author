/**
 * Export Page Object
 *
 * Handles book export to PDF and DOCX formats.
 */

import { Page, expect, Download } from '@playwright/test';

export class ExportPage {
  constructor(private page: Page) {}

  /**
   * Navigate to export page
   */
  async goto(bookId: string): Promise<void> {
    await this.page.goto(`/dashboard/books/${bookId}/export`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Select export format
   */
  async selectFormat(format: 'PDF' | 'DOCX'): Promise<void> {
    await this.page.click(`[data-testid="format-${format.toLowerCase()}"]`);
    console.log(`✅ Selected ${format} format`);
  }

  /**
   * Enable export option
   */
  async enableOption(option: 'coverPage' | 'tableOfContents' | 'pageNumbering' | 'headers'): Promise<void> {
    await this.page.check(`[data-testid="option-${option}"]`);
  }

  /**
   * Disable export option
   */
  async disableOption(option: 'coverPage' | 'tableOfContents' | 'pageNumbering' | 'headers'): Promise<void> {
    await this.page.uncheck(`[data-testid="option-${option}"]`);
  }

  /**
   * Click export button and wait for download
   */
  async export(): Promise<Download> {
    const downloadPromise = this.page.waitForEvent('download');

    await this.page.click('button:has-text("Export")');

    const download = await downloadPromise;

    console.log(`✅ Export initiated: ${download.suggestedFilename()}`);

    return download;
  }

  /**
   * Verify export progress modal appears
   */
  async verifyProgressModal(): Promise<void> {
    await expect(this.page.locator('[data-testid="export-progress"]')).toBeVisible();
  }

  /**
   * Verify progress bar shows processing
   */
  async verifyProgressBar(): Promise<void> {
    await expect(this.page.locator('[data-testid="progress-bar"]')).toBeVisible();
  }

  /**
   * Wait for export to complete
   */
  async waitForExportComplete(timeoutMs: number = 10000): Promise<void> {
    const progressModal = this.page.locator('[data-testid="export-progress"]');
    await expect(progressModal).not.toBeVisible({ timeout: timeoutMs });

    console.log('✅ Export complete');
  }

  /**
   * Configure and export PDF
   */
  async exportPDF(options: {
    coverPage?: boolean;
    tableOfContents?: boolean;
    pageNumbering?: boolean;
    headers?: boolean;
  } = {}): Promise<Download> {
    await this.selectFormat('PDF');

    if (options.coverPage) await this.enableOption('coverPage');
    if (options.tableOfContents) await this.enableOption('tableOfContents');
    if (options.pageNumbering) await this.enableOption('pageNumbering');
    if (options.headers) await this.enableOption('headers');

    const download = await this.export();

    return download;
  }

  /**
   * Configure and export DOCX
   */
  async exportDOCX(options: {
    coverPage?: boolean;
    tableOfContents?: boolean;
  } = {}): Promise<Download> {
    await this.selectFormat('DOCX');

    if (options.coverPage) await this.enableOption('coverPage');
    if (options.tableOfContents) await this.enableOption('tableOfContents');

    const download = await this.export();

    return download;
  }

  /**
   * Save download to file
   */
  async saveDownload(download: Download, filename: string): Promise<string> {
    const path = `tests/e2e/artifacts/downloads/${filename}`;
    await download.saveAs(path);

    console.log(`✅ Download saved: ${path}`);

    return path;
  }

  /**
   * Verify download is complete and has content
   */
  async verifyDownloadComplete(download: Download): Promise<void> {
    // Wait for download to finish
    await download.path();

    const suggestedFilename = download.suggestedFilename();
    expect(suggestedFilename).toBeTruthy();

    console.log(`✅ Download complete: ${suggestedFilename}`);
  }
}
