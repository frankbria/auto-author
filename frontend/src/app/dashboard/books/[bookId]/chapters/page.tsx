/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { use } from 'react';

type Question = {
  id: string;
  text: string;
  isRelevant?: boolean;
};

type ChapterPrompt = {
  chapterId: string;
  chapterTitle: string;
  questions: Question[];
};

interface ChapterPromptsPageProps {
  params: Promise<{ bookId: string }>;
}

export default function ChapterPromptsPage({ params }: ChapterPromptsPageProps) {
  const { bookId } = use(params);
  const router = useRouter();
  const [activeChapter, setActiveChapter] = useState<string>('ch1');
  const [chapters, setChapters] = useState<ChapterPrompt[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  
  // Fetch chapters and their prompts when component mounts
  useEffect(() => {
    const fetchChapters = async () => {
      try {
        // In a real app, this would call your API
        // const response = await bookClient.getBookChapters(bookId);
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Sample chapter data with questions
        const chapterData: ChapterPrompt[] = [
          {
            chapterId: 'ch1',
            chapterTitle: 'Introduction to Machine Learning',
            questions: [
              {
                id: 'q1-1',
                text: 'What is the primary goal of this chapter in introducing machine learning?'
              },
              {
                id: 'q1-2',
                text: 'Who is the target audience for this introduction?'
              },
              {
                id: 'q1-3',
                text: 'What key concepts should readers understand by the end of this chapter?'
              },
              {
                id: 'q1-4',
                text: 'How will you address common misconceptions about machine learning?'
              }
            ]
          },
          {
            chapterId: 'ch2',
            chapterTitle: 'Types of Learning Algorithms',
            questions: [
              {
                id: 'q2-1',
                text: 'What are the main categories of learning algorithms you want to cover?'
              },
              {
                id: 'q2-2',
                text: 'How will you explain the differences between supervised and unsupervised learning?'
              },
              {
                id: 'q2-3',
                text: 'What real-world examples best illustrate each type of algorithm?'
              },
              {
                id: 'q2-4',
                text: 'What level of mathematical detail is appropriate for your audience?'
              }
            ]
          },
          {
            chapterId: 'ch3',
            chapterTitle: 'Practical Applications',
            questions: [
              {
                id: 'q3-1',
                text: 'Which industries or fields will you focus on for practical applications?'
              },
              {
                id: 'q3-2',
                text: 'What case studies demonstrate successful implementations of machine learning?'
              },
              {
                id: 'q3-3',
                text: 'How will you balance technical details with practical insights?'
              },
              {
                id: 'q3-4',
                text: 'What future trends in machine learning applications do you want to highlight?'
              }
            ]
          }
        ];
        
        setChapters(chapterData);
        setActiveChapter(chapterData[0].chapterId);
      } catch (err) {
        console.error('Error fetching chapters:', err);
        setError('Failed to load chapter information. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchChapters();
  }, []);

  const activeChapterData = chapters.find(chapter => chapter.chapterId === activeChapter);
  
  const regenerateQuestions = async (chapterId: string) => {
    setIsGenerating(true);
    
    try {
      // In a real app, this would call your API to regenerate questions
      // const response = await bookClient.regenerateChapterQuestions(bookId, chapterId);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Generate new questions (this would come from the API)
      const newQuestions: Question[] = [
        {
          id: `q${chapterId.substring(2)}-1-new`,
          text: 'What unique perspective will your chapter bring to this topic?'
        },
        {
          id: `q${chapterId.substring(2)}-2-new`,
          text: 'How will you structure the flow of information in this chapter?'
        },
        {
          id: `q${chapterId.substring(2)}-3-new`,
          text: 'What are the most important takeaways for readers of this chapter?'
        },
        {
          id: `q${chapterId.substring(2)}-4-new`,
          text: 'How will this chapter connect to other topics in the book?'
        },
        {
          id: `q${chapterId.substring(2)}-5-new`,
          text: 'What visual elements or diagrams would enhance understanding of these concepts?'
        }
      ];
      
      // Update the chapters with new questions
      setChapters(prevChapters => 
        prevChapters.map(chapter => 
          chapter.chapterId === chapterId
            ? { ...chapter, questions: newQuestions }
            : chapter
        )
      );
    } catch (err) {
      console.error('Error regenerating questions:', err);
      setError('Failed to regenerate questions. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };
  
  const markQuestionRelevance = (chapterId: string, questionId: string, isRelevant: boolean) => {
    setChapters(prevChapters => 
      prevChapters.map(chapter => 
        chapter.chapterId === chapterId
          ? {
              ...chapter,
              questions: chapter.questions.map(question =>
                question.id === questionId
                  ? { ...question, isRelevant }
                  : question
              )
            }
          : chapter
      )
    );
  };
  const handleContinue = () => {
    // In a real app, you would save the question ratings
    // Navigate to the tabbed interface instead of individual chapter pages
    router.push(`/dashboard/books/${bookId}`);
  };

  if (isLoading) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="text-zinc-400">Loading chapter information...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-100 mb-3">Chapter Questions</h1>
        <p className="text-zinc-400">
          Answer these interview-style questions to generate content for each chapter.
        </p>
      </div>
      
      {error && (
        <div className="p-4 mb-6 rounded-lg bg-red-900/20 border border-red-700 text-red-400">
          {error}
        </div>
      )}
      
      <div className="flex gap-6 flex-col md:flex-row">
        {/* Chapter navigation sidebar */}
        <div className="w-full md:w-64 shrink-0">
          <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-4">
            <h2 className="text-lg font-medium text-zinc-100 mb-4">Chapters</h2>
            <nav>
              <ul className="space-y-2">
                {chapters.map(chapter => (
                  <li key={chapter.chapterId}>
                    <button
                      onClick={() => setActiveChapter(chapter.chapterId)}
                      className={`w-full text-left px-3 py-2 rounded-md ${
                        activeChapter === chapter.chapterId
                          ? 'bg-indigo-600 text-white'
                          : 'hover:bg-zinc-700 text-zinc-300'
                      }`}
                    >
                      {chapter.chapterTitle}
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </div>
        
        {/* Questions for active chapter */}
        <div className="flex-1">
          <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-zinc-100">
                {activeChapterData?.chapterTitle || 'Chapter Questions'}
              </h2>
              
              <button
                onClick={() => regenerateQuestions(activeChapter)}
                disabled={isGenerating}
                className="px-3 py-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md flex items-center text-sm disabled:opacity-50"
              >
                {isGenerating ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-indigo-500 mr-2"></div>
                    Generating...
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                    </svg>
                    New Questions
                  </>
                )}
              </button>
            </div>
            
            {activeChapterData?.questions.map((question, index) => (
              <div key={question.id} className="mb-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex space-x-2 items-center">
                    <span className="text-indigo-400 font-medium">{index + 1}.</span>
                    <p className="text-zinc-100">{question.text}</p>
                  </div>
                  <div className="flex space-x-1">
                    <button
                      onClick={() => markQuestionRelevance(activeChapter, question.id, true)}
                      className={`p-1 rounded-md ${
                        question.isRelevant === true 
                          ? 'bg-green-900/30 text-green-400' 
                          : 'text-zinc-500 hover:text-green-400'
                      }`}
                      title="Mark as relevant"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </button>
                    <button
                      onClick={() => markQuestionRelevance(activeChapter, question.id, false)}
                      className={`p-1 rounded-md ${
                        question.isRelevant === false 
                          ? 'bg-red-900/30 text-red-400' 
                          : 'text-zinc-500 hover:text-red-400'
                      }`}
                      title="Mark as irrelevant"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </div>
                
                <textarea
                  placeholder="Type your answer here..."
                  className="w-full mt-2 bg-zinc-800 border border-zinc-700 rounded-md py-2 px-3 text-zinc-100"
                  rows={3}
                ></textarea>
              </div>
            ))}
            
            {activeChapterData?.questions.length === 0 && (
              <div className="text-center py-10">
                <p className="text-zinc-400">No questions for this chapter yet.</p>
                <button
                  onClick={() => regenerateQuestions(activeChapter)}
                  className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
                >
                  Generate Questions
                </button>
              </div>
            )}
          </div>
          
          <div className="mt-6 flex justify-between">
            <button
              onClick={() => router.back()}
              className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md"
            >
              Back
            </button>
            
            <div className="flex space-x-3">
              <button
                onClick={() => {
                  const currentIndex = chapters.findIndex(c => c.chapterId === activeChapter);
                  if (currentIndex > 0) {
                    setActiveChapter(chapters[currentIndex - 1].chapterId);
                  }
                }}
                disabled={chapters.findIndex(c => c.chapterId === activeChapter) === 0}
                className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous Chapter
              </button>
              
              <button
                onClick={() => {
                  const currentIndex = chapters.findIndex(c => c.chapterId === activeChapter);
                  if (currentIndex < chapters.length - 1) {
                    setActiveChapter(chapters[currentIndex + 1].chapterId);
                  } else {
                    handleContinue();
                  }
                }}
                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
              >
                {chapters.findIndex(c => c.chapterId === activeChapter) === chapters.length - 1
                  ? 'Generate Draft Content'
                  : 'Next Chapter'
                }
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div className="mt-8 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
        <h3 className="text-zinc-300 font-medium mb-2">💡 Tips for answering questions:</h3>
        <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
          <li>Provide detailed answers for better content generation</li>
          <li>Mark questions as irrelevant if they don't apply to your chapter</li>
          <li>Generate new questions if the current ones aren't helpful</li>
          <li>Your answers will be used to create a draft of your chapter content</li>
          <li>You can skip questions and come back to them later</li>
        </ul>
      </div>
    </div>
  );
}
