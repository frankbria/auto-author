import { useState, useEffect, useCallback } from 'react';
import { ChapterTabsState, ChapterStatus, ChapterTabMetadata } from '../types/chapter-tabs';
import { chapterTabsApi } from '../lib/api/chapter-tabs';
import bookClient from '../lib/api/bookClient';
import { convertTocToChapterTabs } from '../lib/utils/toc-to-tabs-converter';

export function useChapterTabs(bookId: string, initialActiveChapter?: string) {
  const [state, setState] = useState<ChapterTabsState>({
    chapters: [],
    active_chapter_id: initialActiveChapter || null,
    open_tab_ids: [],
    tab_order: [],
    is_loading: true,
    error: null,
  });  // Load initial chapter metadata and tab state
  useEffect(() => {
    const loadChapterTabs = async () => {
      try {
        setState(prev => ({ ...prev, is_loading: true, error: null }));
        
        // First try to load chapters from the TOC structure
        let chapterTabsMetadata: ChapterTabMetadata[] = [];
        let lastActiveChapter: string | undefined;
        
        try {          // Get TOC data which contains the hierarchical structure
          const tocResponse = await bookClient.getToc(bookId);
          if (tocResponse.toc) {
            // Process chapters to ensure they have proper metadata fields
            const processedTocData = {
              ...tocResponse.toc,
              chapters: tocResponse.toc.chapters.map(ch => ({
                ...ch,
                // Add defaults for required ChapterTabMetadata properties if they don't exist
                status: (ch as { status?: ChapterStatus }).status || ChapterStatus.DRAFT,
                word_count: (ch as { word_count?: number }).word_count || 0,
                estimated_reading_time: (ch as { estimated_reading_time?: number }).estimated_reading_time || 0,
                last_modified: (ch as { last_modified?: string }).last_modified || new Date().toISOString(),
              }))
            };
            
            // Convert TOC data to chapter tab metadata format
            chapterTabsMetadata = convertTocToChapterTabs(processedTocData);
            
            console.log('Successfully loaded TOC structure and converted to chapter tabs');
          }
        } catch (tocError) {
          console.warn('Failed to load TOC structure:', tocError);
          // If TOC fails, fall back to direct chapter tabs API
          try {
            const metadata = await chapterTabsApi.getChaptersMetadata(bookId);
            chapterTabsMetadata = metadata.chapters;
            lastActiveChapter = metadata.last_active_chapter;
            
            console.log('Loaded chapter data from chapter-tabs API');
          } catch (apiError) {
            console.error('Failed to load chapter metadata:', apiError);
            // If both methods fail, we'll end up with an empty array
          }
        }        // Try to load previous tab state
        let tabState = null;        try {
          tabState = await chapterTabsApi.getTabState(bookId);
          console.log('Loaded tab state:', tabState);
        } catch {
          // Tab state might not exist, that's okay
          console.log('No previous tab state found');
        }

        // Handle chapter metadata and state
        setState(prev => ({
          ...prev,
          chapters: chapterTabsMetadata,
          active_chapter_id: tabState?.active_chapter_id || initialActiveChapter || lastActiveChapter || (chapterTabsMetadata.length > 0 ? chapterTabsMetadata[0].id : null),
          open_tab_ids: tabState?.open_tab_ids || (chapterTabsMetadata.length > 0 ? [chapterTabsMetadata[0].id] : []),
          tab_order: tabState?.tab_order || chapterTabsMetadata.map(ch => ch.id),
          is_loading: false,
        }));
      } catch (error) {
        setState(prev => ({
          ...prev,
          is_loading: false,
          error: error instanceof Error ? error.message : 'Failed to load chapter tabs'
        }));
      }
    };

    if (bookId) {
      loadChapterTabs();
    }
  }, [bookId, initialActiveChapter]);

  const setActiveChapter = useCallback((chapterId: string) => {
    setState(prevState => {
      const newState = { ...prevState, active_chapter_id: chapterId };
      
      // Add to open tabs if not already open
      if (!newState.open_tab_ids.includes(chapterId)) {
        newState.open_tab_ids = [...newState.open_tab_ids, chapterId];
        newState.tab_order = [...newState.tab_order.filter(id => id !== chapterId), chapterId];
      }
      
      return newState;
    });
  }, []);

  const reorderTabs = useCallback(async (sourceIndex: number, destinationIndex: number) => {
    setState(prevState => {
      const updatedOrder = Array.from(prevState.tab_order);
      const [movedTab] = updatedOrder.splice(sourceIndex, 1);
      updatedOrder.splice(destinationIndex, 0, movedTab);
      
      return { ...prevState, tab_order: updatedOrder };
    });
  }, []);

  const closeTab = useCallback((chapterId: string) => {
    setState(prevState => {
      const newOpenTabs = prevState.open_tab_ids.filter(id => id !== chapterId);
      const newTabOrder = prevState.tab_order.filter(id => id !== chapterId);
      
      let newActiveChapter = prevState.active_chapter_id;
      
      // If closing the active tab, switch to another open tab
      if (chapterId === prevState.active_chapter_id && newOpenTabs.length > 0) {
        // Find the next tab in the order
        const currentIndex = prevState.tab_order.indexOf(chapterId);
        const nextIndex = currentIndex < newTabOrder.length ? currentIndex : newTabOrder.length - 1;
        newActiveChapter = newTabOrder[nextIndex] || newOpenTabs[0];
      } else if (newOpenTabs.length === 0) {
        newActiveChapter = null;
      }
      
      return {
        ...prevState,
        open_tab_ids: newOpenTabs,
        tab_order: newTabOrder,
        active_chapter_id: newActiveChapter,
      };
    });
  }, []);

  const updateChapterStatus = useCallback(async (chapterId: string, status: ChapterStatus) => {
    try {
      // Optimistically update the UI
      setState(prevState => ({
        ...prevState,
        chapters: prevState.chapters.map(chapter =>
          chapter.id === chapterId ? { ...chapter, status } : chapter
        ),
      }));

      // Update the status on the server
      await chapterTabsApi.updateChapterStatus(bookId, chapterId, status);
    } catch (error) {
      // Revert the optimistic update on error
      setState(prevState => ({
        ...prevState,
        error: error instanceof Error ? error.message : 'Failed to update chapter status'
      }));
      
      // Reload chapters to get the correct state
      try {
        const metadata = await chapterTabsApi.getChaptersMetadata(bookId);
        setState(prevState => ({
          ...prevState,
          chapters: metadata.chapters,
          error: null
        }));
      } catch (reloadError) {
        console.error('Failed to reload chapters after status update error:', reloadError);
      }
    }
  }, [bookId]);

  const saveTabState = useCallback(async () => {
    try {
      await chapterTabsApi.saveTabState(bookId, {
        active_chapter_id: state.active_chapter_id,
        open_tab_ids: state.open_tab_ids,
        tab_order: state.tab_order,
      });
    } catch (error) {
      console.error('Failed to save tab state:', error);
      // Don't show this error to the user as it's not critical
    }
  }, [bookId, state.active_chapter_id, state.open_tab_ids, state.tab_order]);

  // Auto-save tab state when it changes
  useEffect(() => {
    if (!state.is_loading && state.open_tab_ids.length > 0) {
      const timeoutId = setTimeout(saveTabState, 1000); // Debounce saves
      return () => clearTimeout(timeoutId);
    }
  }, [saveTabState, state.is_loading, state.open_tab_ids, state.active_chapter_id, state.tab_order]);
  const openTab = useCallback((chapterId: string) => {
    setActiveChapter(chapterId);
  }, [setActiveChapter]);

  const refreshChapters = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, is_loading: true, error: null }));
      
      // Reload chapters from the TOC structure
      let chapterTabsMetadata: ChapterTabMetadata[] = [];
      
      try {
        const tocResponse = await bookClient.getToc(bookId);
        if (tocResponse.toc) {
          const processedTocData = {
            ...tocResponse.toc,
            chapters: tocResponse.toc.chapters.map(ch => ({
              ...ch,
              status: (ch as { status?: ChapterStatus }).status || ChapterStatus.DRAFT,
              word_count: (ch as { word_count?: number }).word_count || 0,
              estimated_reading_time: (ch as { estimated_reading_time?: number }).estimated_reading_time || 0,
              last_modified: (ch as { last_modified?: string }).last_modified || new Date().toISOString(),
            }))
          };
          
          chapterTabsMetadata = convertTocToChapterTabs(processedTocData);
          console.log('Successfully refreshed TOC structure and converted to chapter tabs');
        }
      } catch (tocError) {
        console.warn('Failed to refresh TOC structure:', tocError);
        // Fall back to direct chapter tabs API
        try {
          const metadata = await chapterTabsApi.getChaptersMetadata(bookId);
          chapterTabsMetadata = metadata.chapters;
          console.log('Refreshed chapter data from chapter-tabs API');
        } catch (apiError) {
          console.error('Failed to refresh chapter metadata:', apiError);
          throw new Error('Unable to refresh chapter data');
        }
      }

      // Handle removed chapters: if active chapter is deleted, switch to first available
      const currentActiveId = state.active_chapter_id;
      const currentOpenTabs = state.open_tab_ids;
      const currentTabOrder = state.tab_order;
      
      const existingChapterIds = chapterTabsMetadata.map(ch => ch.id);
      const validOpenTabs = currentOpenTabs.filter(id => existingChapterIds.includes(id));
      const validTabOrder = currentTabOrder.filter(id => existingChapterIds.includes(id));
      
      // Add any new chapters to tab order
      const newChapterIds = existingChapterIds.filter(id => !validTabOrder.includes(id));
      const updatedTabOrder = [...validTabOrder, ...newChapterIds];
      
      let newActiveChapter = currentActiveId;
      if (!currentActiveId || !existingChapterIds.includes(currentActiveId)) {
        // Active chapter was deleted or doesn't exist, select first available
        newActiveChapter = validOpenTabs.length > 0 ? validOpenTabs[0] : 
                          (chapterTabsMetadata.length > 0 ? chapterTabsMetadata[0].id : null);
      }
      
      // If no tabs are open, open the active chapter
      const finalOpenTabs = validOpenTabs.length > 0 ? validOpenTabs : 
                           (newActiveChapter ? [newActiveChapter] : []);

      setState(prev => ({
        ...prev,
        chapters: chapterTabsMetadata,
        active_chapter_id: newActiveChapter,
        open_tab_ids: finalOpenTabs,
        tab_order: updatedTabOrder,
        is_loading: false,
      }));
      
      console.log('Successfully refreshed chapter tabs state');
    } catch (error) {
      setState(prev => ({
        ...prev,
        is_loading: false,
        error: error instanceof Error ? error.message : 'Failed to refresh chapter tabs'
      }));
    }
  }, [bookId, state.active_chapter_id, state.open_tab_ids, state.tab_order]);

  return {
    state,
    actions: {
      setActiveChapter,
      openTab,
      reorderTabs,
      closeTab,
      updateChapterStatus,
      saveTabState,
      refreshChapters,
    },
    loading: state.is_loading,
    error: state.error,
  };
}
