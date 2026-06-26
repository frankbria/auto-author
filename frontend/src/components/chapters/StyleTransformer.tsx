'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { HugeiconsIcon } from '@hugeicons/react';
import { SparklesIcon, ArrowRight01Icon } from '@hugeicons/core-free-icons';
import { toast } from '@/lib/toast';
import { bookClient } from '@/lib/api/bookClient';
import { LoadingStateManager } from '@/components/loading';
import DOMPurify from 'dompurify';
import { cn } from '@/lib/utils';

// The 5 documented styles (see #55). Kept inline to match DraftGenerator's pattern.
// ponytail: third copy; extract to a shared constant only if drift recurs.
const WRITING_STYLES = [
  { value: 'professional', label: 'Professional' },
  { value: 'conversational', label: 'Conversational' },
  { value: 'academic', label: 'Academic' },
  { value: 'creative', label: 'Creative' },
  { value: 'technical', label: 'Technical' },
];

const SANITIZE_OPTS = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'],
  ALLOWED_ATTR: ['class'],
};

interface StyleTransformerProps {
  bookId: string;
  chapterId: string;
  /** Returns the editor's current HTML to transform. */
  getCurrentContent: () => string;
  /** Apply the transformed text to the editor (caller snapshots for revert). */
  onApply: (transformed: string) => void;
  className?: string;
}

export function StyleTransformer({
  bookId,
  chapterId,
  getCurrentContent,
  onApply,
  className,
}: StyleTransformerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState<'options' | 'transforming' | 'preview'>('options');
  const [targetStyle, setTargetStyle] = useState('professional');
  const [original, setOriginal] = useState('');
  const [transformed, setTransformed] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Guard against SSR (DOMPurify needs a DOM) and skip work until there's content.
  const sanitizedOriginal = useMemo(
    () => (original ? DOMPurify.sanitize(original, SANITIZE_OPTS) : ''),
    [original]
  );
  const sanitizedTransformed = useMemo(
    () => (transformed ? DOMPurify.sanitize(transformed, SANITIZE_OPTS) : ''),
    [transformed]
  );

  const openDialog = () => {
    setIsOpen(true);
    setStep('options');
    setError(null);
    setTransformed('');
  };

  const handleTransform = async () => {
    const content = getCurrentContent();
    // TipTap renders an empty doc as "<p></p>"; treat that as empty.
    if (!content || !content.replace(/<[^>]*>/g, '').trim()) {
      setError('Add some content to the chapter before transforming its style.');
      return;
    }

    setOriginal(content);
    setError(null);
    setStep('transforming');

    try {
      const result = await bookClient.transformChapterStyle(bookId, chapterId, {
        content,
        target_style: targetStyle,
      });
      setTransformed(result.transformed);
      setStep('preview');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to transform style');
      setStep('options');
      toast({
        title: 'Transformation Failed',
        description: err instanceof Error ? err.message : 'Failed to transform style',
        variant: 'destructive',
      });
    }
  };

  const handleApply = () => {
    onApply(transformed);
    setIsOpen(false);
    const label = WRITING_STYLES.find((s) => s.value === targetStyle)?.label ?? targetStyle;
    toast({
      title: 'Style Applied',
      description: `Chapter rewritten in ${label} style. Use "Revert style" to undo.`,
    });
  };

  return (
    <>
      <Button
        onClick={openDialog}
        variant="outline"
        size="sm"
        className={cn('gap-2', className)}
        data-slot="style-transformer"
      >
        <HugeiconsIcon icon={SparklesIcon} size={16} />
        Transform Style
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Transform Writing Style</DialogTitle>
            <DialogDescription>
              {step === 'options' && 'Rewrite this chapter in a different style. Facts and meaning are preserved.'}
              {step === 'transforming' && 'Rewriting your chapter...'}
              {step === 'preview' && 'Compare the original with the transformed version before applying.'}
            </DialogDescription>
          </DialogHeader>

          {step === 'options' && (
            <div className="space-y-6 py-4">
              <div className="space-y-2">
                <Label htmlFor="transform-style">Target Style</Label>
                <Select value={targetStyle} onValueChange={setTargetStyle}>
                  <SelectTrigger id="transform-style">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WRITING_STYLES.map((style) => (
                      <SelectItem key={style.value} value={style.value}>
                        {style.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {error && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive p-3 rounded-md text-sm">
                  {error}
                </div>
              )}
            </div>
          )}

          {step === 'transforming' && (
            <div className="py-12">
              <LoadingStateManager
                isLoading={true}
                operation="Transforming Style"
                message="Rewriting your chapter in the selected style..."
                inline
              />
            </div>
          )}

          {step === 'preview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
              <div className="space-y-2">
                <Label className="text-muted-foreground">Before</Label>
                <div
                  className="border rounded-lg p-4 max-h-80 overflow-y-auto bg-muted/30 text-sm prose prose-sm max-w-none dark:prose-invert"
                  dangerouslySetInnerHTML={{ __html: sanitizedOriginal }}
                />
              </div>
              <div className="space-y-2">
                <Label className="flex items-center gap-1">
                  After
                  <HugeiconsIcon icon={ArrowRight01Icon} size={14} />
                  {WRITING_STYLES.find((s) => s.value === targetStyle)?.label}
                </Label>
                <div
                  className="border rounded-lg p-4 max-h-80 overflow-y-auto bg-muted/30 text-sm prose prose-sm max-w-none dark:prose-invert"
                  dangerouslySetInnerHTML={{ __html: sanitizedTransformed }}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            {step === 'options' && (
              <>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancel</Button>
                <Button onClick={handleTransform}>
                  <HugeiconsIcon icon={SparklesIcon} size={16} className="mr-2" />
                  Transform
                </Button>
              </>
            )}
            {step === 'preview' && (
              <>
                <Button variant="outline" onClick={() => setStep('options')}>
                  Try Another Style
                </Button>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancel</Button>
                <Button onClick={handleApply}>Apply to Chapter</Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default StyleTransformer;
