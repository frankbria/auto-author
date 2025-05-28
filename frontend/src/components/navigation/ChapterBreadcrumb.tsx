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
import { Home, Book, FileText } from 'lucide-react';

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
            <Link href="/dashboard" className="flex items-center gap-1.5 text-zinc-400 hover:text-zinc-200">
              <Home className="h-4 w-4" />
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
                  className="flex items-center gap-1.5 text-zinc-400 hover:text-zinc-200"
                >
                  <Book className="h-4 w-4" />
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
            <BreadcrumbPage className="text-zinc-100">Book Summary</BreadcrumbPage>
          </BreadcrumbItem>
        )}
        
        {isGenerateTocPage && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-zinc-100">Generate TOC</BreadcrumbPage>
          </BreadcrumbItem>
        )}
        
        {isEditTocPage && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-zinc-100">Edit TOC</BreadcrumbPage>
          </BreadcrumbItem>
        )}
        
        {isExportPage && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-zinc-100">Export Book</BreadcrumbPage>
          </BreadcrumbItem>
        )}

        {/* Chapter Context (for tabbed interface) */}
        {isBookPage && showChapterContext && chapterId && chapterTitle && (
          <>
            <BreadcrumbItem>
              <BreadcrumbPage className="text-zinc-100">Writing</BreadcrumbPage>
            </BreadcrumbItem>
            
            <BreadcrumbSeparator />
            
            <BreadcrumbItem>
              <BreadcrumbPage className="text-zinc-100 flex items-center gap-1.5">
                <FileText className="h-4 w-4" />
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
                  className="text-zinc-400 hover:text-zinc-200"
                >
                  Writing (Tabbed)
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            
            <BreadcrumbSeparator />
            
            <BreadcrumbItem>
              <BreadcrumbPage className="text-zinc-100 flex items-center gap-1.5">
                <FileText className="h-4 w-4" />
                {chapterTitle} (Legacy)
              </BreadcrumbPage>
            </BreadcrumbItem>
          </>
        )}
        
        {/* Default book page when no specific context */}
        {isBookPage && !showChapterContext && (
          <BreadcrumbItem>
            <BreadcrumbPage className="text-zinc-100">Book Overview</BreadcrumbPage>
          </BreadcrumbItem>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
