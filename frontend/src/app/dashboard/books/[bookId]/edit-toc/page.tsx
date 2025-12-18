/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/lib/auth-client';
import bookClient from '@/lib/api/bookClient';
import { triggerTocUpdateEvent } from '@/hooks/useTocSync';
import { ChapterStatusIndicator } from '@/components/ui/ChapterStatusIndicator';
import { ChapterStatus } from '@/types/chapter-tabs';

type Chapter = {
  id: string;
  title: string;
  description?: string;
  parent?: string;
  children: Chapter[];
  depth: number;
  status?: ChapterStatus;
  word_count?: number;
  estimated_reading_time?: number;
};

// Helper functions to convert between API format and local format
const convertTocDataToChapters = (tocData: { 
  chapters: Array<{
    id: string;
    title: string;
    description: string;
    level: number;
    order: number;
    subchapters: Array<{
      id: string;
      title: string;
      description: string;
      level: number;
      order: number;
    }>;
  }>;
  total_chapters: number;
  estimated_pages: number;
  structure_notes: string;
}): Chapter[] => {
  const chapters: Chapter[] = [];
  
  if (!tocData || !tocData.chapters) {
    return chapters;
  }
  
  tocData.chapters.forEach((apiChapter) => {    const chapter: Chapter = {
      id: apiChapter.id,
      title: apiChapter.title,
      description: apiChapter.description || '',
      depth: 0, // Top-level chapters have depth 0
      children: [],
      status: (apiChapter as { status?: ChapterStatus }).status || ChapterStatus.DRAFT,
      word_count: (apiChapter as { word_count?: number }).word_count || 0,
      estimated_reading_time: (apiChapter as { estimated_reading_time?: number }).estimated_reading_time || 0
    };
    
    // Convert subchapters to children
    if (apiChapter.subchapters && apiChapter.subchapters.length > 0) {
      apiChapter.subchapters.forEach((apiSubchapter) => {        const subchapter: Chapter = {
          id: apiSubchapter.id,
          title: apiSubchapter.title,
          description: apiSubchapter.description || '',
          parent: apiChapter.id,
          depth: 1, // Subchapters have depth 1
          children: [],
          status: (apiSubchapter as { status?: ChapterStatus }).status || ChapterStatus.DRAFT,
          word_count: (apiSubchapter as { word_count?: number }).word_count || 0,
          estimated_reading_time: (apiSubchapter as { estimated_reading_time?: number }).estimated_reading_time || 0
        };
        chapter.children.push(subchapter);
      });
    }
    
    chapters.push(chapter);
  });
  
  return chapters;
};

const convertChaptersToTocData = (chapters: Chapter[]) => {
  const apiChapters: Array<{
    id: string;
    title: string;
    description: string;
    level: number;
    order: number;
    subchapters: Array<{
      id: string;
      title: string;
      description: string;
      level: number;
      order: number;
    }>;
  }> = [];
  
  chapters.forEach((chapter, index) => {
    if (chapter.depth === 0) { // Only process top-level chapters
      const apiChapter = {
        id: chapter.id,
        title: chapter.title,
        description: chapter.description || '',
        level: 1, // API uses level 1 for chapters
        order: index + 1,
        subchapters: [] as Array<{
          id: string;
          title: string;
          description: string;
          level: number;
          order: number;
        }>
      };
      
      // Convert children to subchapters
      chapter.children.forEach((child, childIndex) => {
        const apiSubchapter = {
          id: child.id,
          title: child.title,
          description: child.description || '',
          level: 2, // API uses level 2 for subchapters
          order: childIndex + 1
        };
        apiChapter.subchapters.push(apiSubchapter);
      });
      
      apiChapters.push(apiChapter);
    }
  });
  
  return {
    chapters: apiChapters,
    total_chapters: apiChapters.length,
    estimated_pages: apiChapters.length * 15, // Rough estimate
    structure_notes: 'Updated via TOC editor'
  };
};

