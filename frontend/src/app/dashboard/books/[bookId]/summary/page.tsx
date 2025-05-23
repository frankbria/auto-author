/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import bookClient from '@/lib/api/bookClient';

// Validation helpers
const MIN_SUMMARY_LENGTH = 30;
const MAX_SUMMARY_LENGTH = 2000;
const OFFENSIVE_REGEX = /\b(fuck|shit|bitch|asshole|bastard|dick|cunt|nigger|faggot|slut|whore)\b/i;
const NON_ENGLISH_REGEX = /[\u0400-\u04FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]/; // Cyrillic, Arabic, CJK, Japanese, Korean

const validateSummary = (text: string) => {
  if (!text.trim()) return 'Please provide a summary of your book.';
  if (text.length < MIN_SUMMARY_LENGTH)
    return `Summary must be at least ${MIN_SUMMARY_LENGTH} characters.`;
  if (text.length > MAX_SUMMARY_LENGTH)
    return `Summary must be at most ${MAX_SUMMARY_LENGTH} characters.`;
  if (OFFENSIVE_REGEX.test(text))
    return 'Summary contains inappropriate language.';
  if (NON_ENGLISH_REGEX.test(text))
    return 'Please write your summary in English.';
  return '';
};

export default function BookSummaryPage() {
  const router = useRouter();
  const params = useParams();
  const bookId = typeof params?.bookId === 'string' ? params.bookId : Array.isArray(params?.bookId) ? params.bookId[0] : '';
  const [summary, setSummary] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState('');
  const saveTimeout = useRef<NodeJS.Timeout | null>(null);
  const lastSaved = useRef('');
  const [summaryHistory, setSummaryHistory] = useState<unknown[]>([]);
  const [inputError, setInputError] = useState('');

  // Load summary and history from remote on mount
  useEffect(() => {
    if (!bookId) return;
    setIsLoading(true);
    bookClient.getBookSummary(bookId)
      .then((data) => {
        setSummary(data.summary || '');
        setSummaryHistory(data.summary_history || []);
        lastSaved.current = data.summary || '';
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [bookId]);

  // Auto-save to localStorage and remote (debounced)
  useEffect(() => {
    if (!bookId) return;
    // Save to localStorage
    localStorage.setItem(`book-summary-${bookId}`, summary);
    // Debounce remote save
    if (saveTimeout.current) clearTimeout(saveTimeout.current);
    if (summary !== lastSaved.current) {
      saveTimeout.current = setTimeout(() => {
        bookClient.saveBookSummary(bookId, summary)
          .then((data) => {
            lastSaved.current = data.summary;
          })
          .catch(() => {});
      }, 1000);
    }
    return () => {
      if (saveTimeout.current) clearTimeout(saveTimeout.current);
    };
  }, [summary, bookId]);

  // Restore from localStorage if available (for offline/refresh)
  useEffect(() => {
    if (!bookId) return;
    const local = localStorage.getItem(`book-summary-${bookId}`);
    if (local && !summary) setSummary(local);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId]);

  // Real-time validation
  useEffect(() => {
    setInputError(validateSummary(summary));
  }, [summary]);

  // Speech recognition setup
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const startListening = () => {
    const SpeechRecognitionCtor =
      (window.SpeechRecognition || window.webkitSpeechRecognition) as typeof SpeechRecognition | undefined;
    if (!SpeechRecognitionCtor) {
      setError('Speech recognition is not supported in your browser.');
      return;
    }
    setError('');
    setIsListening(true);
    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          transcript += event.results[i][0].transcript;
        }
      }
      if (transcript) {
        setSummary(prev => (prev ? prev + ' ' : '') + transcript.trim());
      }
    };
    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      setError('Error occurred in recognition: ' + event.error);
      setIsListening(false);
    };
    recognition.onend = () => {
      setIsListening(false);
    };
    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.onresult = null;
      recognitionRef.current.onerror = null;
      recognitionRef.current.onend = null;
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
  };

  // Add revert handler (type-safe)
  type Revision = { summary: string; timestamp?: string };
  const handleRevert = (revIdx: number) => {
    const rev = summaryHistory[revIdx] as Revision;
    if (rev && typeof rev.summary === 'string') {
      setSummary(rev.summary);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validation = validateSummary(summary);
    if (validation) {
      setError(validation);
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      await bookClient.saveBookSummary(bookId, summary);
      router.push(`/dashboard/books/${bookId}/generate-toc`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setIsListening(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-100 mb-3">Provide a Summary</h1>
        <p className="text-zinc-400">
          Describe your book's main concepts and structure. This summary will be used to generate a Table of Contents.
        </p>
      </div>
      {error && (
        <div className="p-4 mb-6 rounded-lg bg-red-900/20 border border-red-700 text-red-400">
          {error}
        </div>
      )}
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <label className="text-zinc-400" htmlFor="summary">Book Summary</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={startListening}
                  disabled={isListening}
                  className={`px-3 py-1 rounded-md text-sm ${
                    isListening 
                      ? 'bg-red-600 text-white' 
                      : 'bg-zinc-700 hover:bg-zinc-600 text-zinc-100'
                  }`}
                >
                  {isListening ? 'Listening...' : '🎤 Voice Input'}
                </button>
                {isListening && (
                  <button
                    type="button"
                    onClick={stopListening}
                    className="px-3 py-1 rounded-md text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-100 border border-zinc-500"
                  >
                    Stop
                  </button>
                )}
              </div>
            </div>
            <textarea
              id="summary"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={10}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-2 px-3 text-zinc-100"
              placeholder="Describe your book's main concepts, structure, and key points that should be organized into chapters..."
              required
            ></textarea>
            <div className="flex justify-between text-xs text-zinc-500 mt-1">
              <span>{summary.length} characters</span>
              <span>Minimum: {MIN_SUMMARY_LENGTH} characters</span>
            </div>
            {inputError && (
              <div className="text-red-400 text-xs mt-1">{inputError}</div>
            )}
            <div id="summary-help" className="text-xs text-zinc-400 mt-2">
              <div>Guidelines: Aim for 1-3 paragraphs. Include the main idea, genre, and any key themes or characters. Minimum 30 words recommended.</div>
              <div className="italic text-zinc-500 mt-1">
                &quot;A young orphan discovers a hidden world of magic and must stop a dark sorcerer from conquering both realms. The story explores friendship, courage, and the power of believing in oneself.&quot;
              </div>
            </div>
          </div>
          <div className="flex justify-between mt-6">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md"
            >
              Back
            </button>
            <button
              type="submit"
              disabled={isLoading || !!inputError}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : 'Continue to TOC Generation'}
            </button>
          </div>
        </form>
      </div>
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 mt-8">
        <h2 className="text-lg font-semibold text-zinc-100 mb-2">Revision History</h2>
        {summaryHistory.length === 0 ? (
          <div className="text-zinc-400 text-sm">No previous revisions yet.</div>
        ) : (
          <ul className="space-y-3">
            {summaryHistory.slice().reverse().map((rev, idx) => {
              const revision = rev as Revision;
              return (
                <li key={idx} className="border-b border-zinc-700 pb-2">
                  <div className="flex justify-between items-center">
                    <div className="text-xs text-zinc-400">
                      {revision.timestamp
                        ? new Date(revision.timestamp).toLocaleString()
                        : 'Unknown time'}
                    </div>
                    <button
                      className="text-indigo-400 text-xs hover:underline"
                      onClick={() => handleRevert(summaryHistory.length - 1 - idx)}
                    >
                      Revert
                    </button>
                  </div>
                  <div className="text-zinc-200 text-sm mt-1 whitespace-pre-line">
                    {revision.summary}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <div className="mt-8 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
        <h3 className="text-zinc-300 font-medium mb-2">💡 Tips for a good summary:</h3>
        <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
          <li>Include the main topics you want to cover in your book</li>
          <li>Mention specific sections or chapters you have in mind</li>
          <li>Include your target audience and their needs</li>
          <li>Consider the overall structure (e.g., beginner to advanced)</li>
          <li>The more detail you provide, the better your TOC will be</li>
        </ul>
      </div>
    </div>
  );
}