'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { HugeiconsIcon } from '@hugeicons/react';
import { AlertCircleIcon } from '@hugeicons/core-free-icons';
import { QuestionDifficulty, QuestionType } from '@/types/chapter-questions';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { FOCUS_OPTIONS } from '@/lib/questionFocus';

interface QuestionGeneratorProps {
  bookId: string;
  chapterId: string;
  onGenerate: (
    count?: number,
    difficulty?: QuestionDifficulty,
    focus?: QuestionType[]
  ) => Promise<void>;
  isGenerating: boolean;
  error: string | null;
  /** False after a refusal that trying again cannot change: a plan or an exhausted allowance (#855). */
  canRetry?: boolean;
}

export default function QuestionGenerator({
  // We store these but don't use them directly in this component
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  bookId,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  chapterId,
  onGenerate,
  isGenerating,
  error,
  canRetry = true
}: QuestionGeneratorProps) {
  // State for generation options
  const [questionCount, setQuestionCount] = useState<number>(10);
  const [difficulty, setDifficulty] = useState<QuestionDifficulty | undefined>(undefined);
  const [focusTypes, setFocusTypes] = useState<QuestionType[]>([]);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState<boolean>(false);

  // Toggle question type in focus array
  const toggleQuestionType = (type: QuestionType) => {
    if (focusTypes.includes(type)) {
      setFocusTypes(focusTypes.filter(t => t !== type));
    } else {
      setFocusTypes([...focusTypes, type]);
    }
  };

  // Handle generate button click
  const handleGenerate = async () => {
    // Use focus types only if some are selected
    const focus = focusTypes.length > 0 ? focusTypes : undefined;

    await onGenerate(questionCount, difficulty, focus);
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Generate Interview Questions</CardTitle>
        <CardDescription>
          Generate tailored questions to help you develop your chapter content through
          a guided interview process. Answer these questions to explore key aspects of your chapter.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Basic options */}
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <Label htmlFor="question-count">Number of questions: {questionCount}</Label>
            </div>
            <Slider
              id="question-count"
              aria-label="Number of questions"
              min={5}
              max={20}
              step={1}
              value={[questionCount]}
              onValueChange={(values) => setQuestionCount(values[0])}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>5 (Brief)</span>
              <span>10</span>
              <span>20 (Comprehensive)</span>
            </div>
          </div>

          <div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              className="text-xs"
            >
              {showAdvancedOptions ? 'Hide' : 'Show'} Advanced Options
            </Button>
          </div>
        </div>

        {/* Advanced options */}
        {showAdvancedOptions && (
          <div className="space-y-6 border rounded-md p-4 bg-muted/20">
            {/* Difficulty selection */}
            <div className="space-y-2">
              <Label>Question Difficulty</Label>
              <RadioGroup
                value={difficulty}
                onValueChange={(value) => setDifficulty(value as QuestionDifficulty || undefined)}
                className="flex space-x-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="" id="difficulty-any" />
                  <Label htmlFor="difficulty-any" className="font-normal">Any</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={QuestionDifficulty.EASY} id="difficulty-easy" />
                  <Label htmlFor="difficulty-easy" className="font-normal">Easy</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={QuestionDifficulty.MEDIUM} id="difficulty-medium" />
                  <Label htmlFor="difficulty-medium" className="font-normal">Medium</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={QuestionDifficulty.HARD} id="difficulty-hard" />
                  <Label htmlFor="difficulty-hard" className="font-normal">Hard</Label>
                </div>
              </RadioGroup>
            </div>

            {/* Question types focus */}
            <div className="space-y-2">
              <Label>Question Focus (optional)</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
                {FOCUS_OPTIONS.map((option) => (
                  <div key={option.type} className="flex items-start space-x-2">
                    <Checkbox
                      id={`focus-${option.type}`}
                      aria-describedby={`focus-${option.type}-desc`}
                      checked={focusTypes.includes(option.type)}
                      onCheckedChange={() => toggleQuestionType(option.type)}
                      className="mt-0.5"
                    />
                    <div className="grid gap-1.5 leading-none">
                      <Label htmlFor={`focus-${option.type}`} className="font-medium">
                        {option.label}
                      </Label>
                      <p id={`focus-${option.type}-desc`} className="text-xs text-muted-foreground">
                        {option.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Select specific question types to focus on, or leave unchecked for a balanced mix.
              </p>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="bg-destructive/10 p-3 rounded-md text-destructive text-sm flex items-center">
            <HugeiconsIcon icon={AlertCircleIcon} size={16} className="mr-2" />
            {error}
          </div>
        )}
      </CardContent>

      <CardFooter>
        <Button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="w-full"
        >
          {isGenerating ? (
            <>
              <span className="animate-spin mr-2">◌</span>
              Generating Questions...
            </>
          ) : error && canRetry ? (
            <>Retry</>
          ) : (
            <>Generate Interview Questions</>
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
