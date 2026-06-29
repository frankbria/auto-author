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

// The 4 enhancement dimensions (issue #57). Mirrors backend content_enhancement.py.
const ENHANCEMENT_TYPES = [
  { value: 'clarity', label: 'Clarity' },
  { value: 'grammar', label: 'Grammar' },
  { value: 'tone', label: 'Tone' },
  { value: 'vocabulary', label: 'Vocabulary' },
];

const SANITIZE_OPTS = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'],
  ALLOWED_ATTR: ['class'],
};

interface ContentEnhancerProps {
  bookId: string;
  chapterId: string;
  /** Returns the text to enhance — the selection if any, else the whole chapter. */
  getCurrentContent: () => string;
  /** Apply the enhanced text to the editor (caller snapshots for revert). */
  onApply: (enhanced: string) => void;
  className?: string;
}

export function ContentEnhancer({
  bookId,
  chapterId,
  getCurrentContent,
  onApply,
  className,
}: ContentEnhancerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState<'options' | 'enhancing' | 'preview'>('options');
  const [enhancementType, setEnhancementType] = useState('clarity');
  const [original, setOriginal] = useState('');
  const [enhanced, setEnhanced] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Guard against SSR (DOMPurify needs a DOM) and skip work until there's content.
  const sanitizedOriginal = useMemo(
    () => (original ? DOMPurify.sanitize(original, SANITIZE_OPTS) : ''),
    [original]
  );
  const sanitizedEnhanced = useMemo(
    () => (enhanced ? DOMPurify.sanitize(enhanced, SANITIZE_OPTS) : ''),
    [enhanced]
  );

  const openDialog = () => {
    setIsOpen(true);
    setStep('options');
    setError(null);
    setEnhanced('');
  };

  const handleEnhance = async () => {
    const content = getCurrentContent();
    // TipTap renders an empty doc as "<p></p>"; treat that as empty.
    if (!content || !content.replace(/<[^>]*>/g, '').trim()) {
      setError('Add some content to the chapter before enhancing it.');
      return;
    }

    setOriginal(content);
    setError(null);
    setStep('enhancing');

    try {
      const result = await bookClient.enhanceChapterText(bookId, chapterId, {
        content,
        enhancement_type: enhancementType,
      });
      setEnhanced(result.enhanced);
      setStep('preview');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enhance text');
      setStep('options');
      toast({
        title: 'Enhancement Failed',
        description: err instanceof Error ? err.message : 'Failed to enhance text',
        variant: 'destructive',
      });
    }
  };

  const handleApply = () => {
    onApply(enhanced);
    setIsOpen(false);
    const label = ENHANCEMENT_TYPES.find((t) => t.value === enhancementType)?.label ?? enhancementType;
    toast({
      title: 'Enhancement Applied',
      description: `Improved for ${label}. Use "Revert enhancement" to undo.`,
    });
  };

  return (
    <>
      <Button
        onClick={openDialog}
        variant="outline"
        size="sm"
        className={cn('gap-2', className)}
        data-slot="content-enhancer"
      >
        <HugeiconsIcon icon={SparklesIcon} size={16} />
        Enhance
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Enhance Content</DialogTitle>
            <DialogDescription>
              {step === 'options' && 'Improve the selected text (or the whole chapter). Facts and meaning are preserved.'}
              {step === 'enhancing' && 'Improving your text...'}
              {step === 'preview' && 'Compare the original with the enhanced version before applying.'}
            </DialogDescription>
          </DialogHeader>

          {step === 'options' && (
            <div className="space-y-6 py-4">
              <div className="space-y-2">
                <Label htmlFor="enhancement-type">Enhancement Type</Label>
                <Select value={enhancementType} onValueChange={setEnhancementType}>
                  <SelectTrigger id="enhancement-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ENHANCEMENT_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
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

          {step === 'enhancing' && (
            <div className="py-12">
              <LoadingStateManager
                isLoading={true}
                operation="Enhancing Content"
                message="Improving your text..."
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
                  {ENHANCEMENT_TYPES.find((t) => t.value === enhancementType)?.label}
                </Label>
                <div
                  className="border rounded-lg p-4 max-h-80 overflow-y-auto bg-muted/30 text-sm prose prose-sm max-w-none dark:prose-invert"
                  dangerouslySetInnerHTML={{ __html: sanitizedEnhanced }}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            {step === 'options' && (
              <>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancel</Button>
                <Button onClick={handleEnhance}>
                  <HugeiconsIcon icon={SparklesIcon} size={16} className="mr-2" />
                  Enhance
                </Button>
              </>
            )}
            {step === 'preview' && (
              <>
                <Button variant="outline" onClick={() => setStep('options')}>
                  Try Another Type
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

export default ContentEnhancer;
