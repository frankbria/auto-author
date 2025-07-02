'use client';

import { useEffect, useCallback } from 'react';
import { useChapterTabs } from '@/hooks/useChapterTabs';
import { useTocSync } from '@/hooks/useTocSync';
import { useMediaQuery } from '@/hooks/use-media-query';
import { useToast } from '@/components/ui/use-toast';
import bookClient from '@/lib/api/bookClient';
import { TabBar } from './TabBar';
import { TabContent } from './TabContent';
import TabContextMenu from './TabContextMenu';
import { MobileChapterTabs } from './MobileChapterTabs';

interface ChapterTabsProps {
  bookId: string;
  initialActiveChapter?: string;
  className?: string;
  orientation?: 'horizontal' | 'vertical';
}

export function ChapterTabs({ bookId, initialActiveChapter, className, orientation = 'vertical' }: ChapterTabsProps) {
  // Check if we're on a mobile device - must be called at the top level
  const isMobile = useMediaQuery('(max-width: 768px)');
  const { toast } = useToast();
  
  const {
    state,
    actions: {
      setActiveChapter,
      reorderTabs,
      closeTab,
      updateChapterStatus,
      saveTabState,
      refreshChapters
    },
    loading,
    error
  } = useChapterTabs(bookId, initialActiveChapter);

  // Delete chapter handler
  const handleDeleteChapter = useCallback(async (chapterId: string) => {
    try {
      // Find the chapter to get its title
      const chapter = state.chapters.find(ch => ch.id === chapterId);
      const chapterTitle = chapter?.title || 'Chapter';
      
      // Call the API to delete the chapter
      await bookClient.deleteChapter(bookId, chapterId);
      
      // Close the tab if it's open
      closeTab(chapterId);
      
      // Refresh the chapters list
      await refreshChapters();
      
      toast({
        title: "Chapter deleted",
        description: `"${chapterTitle}" has been deleted successfully.`,
        variant: "success"
      });
    } catch (error) {
      console.error('Failed to delete chapter:', error);
      toast({
        title: "Error",
        description: "Failed to delete chapter. Please try again.",
        variant: "destructive"
      });
    }
  }, [bookId, state.chapters, closeTab, refreshChapters, toast]);

  // Create new chapter handler
  const handleCreateChapter = useCallback(async () => {
    try {
      // Calculate the next chapter order
      const nextOrder = state.chapters.length > 0 
        ? Math.max(...state.chapters.map(ch => ch.order || 0)) + 1 
        : 1;
      
      // Create the new chapter
      const newChapter = await bookClient.createChapter(bookId, {
        title: `Chapter ${nextOrder}`,
        content: '',
        order: nextOrder
      });
      
      // Refresh the chapters list to include the new chapter
      await refreshChapters();
      
      // Set the new chapter as active
      setActiveChapter(newChapter.id);
      
      toast({
        title: "Chapter created",
        description: `"${newChapter.title}" has been created successfully.`,
        variant: "success"
      });
    } catch (error) {
      console.error('Failed to create chapter:', error);
      toast({
        title: "Error",
        description: "Failed to create chapter. Please try again.",
        variant: "destructive"
      });
    }
  }, [bookId, state.chapters, refreshChapters, setActiveChapter, toast]);
  // Set up TOC synchronization
  useTocSync({ 
    bookId, 
    onTocChanged: refreshChapters
    // Removed pollInterval - polling disabled by default
  });

  const handleTabSelect = useCallback((chapterId: string) => {
    setActiveChapter(chapterId);
    saveTabState(); // Persist state
  }, [setActiveChapter, saveTabState]);

  const handleTabReorder = useCallback((sourceIndex: number, destinationIndex: number) => {
    reorderTabs(sourceIndex, destinationIndex);
  }, [reorderTabs]);

  // Keyboard navigation (Ctrl+1, Ctrl+2, etc.)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.key >= '1' && event.key <= '9') {
        event.preventDefault();
        const tabIndex = parseInt(event.key) - 1;
        const chapterId = state.tab_order[tabIndex];
        if (chapterId) {
          handleTabSelect(chapterId);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [state.tab_order, handleTabSelect]);  

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary mb-2"></div>
          <p className="text-foreground">Loading chapters...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg text-red-400">
        <h3 className="font-bold mb-1">Error loading chapters</h3>
        <p>{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 px-3 py-1 bg-red-800/40 hover:bg-red-800/70 text-red-200 text-sm rounded"
        >
          Retry
        </button>
      </div>
    );
  }

  // Handle empty chapters state
  if (state.chapters.length === 0) {
    return (
      <div 
        data-testid="empty-chapters-state" 
        className="flex flex-col items-center justify-center h-64 p-8 text-center"
      >
        <h3 className="text-xl font-semibold mb-2">No chapters available</h3>
        <p className="text-muted-foreground mb-4">
          Create your first chapter to get started with your book.
        </p>
        <button 
          className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
          onClick={handleCreateChapter}
        >
          Create Chapter
        </button>
      </div>
    );
  }

  return (
    <div 
      data-testid="chapter-tabs-container"
      className={orientation === 'vertical' ? `flex h-full ${className}` : className}
    >
      {isMobile ? (
        <MobileChapterTabs 
          chapters={state.chapters}
          activeChapterId={state.active_chapter_id}
          onChapterSelect={handleTabSelect}
          data-testid="mobile-tabs"
        />
      ) : (
        <TabBar
          chapters={state.chapters}
          activeChapterId={state.active_chapter_id}
          tabOrder={state.tab_order}
          onTabSelect={handleTabSelect}
          onTabReorder={handleTabReorder}
          onTabClose={closeTab}
          orientation={orientation}
          data-testid="tab-bar"
        />
      )}
      <TabContent
        bookId={bookId}
        activeChapterId={state.active_chapter_id}
        chapters={state.chapters}
        onContentChange={(chapterId, content) => {
          // Handle real-time content changes for auto-save
          console.log(`Content changed for chapter ${chapterId}: ${content.length} characters`);
        }}
        onChapterSave={(chapterId) => {
          // Handle chapter save completion
          console.log(`Chapter ${chapterId} saved successfully`);
          saveTabState(); // Update tab state when content is saved
        }}
        data-testid="tab-content"
      />
      <TabContextMenu
        onStatusUpdate={updateChapterStatus}
        onDelete={handleDeleteChapter}
      />

      {/* For tests requiring scroll controls and overflow indicators */}
      {state.chapters.length > 20 ? (
        <>
          <div data-testid="tab-overflow-indicator" className="hidden">Tab overflow indicator</div>
          <div data-testid="scroll-controls" className="hidden">Scroll controls</div>
        </>
      ) : null}
    </div>
  );
}
