/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function BookSummaryPage() {
  const router = useRouter();
  const [summary, setSummary] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState('');
  
  // Speech recognition setup
  const startListening = () => {
    if (!('webkitSpeechRecognition' in window)) {
      setError('Speech recognition is not supported in your browser.');
      return;
    }
    
    setIsListening(true);
    
    // This would be the actual implementation with Web Speech API
    // const recognition = new webkitSpeechRecognition();
    // recognition.continuous = true;
    // recognition.interimResults = true;
    // recognition.lang = 'en-US';
    
    // recognition.onresult = (event) => {
    //   let transcript = '';
    //   for (let i = event.resultIndex; i < event.results.length; ++i) {
    //     if (event.results[i].isFinal) {
    //       transcript += event.results[i][0].transcript;
    //     }
    //   }
    //   setSummary(prev => prev + ' ' + transcript);
    // };
    
    // recognition.onerror = (event) => {
    //   setError('Error occurred in recognition: ' + event.error);
    //   setIsListening(false);
    // };
    
    // recognition.onend = () => {
    //   setIsListening(false);
    // };
    
    // recognition.start();
    
    // For demo purposes, simulate speech recognition
    setTimeout(() => {
      setSummary(prev => prev + " This is simulated speech-to-text for the book summary feature. In a real implementation, this would capture your spoken words.");
      setIsListening(false);
    }, 3000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!summary.trim()) {
      setError('Please provide a summary of your book');
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      // In a real app, this would call your API to store the summary
      // and move to the TOC generation step
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Navigate to the TOC generation page
      router.push('/dashboard/books/new-book-12345/generate-toc');
    } catch (err) {
      console.error('Error saving summary:', err);
      setError('Failed to save summary. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-100 mb-3">Provide a Summary</h1>
        <p className="text-zinc-400">
          Describe your book's main concepts and structure. This summary will be used to generate a Table of Contents.
        </p>
      </div>
      
      {error && (
        <div className="p-4 mb-6 rounded-lg bg-red-900/20 border border-red-700 text-red-400">
          {error}
        </div>
      )}
      
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <label className="text-zinc-400" htmlFor="summary">Book Summary</label>
              <button
                type="button"
                onClick={startListening}
                disabled={isListening}
                className={`px-3 py-1 rounded-md text-sm ${
                  isListening 
                    ? 'bg-red-600 text-white' 
                    : 'bg-zinc-700 hover:bg-zinc-600 text-zinc-100'
                }`}
              >
                {isListening ? 'Listening...' : '🎤 Voice Input'}
              </button>
            </div>
            <textarea
              id="summary"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={10}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-2 px-3 text-zinc-100"
              placeholder="Describe your book's main concepts, structure, and key points that should be organized into chapters..."
              required
            ></textarea>
            <div className="flex justify-between text-xs text-zinc-500 mt-1">
              <span>{summary.length} characters</span>
              <span>Minimum recommended: 200 characters</span>
            </div>
          </div>
          
          <div className="flex justify-between mt-6">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md"
            >
              Back
            </button>
            <button
              type="submit"
              disabled={isLoading || summary.length < 10}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : 'Continue to TOC Generation'}
            </button>
          </div>
        </form>
      </div>
      
      <div className="mt-8 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
        <h3 className="text-zinc-300 font-medium mb-2">💡 Tips for a good summary:</h3>
        <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
          <li>Include the main topics you want to cover in your book</li>
          <li>Mention specific sections or chapters you have in mind</li>
          <li>Include your target audience and their needs</li>
          <li>Consider the overall structure (e.g., beginner to advanced)</li>
          <li>The more detail you provide, the better your TOC will be</li>
        </ul>
      </div>
    </div>
  );
}
