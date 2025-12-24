'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Sparkles, AlertCircle, CheckCircle, Edit3 } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { bookClient } from '@/lib/api/bookClient';
import { LoadingStateManager } from '@/components/loading';
import { createProgressTracker } from '@/lib/loading';
import DOMPurify from 'dompurify';
import { cn } from '@/lib/utils';

interface DraftGenerationButtonProps {
  bookId: string;
  chapterId: string;
  chapterTitle: string;
  completedCount: number;
  totalQuestions: number;
  onDraftGenerated?: (draft: string) => void;
  onSwitchToEditor?: () => void;
  className?: string;
  minimumResponses?: number;
}

const WRITING_STYLES = [
  { value: 'conversational', label: 'Conversational' },
  { value: 'formal', label: 'Formal' },
  { value: 'narrative', label: 'Narrative' },
  { value: 'educational', label: 'Educational' },
  { value: 'inspirational', label: 'Inspirational' },
  { value: 'technical', label: 'Technical' },
];

const TARGET_LENGTHS = [
  { value: '500', label: '500 words (Short)' },
  { value: '1000', label: '1,000 words (Medium)' },
  { value: '2000', label: '2,000 words (Standard)' },
  { value: '3000', label: '3,000 words (Long)' },
  { value: '5000', label: '5,000 words (Extended)' },
];

/**
 * DraftGenerationButton - Generates AI draft from completed question responses
 *
 * This component provides the critical link between the question-answering workflow
 * and draft generation. It fetches all completed Q&A responses for a chapter and
 * uses them to generate a narrative draft.
 *
 * Features:
 * - Shows progress of completed responses
 * - Allows selection of writing style and target length
 * - Shows draft preview before insertion
 * - Integrates with chapter editor for draft insertion
 */
