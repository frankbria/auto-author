'use client';

import { toast as sonnerToast } from 'sonner';

export interface ToastOptions {
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive' | 'success';
  duration?: number;
}

export interface Toast extends ToastOptions {
  id: string | number;
}

export function useToast() {
  const toast = (options: ToastOptions) => {
    const { title, description, variant = 'default', duration } = options;
    
    const message = title || description || '';
    const descriptionText = title && description ? description : undefined;
    
    switch (variant) {
      case 'destructive':
        return sonnerToast.error(message, {
          description: descriptionText,
          duration,
        });
      case 'success':
        return sonnerToast.success(message, {
          description: descriptionText,
          duration,
        });
      default:
        return sonnerToast(message, {
          description: descriptionText,
          duration,
        });
    }
  };

  return {
    toast,
    dismiss: sonnerToast.dismiss,
  };
}

// Re-export for convenience
export { toast } from 'sonner';