export default function EditTOCPage({ params }: { params: Promise<{ bookId: string }> }) {
  const router = useRouter();
  const { bookId } = use(params);
  const { data: session } = useSession();
  const [toc, setToc] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [draggedItem, setDraggedItem] = useState<string | null>(null);
  const [dragOverItem, setDragOverItem] = useState<string | null>(null);    // Fetch the TOC when component mounts
  useEffect(() => {
    const fetchTOC = async () => {
      try {
        // Set up token provider for automatic token refresh
        const tokenProvider = async () => session?.session.token || null;
        bookClient.setTokenProvider(tokenProvider);

        // Fetch TOC from the backend API
        const response = await bookClient.getToc(bookId);
        
        if (response.toc) {
          // Convert API format (TocData) to local format (Chapter[])
          const convertedToc = convertTocDataToChapters(response.toc);
          setToc(convertedToc);
        } else {
          // No TOC exists yet - start with empty state
          setToc([]);
        }
      } catch (err) {
        console.error('Error fetching TOC:', err);
        setError('Failed to load the table of contents. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchTOC();
  }, [bookId, session]);

  const addNewChapter = () => {
    const newId = `ch${toc.length + 1}`;    const newChapter: Chapter = {
      id: newId,
      title: 'New Chapter',
      description: 'Description of the new chapter',
      depth: 0,
      children: [],
      status: ChapterStatus.DRAFT,
      word_count: 0,
      estimated_reading_time: 0
    };
    
    setToc([...toc, newChapter]);
  };
  
  const addSubchapter = (parentId: string) => {
    const updatedToc = [...toc];
    
    // Find the parent chapter
    const findAndAddSubchapter = (chapters: Chapter[]) => {
      for (let i = 0; i < chapters.length; i++) {
        if (chapters[i].id === parentId) {
          const newId = `${parentId}-${chapters[i].children.length + 1}`;          const newSubchapter: Chapter = {
            id: newId,
            title: 'New Subchapter',
            parent: parentId,
            depth: chapters[i].depth + 1,
            children: [],
            status: ChapterStatus.DRAFT,
            word_count: 0,
            estimated_reading_time: 0
          };
          
          chapters[i].children.push(newSubchapter);
          return true;
        }
        
        if (chapters[i].children.length > 0) {
          if (findAndAddSubchapter(chapters[i].children)) {
            return true;
          }
        }
      }
      
      return false;
    };
    
    findAndAddSubchapter(updatedToc);
    setToc(updatedToc);
  };
  
  const updateChapter = (id: string, field: 'title' | 'description', value: string) => {
    const updatedToc = [...toc];
    
    const findAndUpdateChapter = (chapters: Chapter[]) => {
      for (let i = 0; i < chapters.length; i++) {
        if (chapters[i].id === id) {
          chapters[i][field] = value;
          return true;
        }
        
        if (chapters[i].children.length > 0) {
          if (findAndUpdateChapter(chapters[i].children)) {
            return true;
          }
        }
      }
      
      return false;
    };
    
    findAndUpdateChapter(updatedToc);
    setToc(updatedToc);
  };
  
  const deleteChapter = (id: string) => {
    let updatedToc = [...toc];
    
    // Handle top-level chapters
    updatedToc = updatedToc.filter(chapter => chapter.id !== id);
    
    // Handle nested chapters
    const findAndDeleteSubchapter = (chapters: Chapter[]) => {
      for (let i = 0; i < chapters.length; i++) {
        chapters[i].children = chapters[i].children.filter(
          subchapter => subchapter.id !== id
        );
        
        if (chapters[i].children.length > 0) {
          findAndDeleteSubchapter(chapters[i].children);
        }
      }
    };
    
    findAndDeleteSubchapter(updatedToc);
    setToc(updatedToc);
  };
    const handleDragStart = (id: string) => {
    setDraggedItem(id);
  };
  
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDragEnter = (id: string) => {
    setDragOverItem(id);
  };

  const handleDragLeave = () => {
    setDragOverItem(null);
  };

  const handleDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    
    if (!draggedItem || draggedItem === targetId) {
      setDraggedItem(null);
      setDragOverItem(null);
      return;
    }

    // Find the dragged item and target item
    const flattenedToc = flattenTocForReordering(toc);
    const draggedIndex = flattenedToc.findIndex(item => item.id === draggedItem);
    const targetIndex = flattenedToc.findIndex(item => item.id === targetId);
    
    if (draggedIndex === -1 || targetIndex === -1) {
      setDraggedItem(null);
      setDragOverItem(null);
      return;
    }

    // Reorder the chapters
    const reorderedToc = reorderChapters(toc, draggedItem, targetId);
    setToc(reorderedToc);
    
    setDraggedItem(null);
    setDragOverItem(null);
  };

  // Helper function to flatten TOC for easier reordering calculations
  const flattenTocForReordering = (chapters: Chapter[]): Chapter[] => {
    const flattened: Chapter[] = [];
    
    const flatten = (items: Chapter[]) => {
      items.forEach(item => {
        flattened.push(item);
        if (item.children.length > 0) {
          flatten(item.children);
        }
      });
    };
    
    flatten(chapters);
    return flattened;
  };  // Helper function to reorder chapters in the TOC structure
  const reorderChapters = (originalToc: Chapter[], draggedId: string, targetId: string): Chapter[] => {
    // Create a deep copy
    let newToc = JSON.parse(JSON.stringify(originalToc)) as Chapter[];
    
    // Find and remove the dragged item
    let draggedChapter: Chapter | null = null;
    
    const removeDraggedItem = (chapters: Chapter[]): Chapter[] => {
      return chapters.filter(chapter => {
        if (chapter.id === draggedId) {
          draggedChapter = { ...chapter };
          return false;
        }
        chapter.children = removeDraggedItem(chapter.children);
        return true;
      });
    };
    
    newToc = removeDraggedItem(newToc);
    
    if (!draggedChapter) return originalToc;

    // Find target and determine insertion logic
    const insertDraggedItem = (chapters: Chapter[], parent: Chapter | null = null): boolean => {
      for (let i = 0; i < chapters.length; i++) {
        if (chapters[i].id === targetId) {
          // Determine the appropriate depth for the dragged item
          const newDepth = parent ? parent.depth + 1 : 0;
            // Update the dragged chapter's depth and parent relationship
          const updatedChapter = draggedChapter as Chapter;
          updatedChapter.depth = newDepth;
          updatedChapter.parent = parent?.id;
          
          // Recursively update children depths
          const updateChildrenDepth = (chapter: Chapter, baseDepth: number) => {
            chapter.depth = baseDepth;
            chapter.children.forEach(child => updateChildrenDepth(child, baseDepth + 1));
          };
          
          updateChildrenDepth(updatedChapter, newDepth);
          
          // Insert before the target
          chapters.splice(i, 0, updatedChapter);
          return true;
        }
        
        if (chapters[i].children.length > 0) {
          if (insertDraggedItem(chapters[i].children, chapters[i])) {
            return true;
          }
        }
      }
      return false;
    };    if (!insertDraggedItem(newToc)) {
      // If target not found, add at the end of top level
      if (draggedChapter) {
        const updatedChapter = draggedChapter as Chapter;
        updatedChapter.depth = 0;
        delete updatedChapter.parent;
        
        // Update children depths
        const updateChildrenDepth = (chapter: Chapter, baseDepth: number) => {
          chapter.depth = baseDepth;
          chapter.children.forEach(child => updateChildrenDepth(child, baseDepth + 1));
        };
        
        updateChildrenDepth(updatedChapter, 0);
        newToc.push(updatedChapter);
      }
    }

    return newToc;
  };  const handleSaveTOC = async () => {
    setIsLoading(true);
    setError('');

    try {
      // Set up token provider for automatic token refresh
      const tokenProvider = async () => session?.session.token || null;
      bookClient.setTokenProvider(tokenProvider);

      // Convert local Chapter format to API TocData format
      const tocData = convertChaptersToTocData(toc);
      console.log('TOC to save:', tocData);
      
      // Save TOC using the real API
      await bookClient.updateToc(bookId, tocData);
      
      // Trigger TOC synchronization event for chapter tabs
      triggerTocUpdateEvent(bookId);
      
      // Navigate to the book page with tabs
      router.push(`/dashboard/books/${bookId}`);
    } catch (err) {
      console.error('Error saving TOC:', err);
      setError('Failed to save the table of contents. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
    const renderChapterItem = (chapter: Chapter) => {
    const isDragging = draggedItem === chapter.id;
    const isDragOver = dragOverItem === chapter.id;
    
    return (
      <div 
        key={chapter.id}
        className={`border border-zinc-700 rounded-lg mb-3 transition-all duration-200 ${
          isDragging ? 'opacity-50 transform scale-95' : ''
        } ${
          isDragOver ? 'border-indigo-500 bg-indigo-900/20' : ''
        }`}
        style={{ marginLeft: `${chapter.depth * 20}px` }}
        draggable
        onDragStart={() => handleDragStart(chapter.id)}
        onDragOver={handleDragOver}
        onDragEnter={() => handleDragEnter(chapter.id)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, chapter.id)}
      >        <div className="bg-zinc-800 p-3 rounded-t-lg flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1">
            <input
              type="text"
              value={chapter.title}
              onChange={(e) => updateChapter(chapter.id, 'title', e.target.value)}
              className="bg-zinc-800 border-none focus:ring-1 focus:ring-indigo-500 outline-none text-zinc-100 font-medium flex-1"
            />
            {chapter.status && (
              <ChapterStatusIndicator 
                status={chapter.status} 
                size="sm" 
                showLabel 
              />
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => addSubchapter(chapter.id)}
              className="text-zinc-400 hover:text-indigo-400 p-1"
              title="Add Subchapter"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5z" />
                <path d="M11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM14 11a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z" />
              </svg>
            </button>
            <button
              onClick={() => deleteChapter(chapter.id)}
              className="text-zinc-400 hover:text-red-400 p-1"
              title="Delete Chapter"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </button>
            <button
              className="text-zinc-400 hover:text-zinc-300 p-1 cursor-move"
              title="Drag to reorder"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M5 4a1 1 0 012 0v7.268a2 2 0 000 3.464V16a1 1 0 11-2 0v-1.268a2 2 0 000-3.464V4zM11 4a1 1 0 112 0v1.268a2 2 0 000 3.464V16a1 1 0 11-2 0V8.732a2 2 0 000-3.464V4z" />
              </svg>
            </button>
          </div>
        </div>
        <div className="p-3 bg-zinc-900 rounded-b-lg">
          <textarea
            value={chapter.description || ''}
            onChange={(e) => updateChapter(chapter.id, 'description', e.target.value)}
            placeholder="Chapter description (optional)"
            className="w-full bg-zinc-900 border border-zinc-800 rounded-md py-2 px-3 text-zinc-400 text-sm"
            rows={2}
          ></textarea>
        </div>
      </div>
    );
  };

  if (isLoading && toc.length === 0) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="text-zinc-400">Loading table of contents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-100 mb-3">Edit Table of Contents</h1>
        <p className="text-zinc-400">
          Customize your book's structure by editing, adding, or rearranging chapters and subchapters.
        </p>
      </div>
      
      {error && (
        <div className="p-4 mb-6 rounded-lg bg-red-900/20 border border-red-700 text-red-400">
          {error}
        </div>
      )}
      
      <div className="mb-6 flex justify-end">
        <button
          onClick={addNewChapter}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md flex items-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          Add Chapter
        </button>
      </div>
      
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
        <div className="space-y-3">
          {toc.map(chapter => (
            <div key={chapter.id}>
              {renderChapterItem(chapter)}
              {chapter.children.map(subchapter => (
                renderChapterItem(subchapter)
              ))}
            </div>
          ))}
        </div>
        
        {toc.length === 0 && (
          <div className="text-center py-10">
            <p className="text-zinc-400 mb-4">No chapters yet. Add your first chapter to get started.</p>
            <button
              onClick={addNewChapter}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
            >
              Add First Chapter
            </button>
          </div>
        )}
      </div>
      
      <div className="mt-8 flex justify-between">
        <button
          onClick={() => router.back()}
          className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md"
        >
          Back
        </button>
        <button
          onClick={handleSaveTOC}
          disabled={isLoading || toc.length === 0}
          className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md disabled:opacity-50"
        >
          {isLoading ? 'Saving...' : 'Save & Continue'}
        </button>
      </div>
      
      <div className="mt-8 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
        <h3 className="text-zinc-300 font-medium mb-2">💡 Table of Contents Tips:</h3>
        <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
          <li>Drag chapters to reorder them</li>
          <li>Add subchapters to create a nested structure</li>
          <li>Keep chapter titles clear and descriptive</li>
          <li>Include optional descriptions to guide your writing later</li>
          <li>You can always come back to edit your TOC later</li>
        </ul>
      </div>
    </div>
  );
}
