import React from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { bookCreationSchema, BookFormData } from '../lib/schemas/bookSchema';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from './ui/select';
import { FormField, FormItem, FormLabel, FormControl, FormMessage } from './ui/form';

// These options should match those used in the main BookPage
const genreOptions = [
  { label: 'Fiction', value: 'fiction' },
  { label: 'Non-Fiction', value: 'non-fiction' },
  { label: 'Fantasy', value: 'fantasy' },
  { label: 'Science Fiction', value: 'sci-fi' },
  { label: 'Mystery', value: 'mystery' },
  { label: 'Romance', value: 'romance' },
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

export interface BookMetadataFormProps {
  book: BookFormData;
  onUpdate: (data: BookFormData) => void;
  isSaving?: boolean;
  error?: string | null;
}

export const BookMetadataForm: React.FC<BookMetadataFormProps> = ({ book, onUpdate, isSaving, error }) => {
  const form = useForm<BookFormData>({
    resolver: zodResolver(bookCreationSchema),
    defaultValues: book,
    mode: 'onChange',
  });

  // Use a hash of the book fields as a unique key for reset detection
  const getBookKey = (b: BookFormData) =>
    [b.title, b.subtitle, b.description, b.genre, b.target_audience, b.cover_image_url].join('||');
  const [lastBookKey, setLastBookKey] = React.useState(getBookKey(book));
  const [lastSaved, setLastSaved] = React.useState(book);

  // Only reset if a new book is loaded (by key)
  React.useEffect(() => {
    const newKey = getBookKey(book);
    if (newKey !== lastBookKey) {
      form.reset(book);
      setLastBookKey(newKey);
      setLastSaved(book);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [book, form]);

  React.useEffect(() => {
    const subscription = form.watch((values) => {
      const safeValues = {
        title: values.title || '',
        subtitle: values.subtitle ?? '',
        description: values.description ?? '',
        genre: values.genre ?? '',
        target_audience: values.target_audience ?? '',
        cover_image_url: values.cover_image_url ?? '',
      };
      if (
        JSON.stringify(safeValues) !== JSON.stringify(lastSaved) &&
        form.formState.isValid
      ) {
        const handler = setTimeout(() => {
          onUpdate(safeValues);
          setLastSaved(safeValues);
        }, 600);
        return () => clearTimeout(handler);
      }
    });
    return () => subscription.unsubscribe();
  }, [form, onUpdate, lastSaved]);

  return (
    <FormProvider {...form}>
      <form className="space-y-6 py-2 max-w-2xl">
        {error && (
          <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-400">{error}</div>
        )}
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Book Title *</FormLabel>
              <FormControl>
                <Input {...field} maxLength={100} className="text-gray-100 placeholder:text-gray-300" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="subtitle"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Subtitle</FormLabel>
              <FormControl>
                <Input {...field} maxLength={200} className="text-gray-100 placeholder:text-gray-300" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea {...field} maxLength={1000} className="text-gray-100 placeholder:text-gray-300" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="genre"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Genre</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger className="text-gray-100 placeholder:text-gray-300 bg-gray-800 border-gray-700 min-w-[12rem]">
                      <SelectValue placeholder="Select genre" className="text-gray-300" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {genreOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="target_audience"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Target Audience</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger className="text-gray-100 placeholder:text-gray-300 bg-gray-800 border-gray-700 min-w-[12rem]">
                      <SelectValue placeholder="Select target audience" className="text-gray-300" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {targetAudienceOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField
          control={form.control}
          name="cover_image_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Cover Image URL</FormLabel>
              <FormControl>
                <Input {...field} maxLength={300} className="text-gray-100 placeholder:text-gray-300" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {isSaving && <div className="text-gray-400">Saving...</div>}
      </form>
    </FormProvider>
  );
};
