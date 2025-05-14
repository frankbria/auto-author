'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import bookClient from '@/lib/api/bookClient';

export default function NewBook() {
  const [bookData, setBookData] = useState({
    title: '',
    description: '',
    genre: '',
    targetAudience: '',
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setBookData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      // Use the book client to create a new book
      await bookClient.createBook({
        title: bookData.title,
        description: bookData.description
      });
      
      // Redirect to dashboard after successful creation
      router.push('/dashboard');
    } catch (error) {
      console.error('Error creating book:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-zinc-100 mb-6">Create New Book</h1>
        
        <div className="bg-zinc-800 rounded-lg p-6">
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="title" className="block text-sm font-medium text-zinc-300 mb-1">
                Book Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="title"
                name="title"
                value={bookData.title}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-md text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Enter the title of your book"
              />
            </div>
              <div className="mb-4">
              <label htmlFor="description" className="block text-sm font-medium text-zinc-300 mb-1">
                Description
              </label>
              <textarea
                id="description"
                name="description"
                value={bookData.description}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-md text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Enter a description of your book (optional)"
                rows={4}
              />
            </div>
            
            <div className="mb-4">
              <label htmlFor="genre" className="block text-sm font-medium text-zinc-300 mb-1">
                Genre <span className="text-red-500">*</span>
              </label>
              <select
                id="genre"
                name="genre"
                value={bookData.genre}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-md text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select a genre</option>
                <option value="business">Business & Economics</option>
                <option value="science">Science & Technology</option>
                <option value="selfHelp">Self-Help & Personal Development</option>
                <option value="history">History & Biography</option>
                <option value="health">Health & Wellness</option>
                <option value="philosophy">Philosophy</option>
                <option value="education">Education & Reference</option>
                <option value="other">Other Non-Fiction</option>
              </select>
            </div>
            
            <div className="mb-6">
              <label htmlFor="targetAudience" className="block text-sm font-medium text-zinc-300 mb-1">
                Target Audience <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="targetAudience"
                name="targetAudience"
                value={bookData.targetAudience}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-md text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Who is this book for?"
              />
            </div>
            
            <div className="flex justify-end mt-6 space-x-4">
              <button
                type="button"
                onClick={() => router.push('/dashboard')}
                className="px-4 py-2 bg-transparent border border-zinc-600 text-zinc-300 hover:bg-zinc-700 rounded-md transition"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md transition flex items-center"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creating...
                  </>
                ) : 'Create Book'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
