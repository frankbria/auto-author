'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

type HelpCategory = {
  id: string;
  title: string;
  icon: string;
};

type HelpArticle = {
  id: string;
  title: string;
  summary: string;
  categoryId: string;
  isFeatured?: boolean;
  videoId?: string;
};

export default function HelpPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [categories, setCategories] = useState<HelpCategory[]>([]);
  const [articles, setArticles] = useState<HelpArticle[]>([]);
  const [filteredArticles, setFilteredArticles] = useState<HelpArticle[]>([]);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Fetch help content
  useEffect(() => {
    const fetchHelpContent = async () => {
      try {
        // In a real app, this would call your API
        // const response = await fetch('/api/help-content');
        // const data = await response.json();
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Sample categories
        const categoriesData: HelpCategory[] = [
          {
            id: 'getting-started',
            title: 'Getting Started',
            icon: '🚀'
          },
          {
            id: 'book-creation',
            title: 'Book Creation',
            icon: '📚'
          },
          {
            id: 'writing',
            title: 'Writing & Editing',
            icon: '✏️'
          },
          {
            id: 'ai-features',
            title: 'AI Features',
            icon: '🤖'
          },
          {
            id: 'collaboration',
            title: 'Collaboration',
            icon: '👥'
          },
          {
            id: 'export',
            title: 'Export & Publishing',
            icon: '📤'
          }
        ];
        
        // Sample articles
        const articlesData: HelpArticle[] = [
          {
            id: 'welcome-tour',
            title: 'Welcome Tour',
            summary: 'A quick overview of Auto Author and how to get started with your first book.',
            categoryId: 'getting-started',
            isFeatured: true,
            videoId: 'intro-video'
          },
          {
            id: 'create-book',
            title: 'Creating Your First Book',
            summary: 'Step-by-step guide to creating a new book project and setting up the initial structure.',
            categoryId: 'getting-started',
            isFeatured: true
          },
          {
            id: 'summary-to-toc',
            title: 'From Summary to Table of Contents',
            summary: 'Learn how to provide an effective summary and generate a well-structured table of contents.',
            categoryId: 'book-creation'
          },
          {
            id: 'edit-toc',
            title: 'Editing Your Table of Contents',
            summary: 'Tips and techniques for refining your book structure by editing the table of contents.',
            categoryId: 'book-creation'
          },
          {
            id: 'answering-prompts',
            title: 'Answering Chapter Prompts',
            summary: 'Best practices for answering the AI interview questions to generate quality content.',
            categoryId: 'writing',
            isFeatured: true
          },
          {
            id: 'voice-input',
            title: 'Using Voice-to-Text',
            summary: 'How to use the voice input feature to dictate your content instead of typing.',
            categoryId: 'writing',
            videoId: 'voice-tutorial'
          },
          {
            id: 'ai-styles',
            title: 'AI Writing Styles',
            summary: 'Understanding and customizing AI writing styles to match your voice and tone.',
            categoryId: 'ai-features'
          },
          {
            id: 'regenerating-content',
            title: 'Regenerating AI Content',
            summary: 'How to regenerate chapter content when you want to explore different approaches.',
            categoryId: 'ai-features'
          },
          {
            id: 'invite-collaborators',
            title: 'Inviting Collaborators',
            summary: 'How to invite others to review or edit your book projects.',
            categoryId: 'collaboration'
          },
          {
            id: 'reviewing-changes',
            title: 'Reviewing Collaborative Changes',
            summary: 'Managing and accepting changes from your collaborators.',
            categoryId: 'collaboration'
          },
          {
            id: 'export-formats',
            title: 'Book Export Formats',
            summary: 'Overview of the different export formats available and when to use each one.',
            categoryId: 'export'
          },
          {
            id: 'publishing-guide',
            title: 'Self-Publishing Guide',
            summary: 'A comprehensive guide to self-publishing your completed book.',
            categoryId: 'export',
            isFeatured: true
          }
        ];
        
        setCategories(categoriesData);
        setArticles(articlesData);
        setFilteredArticles(articlesData);
      } catch (error) {
        console.error('Error fetching help content:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchHelpContent();
  }, []);
  
  // Filter articles based on search and category
  useEffect(() => {
    let filtered = [...articles];
    
    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(article => 
        article.title.toLowerCase().includes(query) || 
        article.summary.toLowerCase().includes(query)
      );
    }
    
    // Filter by category
    if (activeCategory !== 'all') {
      filtered = filtered.filter(article => article.categoryId === activeCategory);
    }
    
    setFilteredArticles(filtered);
  }, [searchQuery, activeCategory, articles]);
  
  // Get selected article
  const selectedArticle = selectedArticleId 
    ? articles.find(article => article.id === selectedArticleId)
    : null;
  
  // Get featured articles
  const featuredArticles = articles.filter(article => article.isFeatured);

  if (isLoading) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="text-zinc-400">Loading help center...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <h1 className="text-3xl font-bold text-zinc-100 mb-2">Help Center</h1>
      <p className="text-zinc-400 mb-8">Find tutorials, guides, and answers to common questions</p>
      
      {/* Search */}
      <div className="mb-8">
        <div className="relative">
          <input
            type="text"
            placeholder="Search for help articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg py-3 px-4 pl-12 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
          <div className="absolute left-4 top-3.5 text-zinc-500">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
            </svg>
          </div>
        </div>
      </div>
      
      {selectedArticle ? (
        // Article Detail View
        <div className="bg-zinc-800 border border-zinc-700 rounded-lg overflow-hidden">
          <div className="p-6">
            <button 
              onClick={() => setSelectedArticleId(null)}
              className="flex items-center text-zinc-400 hover:text-indigo-400 mb-4"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
              </svg>
              Back to Help Center
            </button>
            
            <h2 className="text-2xl font-bold text-zinc-100 mb-2">{selectedArticle.title}</h2>
            <div className="flex items-center mb-6">
              <span className="bg-indigo-900/30 text-indigo-400 text-xs px-2 py-1 rounded">
                {categories.find(c => c.id === selectedArticle.categoryId)?.title}
              </span>
            </div>
            
            {selectedArticle.videoId && (
              <div className="mb-6 bg-zinc-900 rounded-lg overflow-hidden">
                <div className="aspect-w-16 aspect-h-9">
                  {/* This would be a real video in a production app */}
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="text-center">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mx-auto text-indigo-500 mb-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                      </svg>
                      <p className="text-zinc-400">Video tutorial would play here</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* This would be actual article content in a real app */}
            <div className="prose prose-invert max-w-none">
              <p className="text-zinc-300 mb-4">
                {selectedArticle.summary}
              </p>
              
              <h3 className="text-xl font-semibold text-zinc-100 mt-6 mb-4">Getting Started</h3>
              <p className="text-zinc-300 mb-4">
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
              </p>
              
              <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 my-6">
                <div className="flex items-start">
                  <div className="text-amber-500 mr-3">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2h-1V9a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div>
                    <h4 className="text-zinc-200 font-medium">Pro Tip</h4>
                    <p className="text-zinc-400 text-sm">
                      Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
                    </p>
                  </div>
                </div>
              </div>
              
              <h3 className="text-xl font-semibold text-zinc-100 mt-6 mb-4">Step-by-Step Instructions</h3>
              <ol className="list-decimal list-inside space-y-2 text-zinc-300 mb-4">
                <li>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</li>
                <li>Sed do eiusmod tempor incididunt ut labore.</li>
                <li>Ut enim ad minim veniam, quis nostrud.</li>
                <li>Duis aute irure dolor in reprehenderit.</li>
                <li>Excepteur sint occaecat cupidatat non proident.</li>
              </ol>
              
              <h3 className="text-xl font-semibold text-zinc-100 mt-6 mb-4">Common Questions</h3>
              <div className="space-y-4 mb-6">
                <div className="border-b border-zinc-700 pb-4">
                  <h4 className="text-zinc-200 font-medium mb-2">How do I save my progress?</h4>
                  <p className="text-zinc-300">
                    Your work is automatically saved as you type. You can also manually save by pressing Ctrl+S (Cmd+S on Mac) or clicking the save button in the editor.
                  </p>
                </div>
                <div className="border-b border-zinc-700 pb-4">
                  <h4 className="text-zinc-200 font-medium mb-2">Can I use Auto Author offline?</h4>
                  <p className="text-zinc-300">
                    Auto Author requires an internet connection for most features, but you can enable offline mode in settings to continue writing when disconnected. Changes will sync when you reconnect.
                  </p>
                </div>
                <div>
                  <h4 className="text-zinc-200 font-medium mb-2">How do I change the AI writing style?</h4>
                  <p className="text-zinc-300">
                    You can select different AI writing styles in the settings or when generating content for a specific chapter. Click the style selector dropdown to choose from available options.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="mt-8 pt-6 border-t border-zinc-700">
              <h3 className="text-lg font-medium text-zinc-100 mb-4">Was this article helpful?</h3>
              <div className="flex space-x-4">
                <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                  </svg>
                  Yes, it helped
                </button>
                <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.105-1.79l-.05-.025A4 4 0 0011.055 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
                  </svg>
                  No, I need more help
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        // Help Center Main View
        <>
          {/* Featured Articles */}
          {featuredArticles.length > 0 && !searchQuery && activeCategory === 'all' && (
            <div className="mb-10">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">Featured Tutorials</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {featuredArticles.map(article => (
                  <div 
                    key={article.id}
                    className="bg-zinc-800 border border-zinc-700 rounded-lg overflow-hidden hover:border-indigo-500 cursor-pointer transition-colors"
                    onClick={() => setSelectedArticleId(article.id)}
                  >
                    {article.videoId && (
                      <div className="bg-zinc-900 p-4 flex items-center justify-center h-40">
                        <div className="text-center">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 mx-auto text-indigo-500 mb-2" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                          </svg>
                          <p className="text-zinc-400 text-sm">Watch video</p>
                        </div>
                      </div>
                    )}
                    <div className="p-4">
                      <h3 className="font-medium text-zinc-100 mb-2">{article.title}</h3>
                      <p className="text-zinc-400 text-sm line-clamp-2">{article.summary}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Categories and Articles */}
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Category Navigation */}
            <div className="w-full lg:w-72 shrink-0 order-2 lg:order-1">
              <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-4 sticky top-24">
                <h3 className="text-lg font-medium text-zinc-100 mb-4">Categories</h3>
                <nav>
                  <ul className="space-y-1">
                    <li>
                      <button
                        onClick={() => setActiveCategory('all')}
                        className={`w-full text-left px-4 py-2 rounded-md ${
                          activeCategory === 'all'
                            ? 'bg-indigo-600 text-white'
                            : 'text-zinc-300 hover:bg-zinc-700'
                        }`}
                      >
                        All Categories
                      </button>
                    </li>
                    {categories.map(category => (
                      <li key={category.id}>
                        <button
                          onClick={() => setActiveCategory(category.id)}
                          className={`w-full text-left px-4 py-2 rounded-md ${
                            activeCategory === category.id
                              ? 'bg-indigo-600 text-white'
                              : 'text-zinc-300 hover:bg-zinc-700'
                          }`}
                        >
                          <span className="mr-2">{category.icon}</span>
                          {category.title}
                        </button>
                      </li>
                    ))}
                  </ul>
                </nav>
                
                <div className="mt-6 pt-6 border-t border-zinc-700">
                  <h3 className="text-lg font-medium text-zinc-100 mb-4">Need more help?</h3>
                  <div className="space-y-3">
                    <Link 
                      href="/contact" 
                      className="block px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md text-center"
                    >
                      Contact Support
                    </Link>
                    <button className="w-full px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md">
                      Join Community
                    </button>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Articles List */}
            <div className="flex-1 order-1 lg:order-2">
              {/* Category Title when filtered */}
              {activeCategory !== 'all' && (
                <h2 className="text-xl font-semibold text-zinc-100 mb-4">
                  {categories.find(c => c.id === activeCategory)?.title}
                </h2>
              )}
              
              {/* Search Results */}              {searchQuery && (
                <h2 className="text-xl font-semibold text-zinc-100 mb-4">
                  Search results for &ldquo;{searchQuery}&rdquo;
                </h2>
              )}
              
              {/* No Results */}
              {filteredArticles.length === 0 && (
                <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8 text-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto text-zinc-500 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h3 className="text-lg font-medium text-zinc-300 mb-2">No articles found</h3>                  <p className="text-zinc-400">
                    Try adjusting your search or filter to find what you&rsquo;re looking for
                  </p>
                </div>
              )}
              
              {/* Articles Grid */}
              {filteredArticles.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredArticles.map(article => (
                    <div 
                      key={article.id}
                      onClick={() => setSelectedArticleId(article.id)}
                      className="bg-zinc-800 border border-zinc-700 rounded-lg p-4 hover:border-indigo-500 cursor-pointer transition-colors"
                    >
                      <h3 className="font-medium text-zinc-100 mb-2">{article.title}</h3>
                      <p className="text-zinc-400 text-sm mb-3 line-clamp-2">{article.summary}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-indigo-400">
                          {categories.find(c => c.id === article.categoryId)?.title}
                        </span>
                        {article.videoId && (
                          <span className="text-xs bg-indigo-900/30 text-indigo-400 px-2 py-0.5 rounded-full flex items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                            </svg>
                            Video
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