export function DraftGenerationButton({
  bookId,
  chapterId,
  chapterTitle,
  completedCount,
  totalQuestions,
  onDraftGenerated,
  onSwitchToEditor,
  className,
  minimumResponses = 3
}: DraftGenerationButtonProps) {
  const { toast } = useToast();

  // Dialog state
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState<'options' | 'generating' | 'preview'>('options');

  // Options
  const [writingStyle, setWritingStyle] = useState('conversational');
  const [targetLength, setTargetLength] = useState('2000');
  const [includeInProgressResponses, setIncludeInProgressResponses] = useState(false);

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedDraft, setGeneratedDraft] = useState<string | null>(null);
  const [draftMetadata, setDraftMetadata] = useState<{
    word_count: number;
    estimated_reading_time: number;
    writing_style: string;
  } | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Determine if we can generate a draft
  const canGenerate = completedCount >= minimumResponses;
  const progressPercentage = totalQuestions > 0 ? Math.round((completedCount / totalQuestions) * 100) : 0;

  // Progress tracking for draft generation
  const getProgress = useMemo(() => {
    if (!isGenerating) return null;
    return createProgressTracker('chapter.draft', {
      questionCount: completedCount,
      wordCount: parseInt(targetLength),
    });
  }, [isGenerating, completedCount, targetLength]);

  const draftProgress = getProgress ? getProgress() : { progress: 0, estimatedTimeRemaining: 0 };

  // Sanitize the generated draft
  const sanitizedDraft = useMemo(() => {
    if (!generatedDraft) return null;
    return DOMPurify.sanitize(generatedDraft, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'],
      ALLOWED_ATTR: ['class']
    });
  }, [generatedDraft]);

  const handleOpenDialog = () => {
    setIsOpen(true);
    setStep('options');
    setError(null);
    setGeneratedDraft(null);
    setDraftMetadata(null);
    setSuggestions([]);
  };

  const handleGenerateDraft = async () => {
    setIsGenerating(true);
    setStep('generating');
    setError(null);

    try {
      // Fetch all Q&A responses for this chapter
      const qaData = await bookClient.getChapterQAResponses(bookId, chapterId);

      // Filter responses based on includeInProgressResponses setting
      const responsesToUse = includeInProgressResponses
        ? qaData.responses
        : qaData.responses.filter(r => r.status === 'completed');

      if (responsesToUse.length < minimumResponses) {
        throw new Error(`Need at least ${minimumResponses} completed responses to generate a draft. You have ${responsesToUse.length}.`);
      }

      // Format for API (only question and answer, not the extra fields)
      const questionResponses = responsesToUse.map(r => ({
        question: r.question,
        answer: r.answer
      }));

      // Generate the draft
      const result = await bookClient.generateChapterDraft(bookId, chapterId, {
        question_responses: questionResponses,
        writing_style: writingStyle,
        target_length: parseInt(targetLength)
      });

      setGeneratedDraft(result.draft);
      setDraftMetadata({
        word_count: result.metadata.word_count,
        estimated_reading_time: result.metadata.estimated_reading_time,
        writing_style: result.metadata.writing_style
      });
      setSuggestions(result.suggestions || []);
      setStep('preview');

      toast({
        title: 'Draft Generated!',
        description: `Created a ${result.metadata.word_count} word draft from ${questionResponses.length} responses.`,
      });
    } catch (err) {
      console.error('Error generating draft:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate draft');
      setStep('options');

      toast({
        title: 'Generation Failed',
        description: err instanceof Error ? err.message : 'Failed to generate draft',
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
        description: 'The generated draft has been added to your chapter editor.',
      });

      // Optionally switch to editor
      if (onSwitchToEditor) {
        onSwitchToEditor();
      }
    }
  };

  const handleRegenerateDraft = () => {
    setStep('options');
    setGeneratedDraft(null);
    setDraftMetadata(null);
    setSuggestions([]);
    setError(null);
  };

  return (
    <>
      <div className={cn("flex flex-col gap-2", className)}>
        {/* Progress indicator */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {completedCount} of {totalQuestions} questions completed
          </span>
          {canGenerate ? (
            <span className="flex items-center text-green-600 dark:text-green-400">
              <CheckCircle className="h-4 w-4 mr-1" />
              Ready to generate draft
            </span>
          ) : (
            <span className="flex items-center text-amber-600 dark:text-amber-400">
              <AlertCircle className="h-4 w-4 mr-1" />
              Need {minimumResponses - completedCount} more responses
            </span>
          )}
        </div>

        {/* Generate button */}
        <Button
          onClick={handleOpenDialog}
          disabled={!canGenerate}
          variant={canGenerate ? "default" : "outline"}
          className="w-full gap-2 min-h-[44px]"
        >
          <Sparkles className="h-4 w-4" />
          Generate Draft from Answers
        </Button>
      </div>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Generate AI Draft for &quot;{chapterTitle}&quot;</DialogTitle>
            <DialogDescription>
              {step === 'options' && 'Configure your draft settings and generate content from your answers.'}
              {step === 'generating' && 'Creating your draft...'}
              {step === 'preview' && 'Review your generated draft before adding it to the editor.'}
            </DialogDescription>
          </DialogHeader>

          {/* Step: Options */}
          {step === 'options' && (
            <div className="space-y-6 py-4">
              {/* Summary of responses */}
              <div className="bg-muted/50 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Responses Summary</h4>
                <p className="text-sm text-muted-foreground">
                  You have <strong>{completedCount} completed</strong> responses out of {totalQuestions} questions ({progressPercentage}% complete).
                </p>
              </div>

              {/* Writing Style Selection */}
              <div className="space-y-2">
                <Label htmlFor="writing-style">Writing Style</Label>
                <Select value={writingStyle} onValueChange={setWritingStyle}>
                  <SelectTrigger id="writing-style">
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
                <p className="text-xs text-muted-foreground">
                  Choose a writing style that matches your book&apos;s tone.
                </p>
              </div>

              {/* Target Length */}
              <div className="space-y-2">
                <Label htmlFor="target-length">Target Word Count</Label>
                <Select value={targetLength} onValueChange={setTargetLength}>
                  <SelectTrigger id="target-length">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TARGET_LENGTHS.map(length => (
                      <SelectItem key={length.value} value={length.value}>
                        {length.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Include draft responses option */}
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="include-drafts"
                  checked={includeInProgressResponses}
                  onChange={(e) => setIncludeInProgressResponses(e.target.checked)}
                  className="rounded"
                />
                <Label htmlFor="include-drafts" className="text-sm cursor-pointer">
                  Include draft (in-progress) responses in generation
                </Label>
              </div>

              {/* Error message */}
              {error && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive p-3 rounded-md text-sm">
                  {error}
                </div>
              )}
            </div>
          )}

          {/* Step: Generating */}
          {step === 'generating' && (
            <div className="py-12">
              <LoadingStateManager
                isLoading={true}
                operation="Generating Chapter Draft"
                progress={draftProgress.progress}
                estimatedTime={draftProgress.estimatedTimeRemaining}
                message="Analyzing your responses and crafting narrative content..."
                inline
              />
            </div>
          )}

          {/* Step: Preview */}
          {step === 'preview' && generatedDraft && (
            <div className="space-y-6 py-4">
              {/* Metadata */}
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>{draftMetadata?.word_count || 0} words</span>
                <span>{draftMetadata?.estimated_reading_time || 0} min read</span>
                <span>Style: {draftMetadata?.writing_style || 'conversational'}</span>
              </div>

              {/* Draft content */}
              <div className="border rounded-lg p-4 max-h-96 overflow-y-auto bg-muted/30">
                <div
                  className="prose prose-sm max-w-none dark:prose-invert"
                  dangerouslySetInnerHTML={{ __html: sanitizedDraft || '' }}
                />
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
            </div>
          )}

          <DialogFooter>
            {step === 'options' && (
              <>
                <Button variant="outline" onClick={() => setIsOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleGenerateDraft} disabled={isGenerating}>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Draft
                </Button>
              </>
            )}

            {step === 'generating' && (
              <Button variant="outline" onClick={() => setIsOpen(false)} disabled>
                Generating...
              </Button>
            )}

            {step === 'preview' && (
              <>
                <Button variant="outline" onClick={handleRegenerateDraft}>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Regenerate
                </Button>
                <Button variant="outline" onClick={() => setIsOpen(false)}>
                  Close
                </Button>
                <Button onClick={handleUseDraft}>
                  <Edit3 className="mr-2 h-4 w-4" />
                  Use This Draft
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default DraftGenerationButton;
