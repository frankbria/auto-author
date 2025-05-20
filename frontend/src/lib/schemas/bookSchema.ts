import * as z from 'zod';

export const bookCreationSchema = z.object({
  title: z
    .string()
    .min(1, { message: 'Title is required' })
    .max(100, { message: 'Title must be 100 characters or less' }),
  subtitle: z
    .string()
    .max(200, { message: 'Subtitle must be 200 characters or less' })
    .optional()
    .or(z.literal('')),
  description: z
    .string()
    .max(1000, { message: 'Description must be 1000 characters or less' })
    .optional()
    .or(z.literal('')),
  genre: z
    .string()
    .max(50, { message: 'Genre must be 50 characters or less' })
    .optional()
    .or(z.literal('')),
  target_audience: z
    .string()
    .max(100, { message: 'Target audience must be 100 characters or less' })
    .optional()
    .or(z.literal('')),
  cover_image_url: z
    .string()
    .url({ message: 'Cover image must be a valid URL' })
    .optional()
    .or(z.literal('')),
});

export type BookFormData = z.infer<typeof bookCreationSchema>;
