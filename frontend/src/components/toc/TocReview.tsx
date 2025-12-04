import { useState } from 'react';
import { TocGenerationResult, TocChapter } from '@/types/toc';
import { ChapterStatusIndicator } from '@/components/ui/ChapterStatusIndicator';

interface TocReviewProps {
  tocResult: TocGenerationResult;
  onAccept: () => void;
  onRegenerate: () => void;
  isLoading: boolean;
}

export default function TocReview({ tocResult, onAccept, onRegenerate, isLoading }: TocReviewProps) {
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(new Set());

  const toggleChapter = (chapterId: string) => {
    setExpandedChapters(prev => {
      const newSet = new Set(prev);
      if (newSet.has(chapterId)) {
        newSet.delete(chapterId);
      } else {
        newSet.add(chapterId);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    setExpandedChapters(new Set(tocResult.toc.chapters.map(ch => ch.id)));
  };

  const collapseAll = () => {
    setExpandedChapters(new Set());
  };

  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-zinc-100 mb-3">
          Your Generated Table of Contents
        </h2>
        <p className="text-zinc-400">
          Review the generated structure below. You can accept it as-is or regenerate for a different approach.
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
          <div className="text-2xl font-bold text-indigo-400">{tocResult.toc.total_chapters}</div>
          <div className="text-zinc-400 text-sm">Total Chapters</div>
        </div>
        
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
          <div className="text-2xl font-bold text-purple-400">{tocResult.toc.estimated_pages}</div>
          <div className="text-zinc-400 text-sm">Estimated Pages</div>
        </div>
        
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-400">
            {tocResult.has_subchapters ? 'Yes' : 'No'}
          </div>
          <div className="text-zinc-400 text-sm">Has Subchapters</div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-zinc-100">Chapter Structure</h3>
        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="px-3 py-1 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="px-3 py-1 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* TOC Display */}
      <div data-testid="generated-toc" className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 mb-6 max-h-96 overflow-y-auto">
        <div className="space-y-3">
          {tocResult.toc.chapters.map((chapter, index) => (
            <ChapterItem
              key={chapter.id}
              chapter={chapter}
              index={index + 1}
              isExpanded={expandedChapters.has(chapter.id)}
              onToggle={() => toggleChapter(chapter.id)}
              expandedChapters={expandedChapters}
              toggleChapter={toggleChapter}
            />
          ))}
        </div>
      </div>

      {/* Structure notes */}
      {tocResult.toc.structure_notes && (
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 mb-6">
          <h4 className="text-zinc-300 font-medium mb-2">📝 AI Structure Notes</h4>
          <p className="text-zinc-400 text-sm">{tocResult.toc.structure_notes}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-4">
        <button
          onClick={onRegenerate}
          disabled={isLoading}
          className="flex-1 px-6 py-3 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:text-zinc-500 text-zinc-100 font-medium rounded-md transition-colors flex items-center justify-center"
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
              Regenerating...
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
              Try Different Structure
            </>
          )}
        </button>
        
        <button
          onClick={onAccept}
          disabled={isLoading}
          className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:text-green-400 text-white font-medium rounded-md transition-colors flex items-center justify-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          Accept & Continue
        </button>
      </div>

      <div className="mt-6 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
        <h4 className="text-zinc-300 font-medium mb-2">✨ Next steps:</h4>
        <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
          <li>Accept this structure to proceed to detailed editing</li>
          <li>You&apos;ll be able to modify individual chapters and subchapters</li>
          <li>Add, remove, or rearrange sections as needed</li>
          <li>Set detailed descriptions and content outlines</li>
        </ul>
      </div>
    </div>
  );
}

interface ChapterItemProps {
  chapter: TocChapter;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
  expandedChapters?: Set<string>;
  toggleChapter?: (id: string) => void;
  parentIndex?: string;
}

function ChapterItem({ chapter, index, isExpanded, onToggle, expandedChapters, toggleChapter, parentIndex }: ChapterItemProps) {
  const hasSubchapters = chapter.subchapters && chapter.subchapters.length > 0;
  const idx = parentIndex ? `${parentIndex}.${index}` : `${index}`;

  return (
    <div data-testid="chapter-item" className="border border-zinc-700 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between p-4 bg-zinc-800 hover:bg-zinc-750 cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center flex-1">
          <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-white text-sm font-medium mr-3">
            {idx}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h4 data-testid="chapter-title" className="text-zinc-100 font-medium">{chapter.title}</h4>
              {chapter.status && (
                <ChapterStatusIndicator 
                  status={chapter.status} 
                  size="sm" 
                  showLabel 
                />
              )}
            </div>
            {chapter.description && (
              <p className="text-zinc-400 text-sm mt-1">{chapter.description}</p>
            )}
            {chapter.word_count && (
              <div className="flex items-center gap-2 text-xs text-zinc-500 mt-1">
                <span>{chapter.word_count} words</span>
                {chapter.estimated_reading_time && (
                  <>
                    <span>•</span>
                    <span>{chapter.estimated_reading_time}min read</span>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
        
        {hasSubchapters && (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`h-5 w-5 text-zinc-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        )}
      </div>
      {hasSubchapters && isExpanded && (
        <div className="bg-zinc-900 p-4 border-t border-zinc-700">
          <div className="space-y-3">
            {chapter.subchapters.map((subchapter, subIndex) => {
              const subId = subchapter.id;
              const subExpanded = expandedChapters?.has(subId) ?? false;
              return (
                <ChapterItem
                  key={subId}
                  chapter={subchapter as TocChapter}
                  index={subIndex + 1}
                  isExpanded={subExpanded}
                  onToggle={() => toggleChapter && toggleChapter(subId)}
                  expandedChapters={expandedChapters}
                  toggleChapter={toggleChapter}
                  parentIndex={idx}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
