'use client';

import { Toaster as SonnerToaster } from 'sonner';

export function SonnerProvider() {
  return (
    <SonnerToaster
      position="top-right"
      toastOptions={{
        className: 'dark:bg-zinc-800 dark:text-zinc-100 dark:border-zinc-700',
        duration: 4000,
        style: {
          fontSize: '14px',
        },
      }}
      closeButton
    />
  );
}
