'use client';

import { Question, QuestionType, QuestionDifficulty, ResponseStatus } from '@/types/chapter-questions';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ThumbsUp, ThumbsDown, RefreshCw, HelpCircle, BookOpen, Map, MessageSquare, Search, Star, StarHalf, StarOff } from 'lucide-react';
import { useState, useEffect } from 'react';
import { bookClient } from '@/lib/api/bookClient';

interface QuestionDisplayProps {
  bookId: string;
  chapterId: string;
  question: Question;
  onResponseSaved: () => void;
  onRegenerateQuestion: (questionId: string) => void;
}

/**
 * Component for displaying a single question with response textarea
 * and actions for saving, rating, etc.
 */
export default function QuestionDisplay({ 
  bookId,
  chapterId,
  question,
  onResponseSaved,
  onRegenerateQuestion
}: QuestionDisplayProps) {
  // State for response text
  const [responseText, setResponseText] = useState('');
  // State for auto-saving
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState('');
  const [saveError, setSaveError] = useState('');
  // State for response completion
  const [isCompleted, setIsCompleted] = useState(false);
  // State for word count
  const [wordCount, setWordCount] = useState(0);
  // State for rating
  const [rating, setRating] = useState(0);
  
  // Load existing response if available
  useEffect(() => {
    const fetchResponse = async () => {
      try {
        const result = await bookClient.getQuestionResponse(bookId, chapterId, question.id);
        if (result && result.response) {
          setResponseText(result.response.response_text || '');
          setWordCount((result.response.response_text || '').split(/\s+/).filter(Boolean).length);
          setIsCompleted(result.response.status === ResponseStatus.COMPLETED);
        }
      } catch (error) {
        console.error('Error fetching response:', error);
      }
    };
    
    if (question.id) {
      fetchResponse();
    }
    
    // Reset states when question changes
    return () => {
      setResponseText('');
      setWordCount(0);
      setIsCompleted(false);
      setSaveStatus('');
      setSaveError('');
      setRating(0);
    };
  }, [bookId, chapterId, question.id]);
  
  // Update word count when response text changes
  useEffect(() => {
    setWordCount(responseText.split(/\s+/).filter(Boolean).length);
  }, [responseText]);
  
  // Auto-save functionality
  useEffect(() => {
    let autoSaveTimer: NodeJS.Timeout;
    
    if (responseText.trim() && !isSaving) {
      autoSaveTimer = setTimeout(() => {
        handleSaveDraft();
      }, 3000); // Auto-save after 3 seconds of inactivity
    }
    
    return () => {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
      }
    };
  }, [responseText, isSaving]);
  
  // Get question type icon
  const getQuestionTypeIcon = (type: QuestionType) => {
    switch (type) {
      case QuestionType.CHARACTER:
        return <MessageSquare className="h-5 w-5 text-purple-500" />;
      case QuestionType.PLOT:
        return <BookOpen className="h-5 w-5 text-blue-500" />;
      case QuestionType.SETTING:
        return <Map className="h-5 w-5 text-green-500" />;
      case QuestionType.THEME:
        return <Star className="h-5 w-5 text-amber-500" />;
      case QuestionType.RESEARCH:
        return <Search className="h-5 w-5 text-red-500" />;
      default:
        return <HelpCircle className="h-5 w-5 text-gray-500" />;
    }
  };
  
  // Get difficulty icon and text
  const getDifficultyInfo = (difficulty: QuestionDifficulty) => {
    switch (difficulty) {
      case QuestionDifficulty.EASY:
        return {
          icon: <StarOff className="h-5 w-5 text-green-500" />,
          text: 'Easy'
        };
      case QuestionDifficulty.MEDIUM:
        return {
          icon: <StarHalf className="h-5 w-5 text-amber-500" />,
          text: 'Medium'
        };
      case QuestionDifficulty.HARD:
        return {
          icon: <Star className="h-5 w-5 text-red-500" />,
          text: 'Hard'
        };
      default:
        return {
          icon: <StarHalf className="h-5 w-5 text-gray-500" />,
          text: 'Medium'
        };
    }
  };
  
  // Get suggested response length
  const getSuggestedLength = () => {
    return question.metadata?.suggested_response_length || 'No specific length requirement';
  };
  
  // Handle save as draft
  const handleSaveDraft = async () => {
    if (!responseText.trim()) return;
    
    setIsSaving(true);
    setSaveStatus('Saving...');
    setSaveError('');
    
    try {
      await bookClient.saveQuestionResponse(
        bookId,
        chapterId,
        question.id,
        {
          response_text: responseText,
          status: ResponseStatus.DRAFT
        }
      );
      
      setSaveStatus('Draft saved');
      // Notify parent component that response was saved
      onResponseSaved();
    } catch (error) {
      console.error('Error saving draft:', error);
      setSaveError('Failed to save draft. Please try again.');
      setSaveStatus('');
    } finally {
      setIsSaving(false);
    }
  };
  
  // Handle mark as completed
  const handleMarkCompleted = async () => {
    if (!responseText.trim()) {
      setSaveError('Please provide a response before marking as completed');
      return;
    }
    
    setIsSaving(true);
    setSaveStatus('Saving...');
    setSaveError('');
    
    try {
      await bookClient.saveQuestionResponse(
        bookId,
        chapterId,
        question.id,
        {
          response_text: responseText,
          status: ResponseStatus.COMPLETED
        }
      );
      
      setIsCompleted(true);
      setSaveStatus('Response completed');
      // Notify parent component that response was saved
      onResponseSaved();
    } catch (error) {
      console.error('Error marking as completed:', error);
      setSaveError('Failed to complete response. Please try again.');
      setSaveStatus('');
    } finally {
      setIsSaving(false);
    }
  };
  
  // Handle rating the question
  const handleRateQuestion = async (rating: number) => {
    setRating(rating);
    
    try {
      await bookClient.rateQuestion(
        bookId,
        chapterId,
        question.id,
        {
          rating
        }
      );
    } catch (error) {
      console.error('Error rating question:', error);
    }
  };
  
  // Handle regenerating the question
  const handleRegenerateQuestion = () => {
    if (onRegenerateQuestion) {
      onRegenerateQuestion(question.id);
    }
  };
  
  const difficultyInfo = getDifficultyInfo(question.difficulty);
  
  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getQuestionTypeIcon(question.question_type)}
            <CardTitle className="text-xl">{question.question_type} Question</CardTitle>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="text-sm text-muted-foreground flex items-center">
              {difficultyInfo.icon}
              <span className="ml-1">{difficultyInfo.text}</span>
            </span>
          </div>
        </div>
        
        <CardDescription>
          {/* Question text */}
          <p className="text-lg font-medium mt-4 mb-2">{question.question_text}</p>
          
          {/* Help text and examples if available */}
          {question.metadata?.help_text && (
            <div className="mt-2 text-sm text-muted-foreground">
              <p>{question.metadata.help_text}</p>
            </div>
          )}
          
          {question.metadata?.examples && question.metadata.examples.length > 0 && (
            <div className="mt-2 text-sm bg-muted/50 p-2 rounded-md">
              <p className="font-medium mb-1">Examples:</p>
              <ul className="list-disc list-inside space-y-1">
                {question.metadata.examples.map((example, i) => (
                  <li key={i}>{example}</li>
                ))}
              </ul>
            </div>
          )}
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        {/* Response textarea */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <label htmlFor="response" className="text-sm font-medium">
              Your Response
            </label>
            
            <div className="flex items-center space-x-4">
              <span className="text-xs text-muted-foreground">
                Suggested length: {getSuggestedLength()}
              </span>
              
              <span className="text-xs text-muted-foreground">
                {wordCount} words
              </span>
            </div>
          </div>
          
          <Textarea
            id="response"
            placeholder="Type your response here..."
            className="min-h-[200px] resize-y"
            value={responseText}
            onChange={(e) => setResponseText(e.target.value)}
            disabled={isSaving || isCompleted}
          />
          
          {/* Save status and error */}
          {saveStatus && (
            <p className="text-xs text-green-600">{saveStatus}</p>
          )}
          
          {saveError && (
            <p className="text-xs text-red-600">{saveError}</p>
          )}
        </div>
      </CardContent>
      
      <CardFooter className="flex flex-col space-y-4">
        {/* Action buttons */}
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-2">
            {!isCompleted ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSaveDraft}
                  disabled={isSaving || !responseText.trim()}
                >
                  Save Draft
                </Button>
                
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleMarkCompleted}
                  disabled={isSaving || !responseText.trim()}
                >
                  Complete Response
                </Button>
              </>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsCompleted(false);
                }}
              >
                Edit Response
              </Button>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleRateQuestion(1)}
              className={rating === 1 ? 'bg-red-100 dark:bg-red-900/20' : ''}
            >
              <ThumbsDown className="h-4 w-4 text-red-500" />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleRateQuestion(5)}
              className={rating === 5 ? 'bg-green-100 dark:bg-green-900/20' : ''}
            >
              <ThumbsUp className="h-4 w-4 text-green-500" />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRegenerateQuestion}
              title="Generate a new question"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {/* Info text */}
        <p className="text-xs text-muted-foreground">
          {isCompleted 
            ? "You've completed this question. You can edit your response if needed."
            : "Remember to click 'Complete Response' when you're satisfied with your answer."}
        </p>
      </CardFooter>
    </Card>
  );
}
