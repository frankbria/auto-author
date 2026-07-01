'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { HugeiconsIcon } from '@hugeicons/react';
import { RefreshIcon } from '@hugeicons/core-free-icons';
import { QuestionType, QuestionDifficulty } from '@/types/chapter-questions';

const FOCUS_OPTIONS: { value: QuestionType; label: string }[] = [
  { value: QuestionType.CHARACTER, label: 'Character' },
  { value: QuestionType.PLOT, label: 'Plot' },
  { value: QuestionType.SETTING, label: 'Setting' },
  { value: QuestionType.THEME, label: 'Theme' },
  { value: QuestionType.RESEARCH, label: 'Research' },
];

interface RegenerateQuestionsDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (
    options: { difficulty?: QuestionDifficulty; focus?: QuestionType[] },
    preserveResponses: boolean
  ) => void;
  isRegenerating: boolean;
}

/**
 * Options dialog for regenerating an entire chapter's question set.
 * Lets the author pick focus areas and whether to keep answered questions.
 */
export default function RegenerateQuestionsDialog({
  isOpen,
  onOpenChange,
  onConfirm,
  isRegenerating,
}: RegenerateQuestionsDialogProps) {
  const [focus, setFocus] = useState<QuestionType[]>([]);
  const [preserveResponses, setPreserveResponses] = useState(true);

  const toggleFocus = (value: QuestionType) => {
    setFocus((prev) =>
      prev.includes(value) ? prev.filter((f) => f !== value) : [...prev, value]
    );
  };

  const handleConfirm = () => {
    onConfirm({ focus: focus.length > 0 ? focus : undefined }, preserveResponses);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Regenerate all questions</DialogTitle>
          <DialogDescription>
            Generate a fresh set of interview questions for this chapter. Choose focus areas
            and whether to keep questions you&apos;ve already answered.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div>
            <p className="text-sm font-medium mb-2">Focus areas (optional)</p>
            <div className="grid grid-cols-2 gap-2">
              {FOCUS_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                >
                  <Checkbox
                    checked={focus.includes(opt.value)}
                    onCheckedChange={() => toggleFocus(opt.value)}
                    aria-label={opt.label}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="preserve-responses" className="text-sm">
              Keep answered questions
            </Label>
            <Switch
              id="preserve-responses"
              checked={preserveResponses}
              onCheckedChange={setPreserveResponses}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isRegenerating}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={isRegenerating}>
            {isRegenerating ? (
              <>
                <HugeiconsIcon icon={RefreshIcon} size={16} className="mr-2 animate-spin" />
                Regenerating...
              </>
            ) : (
              <>
                <HugeiconsIcon icon={RefreshIcon} size={16} className="mr-2" />
                Regenerate
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
