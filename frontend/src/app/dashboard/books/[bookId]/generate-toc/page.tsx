'use client';

import { use } from 'react';
import TocGenerationWizard from '@/components/toc/TocGenerationWizard';

interface GenerateTOCPageProps {
  params: Promise<{
    bookId: string;
  }>;
}

export default function GenerateTOCPage({ params }: GenerateTOCPageProps) {
  const { bookId } = use(params);
  return <TocGenerationWizard bookId={bookId} />;
}
