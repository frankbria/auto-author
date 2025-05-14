'use client';

import { useRouter } from 'next/navigation';
import { Card, CardContent, CardFooter, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export type BookProject = {
  id: string;
  title: string;
  description?: string;
  lastEdited: string;
  progress: number;
  chapters: number;
};

type BookCardProps = {
  book: BookProject;
  onClick?: () => void;
};

export default function BookCard({ book, onClick }: BookCardProps) {
  const router = useRouter();
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };
  
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      router.push(`/dashboard/books/${book.id}`);
    }
  };

  return (
    <Card 
      className="w-[350px] bg-zinc-800 border border-zinc-700 hover:border-indigo-500 transition cursor-pointer"
      onClick={handleClick}
    >
      <div className="p-5">
        <CardTitle className="text-xl font-semibold text-zinc-100 mb-2 truncate" title={book.title}>
          {book.title}
        </CardTitle>
      </div>
      
      <CardContent>
        {book.description && (
          <p className="text-zinc-400 text-sm mb-3 line-clamp-2" title={book.description}>
            {book.description}
          </p>
        )}
        
        <div className="flex items-center text-sm text-zinc-400 mb-4">
          <span>Last edited {formatDate(book.lastEdited)}</span>
          <span className="mx-2">•</span>
          <span>{book.chapters} chapters</span>
        </div>
        
        <div className="mb-4">
          <div className="w-full bg-zinc-700 rounded-full h-2">
            <div 
              className="bg-indigo-600 h-2 rounded-full" 
              style={{ width: `${book.progress}%` }}
            ></div>
          </div>
          <div className="flex justify-between mt-1 text-sm text-zinc-400">
            <span>Progress</span>
            <span>{book.progress}%</span>
          </div>
        </div>
      </CardContent>
      
      <CardFooter className="px-5 pt-0">
        <Button
          className="w-full bg-zinc-700 hover:bg-indigo-600 text-zinc-100"
          onClick={(e) => {
            e.stopPropagation();
            router.push(`/dashboard/books/${book.id}`);
          }}
        >
          Open Project
        </Button>
      </CardFooter>
    </Card>
  );
}
