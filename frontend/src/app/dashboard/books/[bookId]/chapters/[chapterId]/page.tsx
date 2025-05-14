'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ChapterContentPage() {
  const router = useRouter();
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [progress, setProgress] = useState(0);
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  // Simulate loading the chapter and generating content
  useEffect(() => {
    const generateContent = async () => {
      setIsGenerating(true);
      
      // Simulate progress updates
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(interval);
            return prev;
          }
          return prev + 5;
        });
      }, 400);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 4000));
      
      // Simulate completed content generation
      clearInterval(interval);
      setProgress(100);
      
      // Sample chapter content
      const generatedContent = `
# Introduction to Machine Learning

Machine learning is a field of inquiry devoted to understanding and building methods that 'learn' – that is, methods that leverage data to improve performance on some task. It is seen as a part of artificial intelligence.

## What is Machine Learning?

Machine learning algorithms build a model based on sample data, known as training data, in order to make predictions or decisions without being explicitly programmed to do so. Machine learning algorithms are used in a wide variety of applications, such as in medicine, email filtering, speech recognition, and computer vision, where it is difficult or unfeasible to develop conventional algorithms to perform the needed tasks.

### Key Concepts

- **Training data**: The dataset used to train the machine learning model.
- **Features**: The input variables used for prediction.
- **Labels**: The output variable to be predicted.
- **Model**: The representation learned from the data.
- **Prediction**: The output of the model for new, unseen data.

## History and Evolution

The term "machine learning" was coined in 1959 by Arthur Samuel, an IBM employee and pioneer in the field of computer gaming and artificial intelligence. The interest in machine learning has increased dramatically in recent decades, driven by:

1. Increasing volumes and varieties of available data
2. Computational processing that is cheaper and more powerful
3. Affordable data storage

These technological advances have created an environment where machine learning techniques can be more effective and efficient, enabling the development of increasingly advanced models and applications.

### Major Milestones

- **1950s**: Early AI research and the development of the perceptron.
- **1960s-1970s**: Development of symbolic reasoning approaches.
- **1980s**: Resurgence of interest in neural networks.
- **1990s**: Support Vector Machines and statistical learning theory.
- **2000s**: Growth of machine learning as a field.
- **2010s**: Deep learning revolution and significant advances in neural networks.

## Why Machine Learning Matters

Machine learning has become essential in today's world because it allows computers to find insights from data without being explicitly programmed where to look. This capability is particularly valuable in areas where the rules are too complex to code manually or where they change over time.

The impact of machine learning can be seen across various domains:

- **Healthcare**: Diagnosis assistance, drug discovery, and patient care optimization.
- **Finance**: Fraud detection, algorithmic trading, and credit scoring.
- **Transportation**: Autonomous vehicles and traffic prediction.
- **Customer Service**: Chatbots and recommendation systems.
- **Manufacturing**: Quality control and predictive maintenance.

In the next chapter, we will explore the different types of machine learning algorithms and when to apply them.
`;
      
      setContent(generatedContent);
      setIsGenerating(false);
      setIsLoaded(true);
      setLastSaved(new Date());
    };
    
    generateContent();
    
    // Set up auto-save
    const autoSaveInterval = setInterval(() => {
      if (isLoaded && !isGenerating && content) {
        handleSave();
      }
    }, 60000); // Auto-save every minute
    
    return () => {
      clearInterval(autoSaveInterval);
    };
  });
  
  const handleSave = async () => {
    setIsSaving(true);
    
    try {
      // In a real app, this would call your API to save the content
      // await bookClient.saveChapterContent(bookId, chapterId, content);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Update last saved time
      setLastSaved(new Date());
    } catch (err) {
      console.error('Error saving chapter content:', err);
      setError('Failed to save content. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };
  
  const formatLastSaved = () => {
    if (!lastSaved) return '';
    
    return lastSaved.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-zinc-100">Introduction to Machine Learning</h1>
          <p className="text-zinc-400 mt-1">
            {isGenerating ? 'Generating draft content...' : 'Edit and refine your chapter content'}
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          {lastSaved && (
            <span className="text-zinc-500 text-sm">
              Last saved at {formatLastSaved()}
            </span>
          )}
          
          <button
            onClick={handleSave}
            disabled={isGenerating || isSaving}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
      
      {error && (
        <div className="p-4 mb-6 rounded-lg bg-red-900/20 border border-red-700 text-red-400">
          {error}
        </div>
      )}
      
      {isGenerating && (
        <div className="mb-8">
          <div className="flex justify-between text-sm text-zinc-400 mb-2">
            <span>Generating draft content...</span>
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
              {progress < 30 && "Analyzing question responses..."}
              {progress >= 30 && progress < 60 && "Organizing key concepts and ideas..."}
              {progress >= 60 && progress < 90 && "Drafting content sections..."}
              {progress >= 90 && "Finalizing chapter content..."}
            </p>
          </div>
        </div>
      )}
      
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg mb-6">
        <div className="border-b border-zinc-700 p-3 bg-zinc-900 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button className="p-2 text-zinc-400 hover:text-zinc-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </button>
            <button className="p-2 text-zinc-400 hover:text-zinc-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </button>
            <div className="h-5 border-r border-zinc-700"></div>
            <button className="p-2 text-zinc-400 hover:text-zinc-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
            </button>
            <button className="p-2 text-zinc-400 hover:text-zinc-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
              </svg>
            </button>
            <button className="p-2 text-zinc-400 hover:text-zinc-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
              </svg>
            </button>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-zinc-500 text-sm">Draft</span>
            <button className="p-2 text-zinc-400 hover:text-zinc-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
        
        <div className="p-6">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full bg-zinc-800 border-0 focus:ring-0 text-zinc-100 min-h-[60vh]"
            placeholder="Chapter content will appear here..."
            disabled={isGenerating}
          ></textarea>
        </div>
      </div>
      
      <div className="flex justify-between">
        <div className="flex space-x-3">
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md"
          >
            Back to Prompts
          </button>
          <button
            onClick={() => {
              // In a real app, trigger content regeneration
              setIsLoaded(false);
              setContent('');
              setProgress(0);
              setIsGenerating(true);
              
              const interval = setInterval(() => {
                setProgress(prev => Math.min(prev + 10, 90));
              }, 400);
              
              setTimeout(() => {
                clearInterval(interval);
                setProgress(100);
                setContent("Regenerated content would appear here...");
                setIsGenerating(false);
                setIsLoaded(true);
                setLastSaved(new Date());
              }, 3000);
            }}
            disabled={isGenerating}
            className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md flex items-center disabled:opacity-50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
            </svg>
            Regenerate Content
          </button>
        </div>
        
        <button
          onClick={() => router.push('/dashboard/books/new-book-12345')}
          className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
        >
          View All Chapters
        </button>
      </div>
      
      <div className="mt-8 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
        <h3 className="text-zinc-300 font-medium mb-2">💡 Editing Tips:</h3>
        <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
          <li>Edit the generated text to better match your voice and style</li>
          <li>Use Markdown formatting for headings, lists, and emphasis</li>
          <li>Content is auto-saved every minute, but you can save manually anytime</li>
          <li>Regenerate content if you want to start fresh with a new draft</li>
          <li>View the full book structure to see how this chapter fits with others</li>
        </ul>
      </div>
    </div>
  );
}
