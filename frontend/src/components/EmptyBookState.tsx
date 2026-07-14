'use client';

import { Button } from '@/components/ui/button';
import Image from 'next/image';

interface EmptyBookStateProps {
  onCreateNew: () => void;
}

export function EmptyBookState({ onCreateNew }: EmptyBookStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-10 bg-card/50 rounded-xl border border-border text-center my-8 max-w-2xl mx-auto">
      <div className="relative h-40 w-40 mb-6">
        <Image
          src="/book-placeholder.svg"
          alt="Empty book shelf"
          fill
          className="object-contain opacity-70"
          sizes="(max-width: 768px) 100vw, 160px"
          priority
        />
      </div>

      <h3 className="text-2xl font-semibold text-foreground mb-3">Start Your First Book</h3>

      <p className="text-muted-foreground mb-6 max-w-md">
        Create your first book project and begin your writing journey. Auto Author will help you
        organize your ideas and generate a structured outline.
      </p>

      <div className="space-y-4 w-full max-w-sm">
        <Button
          onClick={onCreateNew}
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-6 text-lg"
        >
          Create New Book
        </Button>

        <div className="grid grid-cols-3 gap-4 mt-8">
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted/40">
            <span className="text-foreground text-sm mb-1">1. Create</span>
            <span className="text-xs text-muted-foreground">Enter book details</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted/40">
            <span className="text-foreground text-sm mb-1">2. Outline</span>
            <span className="text-xs text-muted-foreground">Generate table of contents</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted/40">
            <span className="text-foreground text-sm mb-1">3. Write</span>
            <span className="text-xs text-muted-foreground">Draft your content</span>
          </div>
        </div>
      </div>
    </div>
  );
}
