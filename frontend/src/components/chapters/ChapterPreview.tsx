'use client';

import { ChapterTabMetadata } from '@/types/chapter-tabs';

interface ChapterPreviewProps {
  chapter: ChapterTabMetadata;
  content?: string;
}

export function ChapterPreview({ chapter, content }: ChapterPreviewProps) {
  return (
    <div className="h-full p-4">
      <div className="max-w-4xl mx-auto">
        <header className="mb-6">
          <h1 className="text-3xl font-bold mb-2">{chapter.title}</h1>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{chapter.word_count} words</span>
            <span>{chapter.estimated_reading_time} min read</span>
            <span className="capitalize">{chapter.status}</span>
          </div>
        </header>
        
        <div className="prose prose-lg max-w-none">
          {content ? (
            <div className="whitespace-pre-wrap">{content}</div>
          ) : (
            <div className="text-muted-foreground italic">
              No content available for preview
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
