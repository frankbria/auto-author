'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';

// Stub components for UI elements that will be properly implemented later
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const Tabs = ({ className, children, defaultValue }: { className?: string, children: React.ReactNode, defaultValue?: string }) => (
  <div className={className}>{children}</div>
);

const TabsList = ({ className, children }: { className?: string, children: React.ReactNode }) => (
  <div className={`flex space-x-2 mb-4 ${className}`}>{children}</div>
);

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const TabsTrigger = ({ children, value, className, onClick }: { children: React.ReactNode, value?: string, className?: string, onClick?: () => void }) => (
  <div className={`px-4 py-2 border rounded cursor-pointer hover:bg-gray-100 ${className}`} onClick={onClick}>{children}</div>
);

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const TabsContent = ({ className, children, value }: { className?: string, children: React.ReactNode, value?: string }) => (
  <div className={className}>{children}</div>
);
import { AlertCircle, BookOpen, PenTool } from 'lucide-react';
import QuestionContainer from './QuestionContainer';
import { bookClient } from '@/lib/api/bookClient';
import { QuestionProgressResponse } from '@/types/chapter-questions';
import { Button } from '@/components/ui/button';

interface ChapterQuestionsProps {
  bookId: string;
  chapterId: string;
  chapterTitle: string;
  onSwitchToEditor?: () => void;
}

/**
 * ChapterQuestions component serves as the main entry point for the interview-style 
 * questions feature in the chapter tabs interface. It displays the QuestionContainer
 * component and provides a tab interface to switch between questions and the chapter editor.
 */
export default function ChapterQuestions({
  bookId,
  chapterId,
  chapterTitle,
  onSwitchToEditor
}: ChapterQuestionsProps) {
  const [progress, setProgress] = useState<QuestionProgressResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch question progress on mount
  useEffect(() => {
    const fetchProgress = async () => {
      try {
        setLoading(true);
        const progressData = await bookClient.getChapterQuestionProgress(bookId, chapterId);
        setProgress(progressData);
      } catch (err) {
        console.error('Error fetching question progress:', err);
        setError('Failed to load question progress');
      } finally {
        setLoading(false);
      }
    };

    fetchProgress();
  }, [bookId, chapterId]);

  // Handle progress update when a response is saved
  const handleResponseSaved = async () => {
    try {
      const progressData = await bookClient.getChapterQuestionProgress(bookId, chapterId);
      setProgress(progressData);
    } catch (err) {
      console.error('Error updating question progress:', err);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">{chapterTitle}</h2>
        
        {/* Progress summary */}
        {!loading && progress && (
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <span>
              {progress.completed} of {progress.total} questions answered
              {progress.completed > 0 && progress.total > 0 && (
                <span> ({Math.round((progress.completed / progress.total) * 100)}%)</span>
              )}
            </span>
            
            {progress.status === 'completed' && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Complete
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tab interface for questions and editor */}
      <Tabs defaultValue="questions" className="w-full">
        <TabsList className="w-full border-b mb-4">
          <TabsTrigger value="questions" className="flex items-center">
            <BookOpen className="w-4 h-4 mr-2" />
            Interview Questions
          </TabsTrigger>
          {onSwitchToEditor && (
            <TabsTrigger value="editor" className="flex items-center" onClick={onSwitchToEditor}>
              <PenTool className="w-4 h-4 mr-2" />
              Chapter Editor
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="questions" className="p-0">
          {error ? (
            <Card className="p-6">
              <div className="flex items-center text-destructive">
                <AlertCircle className="h-5 w-5 mr-2" />
                <p>{error}</p>
              </div>
              <Button 
                className="mt-4" 
                variant="outline" 
                onClick={() => window.location.reload()}
              >
                Retry
              </Button>
            </Card>
          ) : (
            <QuestionContainer 
              bookId={bookId}
              chapterId={chapterId}
              chapterTitle={chapterTitle}
              onResponseSaved={handleResponseSaved}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
