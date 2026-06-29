'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { HugeiconsIcon } from '@hugeicons/react';
import { SparklesIcon, ArrowRight01Icon } from '@hugeicons/core-free-icons';
import { toast } from '@/lib/toast';
import { bookClient } from '@/lib/api/bookClient';
import { LoadingStateManager } from '@/components/loading';
import DOMPurify from 'dompurify';
import { cn } from '@/lib/utils';

const SANITIZE_OPTS = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'],
  ALLOWED_ATTR: ['class'],
};

interface VoiceEnhancerProps {
  bookId: string;
  chapterId: string;
  /** Returns the text to clean up — the selection if any, else the whole chapter. */
  getCurrentContent: () => string;
  /** Apply the cleaned-up text to the editor (caller snapshots for revert). */
  onApply: (enhanced: string) => void;
  className?: string;
}

/**
 * Voice/dictation cleanup dialog (issue #56). Turns raw transcription into
 * readable prose — filler removal, paragraph breaks, grammar/punctuation —
 * with a side-by-side raw-vs-cleaned preview before applying. Single mode,
 * preview-only; mirrors ContentEnhancer (#57).
 */
export function VoiceEnhancer({
  bookId,
  chapterId,
  getCurrentContent,
  onApply,
  className,
}: VoiceEnhancerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState<'intro' | 'enhancing' | 'preview'>('intro');
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
    setStep('intro');
    setError(null);
    setEnhanced('');
  };

  const handleCleanup = async () => {
    const content = getCurrentContent();
    // TipTap renders an empty doc as "<p></p>"; treat that as empty.
    if (!content || !content.replace(/<[^>]*>/g, '').trim()) {
      setError('Dictate or add some text before cleaning it up.');
      return;
    }

    setOriginal(content);
    setError(null);
    setStep('enhancing');

    try {
      const result = await bookClient.enhanceVoiceTranscription(bookId, chapterId, {
        content,
      });
      setEnhanced(result.enhanced);
      setStep('preview');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clean up transcription');
      setStep('intro');
      toast({
        title: 'Cleanup Failed',
        description: err instanceof Error ? err.message : 'Failed to clean up transcription',
        variant: 'destructive',
      });
    }
  };

  const handleApply = () => {
    onApply(enhanced);
    setIsOpen(false);
    toast({
      title: 'Cleanup Applied',
      description: 'Dictation cleaned up. Use "Revert enhancement" to undo.',
    });
  };

  return (
    <>
      <Button
        onClick={openDialog}
        variant="outline"
        size="sm"
        className={cn('gap-2', className)}
        data-slot="voice-enhancer"
      >
        <HugeiconsIcon icon={SparklesIcon} size={16} />
        Clean up dictation
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Clean Up Dictation</DialogTitle>
            <DialogDescription>
              {step === 'intro' && 'Remove filler words, add paragraph breaks, and fix grammar and punctuation in your dictated text. Facts and meaning are preserved.'}
              {step === 'enhancing' && 'Cleaning up your dictation...'}
              {step === 'preview' && 'Compare your raw dictation with the cleaned-up version before applying.'}
            </DialogDescription>
          </DialogHeader>

          {step === 'intro' && error && (
            <div className="py-4">
              <div className="bg-destructive/10 border border-destructive/20 text-destructive p-3 rounded-md text-sm">
                {error}
              </div>
            </div>
          )}

          {step === 'enhancing' && (
            <div className="py-12">
              <LoadingStateManager
                isLoading={true}
                operation="Cleaning Up Dictation"
                message="Removing fillers and formatting your text..."
                inline
              />
            </div>
          )}

          {step === 'preview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
              <div className="space-y-2">
                <Label className="text-muted-foreground">Raw dictation</Label>
                <div
                  className="border rounded-lg p-4 max-h-80 overflow-y-auto bg-muted/30 text-sm prose prose-sm max-w-none dark:prose-invert"
                  dangerouslySetInnerHTML={{ __html: sanitizedOriginal }}
                />
              </div>
              <div className="space-y-2">
                <Label className="flex items-center gap-1">
                  Cleaned up
                  <HugeiconsIcon icon={ArrowRight01Icon} size={14} />
                </Label>
                <div
                  className="border rounded-lg p-4 max-h-80 overflow-y-auto bg-muted/30 text-sm prose prose-sm max-w-none dark:prose-invert"
                  dangerouslySetInnerHTML={{ __html: sanitizedEnhanced }}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            {step === 'intro' && (
              <>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancel</Button>
                <Button onClick={handleCleanup}>
                  <HugeiconsIcon icon={SparklesIcon} size={16} className="mr-2" />
                  Clean up
                </Button>
              </>
            )}
            {step === 'preview' && (
              <>
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

export default VoiceEnhancer;
