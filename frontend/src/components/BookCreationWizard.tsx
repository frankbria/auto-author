'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { bookCreationSchema, BookFormData } from '@/lib/schemas/bookSchema';
import bookClient from '@/lib/api/bookClient';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { HugeiconsIcon } from '@hugeicons/react';
import { Loading03Icon } from '@hugeicons/core-free-icons';

type BookCreationWizardProps = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (bookId: string) => void;
};

const genreOptions = [
  { label: 'Fiction', value: 'fiction' },
  { label: 'Non-Fiction', value: 'non-fiction' },
  { label: 'Science Fiction', value: 'sci-fi' },
  { label: 'Fantasy', value: 'fantasy' },
  { label: 'Mystery', value: 'mystery' },
  { label: 'Romance', value: 'romance' },
  { label: 'Historical', value: 'historical' },
  { label: 'Biography', value: 'biography' },
  { label: 'Self-Help', value: 'self-help' },
  { label: 'Business', value: 'business' },
  { label: 'Other', value: 'other' },
];

const targetAudienceOptions = [
  { label: 'Children', value: 'children' },
  { label: 'Young Adult', value: 'young-adult' },
  { label: 'Adult', value: 'adult' },
  { label: 'General', value: 'general' },
  { label: 'Academic', value: 'academic' },
  { label: 'Professional', value: 'professional' },
];

export function BookCreationWizard({ isOpen, onOpenChange, onSuccess }: BookCreationWizardProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const form = useForm<BookFormData>({
    resolver: zodResolver(bookCreationSchema),
    defaultValues: {
      title: '',
      subtitle: '',
      description: '',
      genre: '',
      target_audience: '',
      cover_image_url: '',
    },
  });

  const onSubmit = async (data: BookFormData) => {
    try {
      setIsSubmitting(true);
      const book = await bookClient.createBook({
        title: data.title,
        subtitle: data.subtitle,
        description: data.description,
        genre: data.genre,
        target_audience: data.target_audience, // pass as targetAudience for API compatibility
        cover_image_url: data.cover_image_url,
      });
      toast.success('Book created successfully!');
      form.reset();
      onOpenChange(false);
      if (onSuccess) {
        onSuccess(book.id);
      } else {
        router.push(`/dashboard/books/${book.id}`);
      }
    } catch (error) {
      console.error('Error creating book:', error);
      toast.error('Failed to create book. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] bg-background border-input text-foreground dark:bg-gray-900 dark:border-gray-800 dark:text-gray-100">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold">Create New Book</DialogTitle>
          <DialogDescription className="text-muted-foreground dark:text-gray-400">
            Fill in the details for your new book project. You can edit these later.
          </DialogDescription>
        </DialogHeader>
        <FormProvider {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 py-2">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground dark:text-gray-200">Book Title *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Enter book title"
                      className="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100"
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormMessage className="text-destructive dark:text-red-400" />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="subtitle"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground dark:text-gray-200">Subtitle</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Enter subtitle (optional)"
                      className="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100"
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormMessage className="text-destructive dark:text-red-400" />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground dark:text-gray-200">Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Enter a brief description of your book"
                      className="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 resize-none min-h-[100px]"
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormDescription className="text-muted-foreground dark:text-gray-500">
                    Provide a short summary or description of your book project.
                  </FormDescription>
                  <FormMessage className="text-destructive dark:text-red-400" />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="cover_image_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground dark:text-gray-200">Cover Image URL</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="https://example.com/cover.jpg"
                      className="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100"
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormDescription className="text-muted-foreground dark:text-gray-500">
                    Optional: Add a URL to your book&apos;s cover image.
                  </FormDescription>
                  <FormMessage className="text-destructive dark:text-red-400" />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="genre"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-foreground dark:text-gray-200">Genre</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                      disabled={isSubmitting}
                    >
                      <FormControl>
                        <SelectTrigger className="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100">
                          <SelectValue placeholder="Select genre" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent className="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100">
                        {genreOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage className="text-destructive dark:text-red-400" />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="target_audience"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-foreground dark:text-gray-200">Target Audience</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                      disabled={isSubmitting}
                    >
                      <FormControl>
                        <SelectTrigger className="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100">
                          <SelectValue placeholder="Select target audience" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent className="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100">
                        {targetAudienceOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage className="text-destructive dark:text-red-400" />
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                className="dark:bg-transparent dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-gray-100"
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                className="bg-primary hover:bg-primary/90 text-primary-foreground dark:bg-indigo-600 dark:hover:bg-indigo-700 dark:text-white"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <HugeiconsIcon icon={Loading03Icon} size={16} className="mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Book'
                )}
              </Button>
            </DialogFooter>
          </form>
        </FormProvider>
      </DialogContent>
    </Dialog>
  );
}
