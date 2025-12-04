'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sparkles, Loader2, AlertCircle, FileText } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';
import bookClient from '@/lib/api/bookClient';
import { cn } from '@/lib/utils';
import DOMPurify from 'dompurify';
import { LoadingStateManager } from '@/components/loading';
import { createProgressTracker } from '@/lib/loading';

interface DraftGeneratorProps {
  bookId: string;
  chapterId: string;
  chapterTitle: string;
  onDraftGenerated?: (draft: string) => void;
  className?: string;
}

interface QuestionResponse {
  question: string;
  answer: string;
}

const WRITING_STYLES = [
  { value: 'conversational', label: 'Conversational' },
  { value: 'formal', label: 'Formal' },
  { value: 'narrative', label: 'Narrative' },
  { value: 'educational', label: 'Educational' },
  { value: 'inspirational', label: 'Inspirational' },
  { value: 'technical', label: 'Technical' },
];

const SAMPLE_QUESTIONS = [
  "What is the main concept or idea you want to convey in this chapter?",
  "Can you share a personal story or example that illustrates this concept?",
  "What are the key takeaways you want readers to remember?",
  "How does this chapter connect to the overall theme of your book?",
  "What challenges might readers face, and how can they overcome them?",
];

export function DraftGenerator({
  bookId,
  chapterId,
  chapterTitle,
  onDraftGenerated,
  className
}: DraftGeneratorProps) {
  const { trackOperation } = usePerformanceTracking();
  const [isOpen, setIsOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [questionResponses, setQuestionResponses] = useState<QuestionResponse[]>(
    SAMPLE_QUESTIONS.map(q => ({ question: q, answer: '' }))
  );
  const [writingStyle, setWritingStyle] = useState('conversational');
  const [targetLength, setTargetLength] = useState(2000);
  const [generatedDraft, setGeneratedDraft] = useState<string | null>(null);
  const [draftMetadata, setDraftMetadata] = useState<{
    word_count: number;
    estimated_reading_time: number;
    generated_at: string;
    model_used: string;
    writing_style: string;
    target_length: number;
    actual_length: number;
  } | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Progress tracking for draft generation
  const getProgress = useMemo(() => {
    if (!isGenerating) return null;
    const validResponseCount = questionResponses.filter(qr => qr.question.trim() && qr.answer.trim()).length;
    return createProgressTracker('chapter.draft', {
      questionCount: validResponseCount,
      wordCount: targetLength,
    });
  }, [isGenerating, questionResponses, targetLength]);

  const draftProgress = getProgress ? getProgress() : { progress: 0, estimatedTimeRemaining: 0 };

  // Sanitize the generated draft to prevent XSS attacks
  const sanitizedDraft = useMemo(() => {
    if (!generatedDraft) return null;
    return DOMPurify.sanitize(generatedDraft, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'],
      ALLOWED_ATTR: ['class']
    });
  }, [generatedDraft]);
  const { toast } = useToast();

  const handleResponseChange = (index: number, value: string) => {
    const newResponses = [...questionResponses];
    newResponses[index].answer = value;
    setQuestionResponses(newResponses);
  };

  const addQuestion = () => {
    setQuestionResponses([...questionResponses, { question: '', answer: '' }]);
  };

  const removeQuestion = (index: number) => {
    setQuestionResponses(questionResponses.filter((_, i) => i !== index));
  };

  const isReadyToGenerate = () => {
    return questionResponses.some(qr => qr.question.trim() && qr.answer.trim());
  };

  const handleGenerateDraft = async () => {
    if (!isReadyToGenerate()) {
      toast({
        title: 'Missing Information',
        description: 'Please answer at least one question before generating a draft.',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    setGeneratedDraft(null);
    setDraftMetadata(null);
    setSuggestions([]);

    try {
      // Filter out empty responses
      const validResponses = questionResponses.filter(
        qr => qr.question.trim() && qr.answer.trim()
      );

      const { data: result } = await trackOperation('generate-draft', async () => {
        return await bookClient.generateChapterDraft(bookId, chapterId, {
          question_responses: validResponses,
          writing_style: writingStyle,
          target_length: targetLength,
        });
      }, { bookId, chapterId, writingStyle, targetLength, responseCount: validResponses.length });

      setGeneratedDraft(result.draft);
      setDraftMetadata(result.metadata);
      setSuggestions(result.suggestions || []);

      toast({
        title: 'Draft Generated!',
        description: `Successfully generated a ${result.metadata.word_count} word draft.`,
      });
    } catch (error) {
      console.error('Error generating draft:', error);
      toast({
        title: 'Generation Failed',
        description: error instanceof Error ? error.message : 'Failed to generate draft',
        variant: 'destructive',
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUseDraft = () => {
    if (generatedDraft && onDraftGenerated) {
      onDraftGenerated(generatedDraft);
      setIsOpen(false);
      toast({
        title: 'Draft Applied',
        description: 'The generated draft has been added to your chapter.',
      });
    }
  };

  return (
    <>
      <Button
        data-testid="generate-draft-button"
        onClick={() => setIsOpen(true)}
        variant="outline"
        size="sm"
        className={cn("gap-2", className)}
      >
        <Sparkles className="h-4 w-4" />
        Generate AI Draft
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent data-testid="draft-wizard" className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Generate AI Draft for &quot;{chapterTitle}&quot;</DialogTitle>
            <DialogDescription>
              Answer questions about your chapter to generate a personalized draft.
            </DialogDescription>
          </DialogHeader>

          {!generatedDraft ? (
            <div className="space-y-6">
              {/* Writing Style Selection */}
              <div className="space-y-2">
                <Label>Writing Style</Label>
                <Select value={writingStyle} onValueChange={setWritingStyle}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WRITING_STYLES.map(style => (
                      <SelectItem key={style.value} value={style.value}>
                        {style.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Target Length */}
              <div className="space-y-2">
                <Label>Target Word Count</Label>
                <Select value={targetLength.toString()} onValueChange={(v) => setTargetLength(parseInt(v))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="500">500 words (Short)</SelectItem>
                    <SelectItem value="1000">1,000 words (Medium)</SelectItem>
                    <SelectItem value="2000">2,000 words (Standard)</SelectItem>
                    <SelectItem value="3000">3,000 words (Long)</SelectItem>
                    <SelectItem value="5000">5,000 words (Extended)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Question/Answer Pairs */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <Label>Interview Questions</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addQuestion}
                  >
                    Add Question
                  </Button>
                </div>

                {questionResponses.map((qr, index) => (
                  <div key={index} className="space-y-2 p-4 border rounded-lg">
                    <div className="flex justify-between items-start">
                      <div className="flex-1 space-y-2">
                        <input
                          type="text"
                          placeholder="Enter your question..."
                          value={qr.question}
                          onChange={(e) => {
                            const newResponses = [...questionResponses];
                            newResponses[index].question = e.target.value;
                            setQuestionResponses(newResponses);
                          }}
                          className="w-full px-3 py-2 border rounded-md"
                        />
                        <Textarea
                          data-testid={`draft-question-${index}`}
                          placeholder="Your answer..."
                          value={qr.answer}
                          onChange={(e) => handleResponseChange(index, e.target.value)}
                          rows={3}
                        />
                      </div>
                      {questionResponses.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeQuestion(index)}
                          className="ml-2"
                        >
                          Remove
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Generate Button */}
              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => setIsOpen(false)}
                  disabled={isGenerating}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleGenerateDraft}
                  disabled={isGenerating || !isReadyToGenerate()}
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Generate Draft
                    </>
                  )}
                </Button>
              </div>
            </div>
          ) : isGenerating ? (
            <div data-testid="generating-draft" className="py-8">
              <LoadingStateManager
                isLoading={true}
                operation="Generating Chapter Draft"
                progress={draftProgress.progress}
                estimatedTime={draftProgress.estimatedTimeRemaining}
                message="Analyzing your responses and creating narrative content..."
                inline
              />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Generated Draft Display */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label>Generated Draft</Label>
                  <div className="text-sm text-muted-foreground">
                    {draftMetadata?.word_count || 0} words • 
                    {' '}{draftMetadata?.estimated_reading_time || 0} min read
                  </div>
                </div>
                <div className="border rounded-lg p-4 max-h-96 overflow-y-auto bg-muted/30">
                  <div 
                    className="text-sm leading-relaxed whitespace-pre-wrap"
                    dangerouslySetInnerHTML={{ __html: sanitizedDraft || '' }}
                  />
                </div>
              </div>

              {/* Suggestions */}
              {suggestions.length > 0 && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Improvement Suggestions
                  </Label>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    {suggestions.map((suggestion, index) => (
                      <li key={index}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex justify-between">
                <Button
                  variant="outline"
                  onClick={() => {
                    setGeneratedDraft(null);
                    setDraftMetadata(null);
                    setSuggestions([]);
                  }}
                >
                  Generate New Draft
                </Button>
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={() => setIsOpen(false)}
                  >
                    Close
                  </Button>
                  <Button onClick={handleUseDraft}>
                    <FileText className="mr-2 h-4 w-4" />
                    Use This Draft
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}