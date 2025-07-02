import * as z from 'zod';
import { sanitizeText, sanitizeUrl } from '../security';

export const bookCreationSchema = z.object({
  title: z
    .string()
    .transform(sanitizeText)
    .refine(val => val.length > 0, { message: 'Title is required' })
    .refine(val => val.length <= 100, { message: 'Title must be 100 characters or less' }),
  subtitle: z
    .string()
    .transform(sanitizeText)
    .refine(val => val.length <= 200, { message: 'Subtitle must be 200 characters or less' })
    .optional()
    .or(z.literal('')),
  description: z
    .string()
    .transform(sanitizeText)
    .refine(val => val.length <= 1000, { message: 'Description must be 1000 characters or less' })
    .optional()
    .or(z.literal('')),
  genre: z
    .string()
    .transform(sanitizeText)
    .refine(val => val.length <= 50, { message: 'Genre must be 50 characters or less' })
    .optional()
    .or(z.literal('')),
  target_audience: z
    .string()
    .transform(sanitizeText)
    .refine(val => val.length <= 100, { message: 'Target audience must be 100 characters or less' })
    .optional()
    .or(z.literal('')),
  cover_image_url: z
    .string()
    .transform(sanitizeUrl)
    .refine(val => val === '' || val.startsWith('http'), { message: 'Cover image must be a valid URL' })
    .optional()
    .or(z.literal('')),
});

export type BookFormData = z.infer<typeof bookCreationSchema>;
