'use client';

import TocGenerationWizard from '@/components/toc/TocGenerationWizard';

interface GenerateTOCPageProps {
  params: {
    bookId: string;
  };
}

export default function GenerateTOCPage({ params }: GenerateTOCPageProps) {
  return <TocGenerationWizard bookId={params.bookId} />;
}
