/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

type Chapter = {
  id: string;
  title: string;
  description?: string;
  parent?: string;
  children: Chapter[];
  depth: number;
};

export default function EditTOCPage() {
  const router = useRouter();
  const [toc, setToc] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [draggedItem, setDraggedItem] = useState<string | null>(null);
  
  // Fetch the TOC when component mounts
  useEffect(() => {
    const fetchTOC = async () => {
      try {
        // In a real app, this would call your API
        // const response = await bookClient.getBookTOC(bookId);
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Sample TOC data
        const tocData: Chapter[] = [
          {
            id: 'ch1',
            title: 'Introduction to Machine Learning',
            description: 'Overview of machine learning concepts and applications',
            depth: 0,
            children: [
              {
                id: 'ch1-1',
                title: 'What is Machine Learning?',
                description: 'Definition and basic concepts',
                parent: 'ch1',
                depth: 1,
                children: []
              },
              {
                id: 'ch1-2',
                title: 'History and Evolution',
                description: 'Historical development of ML techniques',
                parent: 'ch1',
                depth: 1,
                children: []
              }
            ]
          },
          {
            id: 'ch2',
            title: 'Types of Learning Algorithms',
            description: 'Exploring different ML approaches',
            depth: 0,
            children: [
              {
                id: 'ch2-1',
                title: 'Supervised Learning',
                parent: 'ch2',
                depth: 1,
                children: []
              },
              {
                id: 'ch2-2',
                title: 'Unsupervised Learning',
                parent: 'ch2',
                depth: 1,
                children: []
              },
              {
                id: 'ch2-3',
                title: 'Reinforcement Learning',
                parent: 'ch2',
                depth: 1,
                children: []
              }
            ]
          },
          {
            id: 'ch3',
            title: 'Practical Applications',
            description: 'Real-world ML implementations',
            depth: 0,
            children: []
          }
        ];
        
        setToc(tocData);
      } catch (err) {
        console.error('Error fetching TOC:', err);
        setError('Failed to load the table of contents. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchTOC();
  }, []);

  const addNewChapter = () => {
    const newId = `ch${toc.length + 1}`;
    const newChapter: Chapter = {
      id: newId,
      title: 'New Chapter',
      description: 'Description of the new chapter',
      depth: 0,
      children: []
    };
    
    setToc([...toc, newChapter]);
  };
  
  const addSubchapter = (parentId: string) => {
    const updatedToc = [...toc];
    
    // Find the parent chapter
    const findAndAddSubchapter = (chapters: Chapter[]) => {
      for (let i = 0; i < chapters.length; i++) {
        if (chapters[i].id === parentId) {
          const newId = `${parentId}-${chapters[i].children.length + 1}`;
          const newSubchapter: Chapter = {
            id: newId,
            title: 'New Subchapter',
            parent: parentId,
            depth: chapters[i].depth + 1,
            children: []
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
  
  const handleSaveTOC = async () => {
    setIsLoading(true);
    
    try {
      // In a real app, save the updated TOC to your backend
      // await bookClient.saveTOC(bookId, toc);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Navigate to the next step
      router.push('/dashboard/books/new-book-12345/chapters');
    } catch (err) {
      console.error('Error saving TOC:', err);
      setError('Failed to save the table of contents. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const renderChapterItem = (chapter: Chapter) => {
    return (
      <div 
        key={chapter.id}
        className="border border-zinc-700 rounded-lg mb-3"
        style={{ marginLeft: `${chapter.depth * 20}px` }}
        draggable
        onDragStart={() => handleDragStart(chapter.id)}
        onDragOver={handleDragOver}
      >
        <div className="bg-zinc-800 p-3 rounded-t-lg flex items-center justify-between">
          <input
            type="text"
            value={chapter.title}
            onChange={(e) => updateChapter(chapter.id, 'title', e.target.value)}
            className="bg-zinc-800 border-none focus:ring-1 focus:ring-indigo-500 outline-none text-zinc-100 font-medium w-full"
          />
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
