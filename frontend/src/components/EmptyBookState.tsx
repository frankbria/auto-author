'use client';

import { Button } from '@/components/ui/button';
import Image from 'next/image';

interface EmptyBookStateProps {
  onCreateNew: () => void;
}

export function EmptyBookState({ onCreateNew }: EmptyBookStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-10 bg-gray-800/50 rounded-xl border border-gray-700 text-center my-8 max-w-2xl mx-auto">
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

      <h3 className="text-2xl font-semibold text-gray-200 mb-3">Start Your First Book</h3>

      <p className="text-gray-400 mb-6 max-w-md">
        Create your first book project and begin your writing journey. Auto Author will help you
        organize your ideas and generate a structured outline.
      </p>

      <div className="space-y-4 w-full max-w-sm">
        <Button
          onClick={onCreateNew}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-6 text-lg"
        >
          Create New Book
        </Button>

        <div className="grid grid-cols-3 gap-4 mt-8">
          <div className="flex flex-col items-center p-3 rounded-lg bg-gray-700/40">
            <span className="text-gray-200 text-sm mb-1">1. Create</span>
            <span className="text-xs text-gray-400">Enter book details</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-gray-700/40">
            <span className="text-gray-200 text-sm mb-1">2. Outline</span>
            <span className="text-xs text-gray-400">Generate table of contents</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-gray-700/40">
            <span className="text-gray-200 text-sm mb-1">3. Write</span>
            <span className="text-xs text-gray-400">Draft your content</span>
          </div>
        </div>
      </div>
    </div>
  );
}
