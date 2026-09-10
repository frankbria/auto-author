'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { HugeiconsIcon } from '@hugeicons/react';
import { Home01Icon, Book02Icon, File01Icon } from '@hugeicons/core-free-icons';

interface ChapterBreadcrumbProps {
  bookId?: string;
  bookTitle?: string;
  chapterId?: string;
  chapterTitle?: string;
  showChapterContext?: boolean;
}

export function ChapterBreadcrumb({
  bookId,
  bookTitle = 'Untitled Book',
  chapterId,
  chapterTitle,
  showChapterContext = false
}: ChapterBreadcrumbProps) {
  const pathname = usePathname();

  // Determine current page context
  const isBookPage = pathname.includes(`/books/${bookId}`) && !pathname.includes('/chapters/');
  const isChapterPage = pathname.includes(`/books/${bookId}/chapters/`);
  const isEditTocPage = pathname.includes('/edit-toc');
  const isSummaryPage = pathname.includes('/summary');
  const isGenerateTocPage = pathname.includes('/generate-toc');
  const isExportPage = pathname.includes('/export');

  return (
    <Breadcrumb className="mb-4">
      <BreadcrumbList>
        {/* Dashboard */}
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link href="/dashboard" className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
              <HugeiconsIcon icon={Home01Icon} size={16} />
              Dashboard
            </Link>
          </BreadcrumbLink>
        </BreadcrumbItem>

        <BreadcrumbSeparator />

        {/* Book */}
        {bookId && (
          <>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link
                  href={`/dashboard/books/${bookId}`}
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground"
                >
                  <HugeiconsIcon icon={Book02Icon} size={16} />
                  {bookTitle}
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>

            <BreadcrumbSeparator />
          </>
        )}

        {/* Current Page */}
        {isSummaryPage && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-foreground">Book Summary</BreadcrumbPage>
          </BreadcrumbItem>
        )}

        {isGenerateTocPage && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-foreground">Generate TOC</BreadcrumbPage>
          </BreadcrumbItem>
        )}

        {isEditTocPage && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-foreground">Edit TOC</BreadcrumbPage>
          </BreadcrumbItem>
        )}

        {isExportPage && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-foreground">Export Book</BreadcrumbPage>
          </BreadcrumbItem>
        )}

        {/* Chapter Context (for tabbed interface) */}
        {isBookPage && showChapterContext && chapterId && chapterTitle && (
          <>
            <BreadcrumbItem>
              <BreadcrumbPage className="text-foreground">Writing</BreadcrumbPage>
            </BreadcrumbItem>

            <BreadcrumbSeparator />

            <BreadcrumbItem>
              <BreadcrumbPage className="text-foreground flex items-center gap-1.5">
                <HugeiconsIcon icon={File01Icon} size={16} />
                {chapterTitle}
              </BreadcrumbPage>
            </BreadcrumbItem>
          </>
        )}

        {/* Individual Chapter Page (legacy) */}
        {isChapterPage && chapterTitle && (
          <>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link
                  href={`/dashboard/books/${bookId}?chapter=${chapterId}`}
                  className="text-muted-foreground hover:text-foreground"
                >
                  Writing (Tabbed)
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>

            <BreadcrumbSeparator />

            <BreadcrumbItem>
              <BreadcrumbPage className="text-foreground flex items-center gap-1.5">
                <HugeiconsIcon icon={File01Icon} size={16} />
                {chapterTitle} (Legacy)
              </BreadcrumbPage>
            </BreadcrumbItem>
          </>
        )}

        {/* Default book page when no specific context */}
        {isBookPage && !showChapterContext && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-foreground">Book Overview</BreadcrumbPage>
          </BreadcrumbItem>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
