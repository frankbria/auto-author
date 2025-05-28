'use client';

import { use, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ChapterEditor } from '@/components/chapters/ChapterEditor';
import { Button } from '@/components/ui/button';
import { ArrowLeft, LayoutGrid, ExternalLink } from 'lucide-react';

interface ChapterContentPageProps {
  params: Promise<{ bookId: string; chapterId: string }>;
}

export default function ChapterContentPage({ params }: ChapterContentPageProps) {
  const { bookId, chapterId } = use(params);
  const router = useRouter();

  // Auto-redirect to tabbed interface after a short delay
  useEffect(() => {
    const timer = setTimeout(() => {
      // Set the active chapter in localStorage so tabs open with the right chapter
      localStorage.setItem(`chapter-tabs-${bookId}`, JSON.stringify({
        active_chapter_id: chapterId,
        timestamp: Date.now()
      }));
      
      // Redirect to book page with tabs
      router.replace(`/dashboard/books/${bookId}?chapter=${chapterId}`);
    }, 2000); // 2 second delay to show the redirect message

    return () => clearTimeout(timer);
  }, [bookId, chapterId, router]);

  return (
    <div className="container mx-auto h-[calc(100vh-4rem)] flex flex-col">
      <div className="mb-4 px-4 py-2 border-b">          <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <ExternalLink className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <div className="flex-1">
                <h3 className="font-medium text-blue-900 dark:text-blue-100">Redirecting to Tabbed Interface</h3>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                  You&apos;re being redirected to the improved tabbed chapter interface for a better writing experience.
                </p>
              </div>
            <Button 
              onClick={() => {
                localStorage.setItem(`chapter-tabs-${bookId}`, JSON.stringify({
                  active_chapter_id: chapterId,
                  timestamp: Date.now()
                }));
                router.replace(`/dashboard/books/${bookId}?chapter=${chapterId}`);
              }}
              size="sm"
              className="bg-blue-600 hover:bg-blue-700"
            >
              Go Now
            </Button>
          </div>
        </div>
      </div>
      
      <div className="mb-4 px-4 py-2 border-b flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Chapter Editor (Legacy)</h1>
          <p className="text-muted-foreground">
            Individual chapter editing is being phased out in favor of the tabbed interface
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href={`/dashboard/books/${bookId}?chapter=${chapterId}`}>
            <Button variant="outline" size="sm">
              <LayoutGrid className="w-4 h-4 mr-2" />
              Open in Tabs
            </Button>
          </Link>
          <Link href={`/dashboard/books/${bookId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Book
            </Button>
          </Link>
        </div>
      </div>
      
      <div className="flex-1 px-4">
        <ChapterEditor
          bookId={bookId}
          chapterId={chapterId}
          onSave={(content: string) => {
            console.log('Chapter saved from individual page:', content.length, 'characters');
          }}
          onContentChange={(content: string) => {
            console.log('Content changed:', content.length, 'characters');
          }}
        />
      </div>
    </div>
  );
}
