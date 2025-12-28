'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { HugeiconsIcon } from '@hugeicons/react';
import { AlertCircleIcon, BookOpen01Icon, PenTool01Icon } from '@hugeicons/core-free-icons';
import QuestionContainer from './QuestionContainer';
import { bookClient } from '@/lib/api/bookClient';
import { QuestionProgressResponse } from '@/types/chapter-questions';
import { Button } from '@/components/ui/button';

interface ChapterQuestionsProps {
  bookId: string;
  chapterId: string;
  chapterTitle: string;
  onSwitchToEditor?: () => void;
  onDraftGenerated?: (draft: string) => void;
}

const TAB_VALUES = {
  QUESTIONS: 'questions',
  EDITOR: 'editor'
} as const;

type TabValue = typeof TAB_VALUES[keyof typeof TAB_VALUES];

/**
 * ChapterQuestions component serves as the main entry point for the interview-style
 * questions feature in the chapter tabs interface. It displays the QuestionContainer
 * component and provides a tab interface to switch between questions and the chapter editor.
 */
export default function ChapterQuestions({
  bookId,
  chapterId,
  chapterTitle,
  onSwitchToEditor,
  onDraftGenerated
}: ChapterQuestionsProps) {
  const [progress, setProgress] = useState<QuestionProgressResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Session storage key for tab state persistence
  const storageKey = `chapterQuestionsTab_${bookId}_${chapterId}`;

  // Initialize active tab from session storage or default to 'questions'
  const [activeTab, setActiveTab] = useState<TabValue>(() => {
    if (typeof window !== 'undefined') {
      const saved = sessionStorage.getItem(storageKey);
      if (saved === TAB_VALUES.QUESTIONS || saved === TAB_VALUES.EDITOR) {
        return saved;
      }
    }
    return TAB_VALUES.QUESTIONS;
  });

  // Handle tab change with session storage persistence
  const handleTabChange = useCallback((value: string) => {
    const tabValue = value as TabValue;
    setActiveTab(tabValue);

    if (typeof window !== 'undefined') {
      sessionStorage.setItem(storageKey, tabValue);
    }

    // Call onSwitchToEditor when switching to editor tab
    if (tabValue === TAB_VALUES.EDITOR && onSwitchToEditor) {
      onSwitchToEditor();
    }
  }, [storageKey, onSwitchToEditor]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Check for Ctrl key
      if (!event.ctrlKey) return;

      // Ctrl+1: Switch to questions tab
      if (event.key === '1') {
        event.preventDefault();
        handleTabChange(TAB_VALUES.QUESTIONS);
        return;
      }

      // Ctrl+2: Switch to editor tab (if available)
      if (event.key === '2' && onSwitchToEditor) {
        event.preventDefault();
        handleTabChange(TAB_VALUES.EDITOR);
        return;
      }

      // Ctrl+Tab: Next tab, Ctrl+Shift+Tab: Previous tab
      if (event.key === 'Tab') {
        event.preventDefault();
        const tabs = onSwitchToEditor
          ? [TAB_VALUES.QUESTIONS, TAB_VALUES.EDITOR]
          : [TAB_VALUES.QUESTIONS];

        if (tabs.length < 2) return;

        const currentIndex = tabs.indexOf(activeTab);
        let nextIndex: number;

        if (event.shiftKey) {
          // Previous tab
          nextIndex = currentIndex <= 0 ? tabs.length - 1 : currentIndex - 1;
        } else {
          // Next tab
          nextIndex = currentIndex >= tabs.length - 1 ? 0 : currentIndex + 1;
        }

        handleTabChange(tabs[nextIndex]);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, handleTabChange, onSwitchToEditor]);

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
      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="w-full"
        data-testid="chapter-questions-tabs"
      >
        <TabsList className="w-full border-b mb-4">
          <TabsTrigger value="questions" className="flex items-center">
            <HugeiconsIcon icon={BookOpen01Icon} size={16} className="mr-2" />
            Interview Questions
          </TabsTrigger>
          {onSwitchToEditor && (
            <TabsTrigger value="editor" className="flex items-center">
              <HugeiconsIcon icon={PenTool01Icon} size={16} className="mr-2" />
              Chapter Editor
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="questions" className="p-0">
          {error ? (
            <Card className="p-6">
              <div className="flex items-center text-destructive">
                <HugeiconsIcon icon={AlertCircleIcon} size={20} className="mr-2" />
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
              onDraftGenerated={onDraftGenerated}
              onSwitchToEditor={onSwitchToEditor}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
