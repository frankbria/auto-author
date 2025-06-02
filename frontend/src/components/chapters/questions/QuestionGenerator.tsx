'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, BookOpen, HelpCircle, Brain, Sparkles } from 'lucide-react';
import { QuestionDifficulty, QuestionType } from '@/types/chapter-questions';
import { Label } from '@/components/ui/label';

// Stub components for UI elements that will be properly implemented later
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const Checkbox = ({ id, checked, onCheckedChange, className }: { id: string, checked: boolean, onCheckedChange: (checked: boolean) => void, className?: string }) => (
  <div className={`w-4 h-4 border rounded ${checked ? 'bg-primary' : 'bg-transparent'} ${className}`} onClick={() => onCheckedChange(!checked)} />
);

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const RadioGroup = ({ value, onValueChange, className, children }: { value?: string, onValueChange: (value: string) => void, className?: string, children: React.ReactNode }) => (
  <div className={className}>{children}</div>
);

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const RadioGroupItem = ({ value, id }: { value: string, id: string }) => (
  <div className="w-4 h-4 border rounded-full" />
);

const Tooltip = ({ children }: { children: React.ReactNode }) => <>{children}</>;
const TooltipProvider = ({ children }: { children: React.ReactNode }) => <>{children}</>;
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const TooltipTrigger = ({ asChild, children }: { asChild?: boolean, children: React.ReactNode }) => <>{children}</>;
const TooltipContent = ({ children }: { children: React.ReactNode }) => <>{children}</>;

const Slider = ({ id, min, max, step, value, onValueChange, className }: { 
  id: string, 
  min: number, 
  max: number, 
  step: number, 
  value: number[], 
  onValueChange: (values: number[]) => void, 
  className?: string 
}) => (
  <input 
    type="range" 
    id={id} 
    min={min} 
    max={max} 
    step={step} 
    value={value[0]} 
    onChange={(e) => onValueChange([parseInt(e.target.value)])}
    className={className} 
  />
);

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
}

export default function QuestionGenerator({
  // We store these but don't use them directly in this component
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  bookId,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  chapterId,
  onGenerate,
  isGenerating,
  error
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

  // Question type options with descriptions
  const questionTypeOptions = [
    {
      type: QuestionType.CHARACTER,
      label: 'Character',
      description: 'Questions about characters, their motivations, development, and relationships',
      icon: <BookOpen className="h-4 w-4" />
    },
    {
      type: QuestionType.PLOT,
      label: 'Plot',
      description: 'Questions about story structure, events, conflicts, and resolutions',
      icon: <Sparkles className="h-4 w-4" />
    },
    {
      type: QuestionType.SETTING,
      label: 'Setting',
      description: 'Questions about world-building, locations, time periods, and atmosphere',
      icon: <HelpCircle className="h-4 w-4" />
    },
    {
      type: QuestionType.THEME,
      label: 'Theme',
      description: 'Questions about central ideas, messages, symbolism, and deeper meaning',
      icon: <Brain className="h-4 w-4" />
    }
  ];

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
                {questionTypeOptions.map((option) => (
                  <TooltipProvider key={option.type}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="flex items-start space-x-2">
                          <Checkbox
                            id={`focus-${option.type}`}
                            checked={focusTypes.includes(option.type)}
                            onCheckedChange={() => toggleQuestionType(option.type)}
                            className="mt-0.5"
                          />
                          <div className="grid gap-1.5 leading-none">
                            <Label htmlFor={`focus-${option.type}`} className="font-medium flex items-center">
                              {option.icon} <span className="ml-1">{option.label}</span>
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              {option.description.substring(0, 40)}...
                            </p>
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs">{option.description}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
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
            <AlertCircle className="h-4 w-4 mr-2" />
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
          ) : (
            <>Generate Interview Questions</>
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
