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

export default function GenerateTOCPage() {
  const router = useRouter();
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [progress, setProgress] = useState(0);
  const [toc, setToc] = useState<Chapter[]>([]);
  const [error, setError] = useState('');

  // Simulate TOC generation when the component mounts
  useEffect(() => {
    const generateTOC = async () => {
      setIsGenerating(true);
      
      // Simulate progress updates
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(interval);
            return prev;
          }
          return prev + 10;
        });
      }, 600);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 6000));
      
      // Simulate completed TOC
      clearInterval(interval);
      setProgress(100);
      
      // Sample TOC data
      const generatedTOC: Chapter[] = [
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
      
      setToc(generatedTOC);
      setIsGenerating(false);
      setIsLoaded(true);
    };
    
    generateTOC();
    
    return () => {
      // Cleanup if needed
    };
  }, []);
  
  const handleContinue = () => {
    // In a real app, you would save the TOC to your backend
    router.push('/dashboard/books/new-book-12345/edit-toc');
  };
  
  const handleRegenerate = () => {
    setIsLoaded(false);
    setProgress(0);
    setToc([]);
    
    // Restart the generation process
    setTimeout(() => {
      setIsGenerating(true);
      
      // Similar simulation as before...
      const interval = setInterval(() => {
        setProgress(prev => Math.min(prev + 15, 90));
      }, 500);
      
      setTimeout(() => {
        clearInterval(interval);
        setProgress(100);
        // Generate slightly different TOC...
        setToc([ /* slightly different structure */ ]);
        setIsGenerating(false);
        setIsLoaded(true);
      }, 4000);
    }, 500);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-100 mb-3">Generate Table of Contents</h1>
        <p className="text-zinc-400">
          Our AI is analyzing your summary to create a structured table of contents for your book.
        </p>
      </div>
      
      {error && (
        <div className="p-4 mb-6 rounded-lg bg-red-900/20 border border-red-700 text-red-400">
          {error}
        </div>
      )}
      
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
        {isGenerating && (
          <div className="mb-8">
            <div className="flex justify-between text-sm text-zinc-400 mb-2">
              <span>Generating TOC...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-zinc-700 rounded-full h-2">
              <div 
                className="bg-indigo-600 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <div className="mt-6 flex flex-col items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500 mb-4"></div>
              <p className="text-zinc-400 text-sm">
                {progress < 30 && "Analyzing your summary..."}
                {progress >= 30 && progress < 60 && "Identifying key topics and themes..."}
                {progress >= 60 && progress < 90 && "Structuring chapters and sections..."}
                {progress >= 90 && "Finalizing your table of contents..."}
              </p>
            </div>
          </div>
        )}
        
        {isLoaded && (
          <>
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">Generated Table of Contents</h2>
              
              <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
                <ul className="space-y-4">
                  {toc.map((chapter) => (
                    <li key={chapter.id}>
                      <div className="font-medium text-zinc-100">{chapter.title}</div>
                      {chapter.description && (
                        <div className="text-sm text-zinc-400 mt-1">{chapter.description}</div>
                      )}
                      
                      {chapter.children.length > 0 && (
                        <ul className="space-y-2 mt-2 pl-5">
                          {chapter.children.map((subChapter) => (
                            <li key={subChapter.id}>
                              <div className="font-medium text-zinc-300">{subChapter.title}</div>
                              {subChapter.description && (
                                <div className="text-sm text-zinc-500 mt-1">{subChapter.description}</div>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            <div className="flex justify-between">
              <button
                onClick={handleRegenerate}
                className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md flex items-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                </svg>
                Regenerate TOC
              </button>
              <button
                onClick={handleContinue}
                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
              >
                Continue to Edit TOC
              </button>
            </div>
          </>
        )}
      </div>
      
      {isLoaded && (
        <div className="mt-8 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
          <h3 className="text-zinc-300 font-medium mb-2">💡 Next steps:</h3>
          <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
            <li>Review the generated table of contents</li>
            <li>On the next screen, you can edit, add, or remove chapters</li>
            <li>You can also rearrange chapters by dragging and dropping</li>
            <li>Once you're happy with the structure, we'll move on to creating content</li>
          </ul>
        </div>
      )}
    </div>
  );
}
