'use client';

import Image from 'next/image';
import { useId, useRef, useState } from 'react';
import { HugeiconsIcon } from '@hugeicons/react';
import { ImageUpload01Icon } from '@hugeicons/core-free-icons';
import { Button } from '@/components/ui/button';
import { toast } from '@/lib/toast';
import { IMAGE_ACCEPT, imageFileProblem, uploadImage, uploadUrl } from '@/lib/api/imageUpload';

export interface CoverUrls {
  cover_image_url: string;
  cover_thumbnail_url: string;
}

interface BookCoverUploadProps {
  bookId: string;
  coverUrl: string | undefined;
  onUploaded: (urls: CoverUrls) => void;
}

/**
 * Book cover display + upload (#941), modelled on ProfilePictureUpload. Posts
 * to POST /books/{id}/cover-image; the server writes the URLs (#797).
 */
export function BookCoverUpload({ bookId, coverUrl, onUploaded }: BookCoverUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const hintId = useId();
  const [uploading, setUploading] = useState(false);
  const coverSrc = uploadUrl(coverUrl);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const problem = imageFileProblem(file);
    if (problem) {
      toast.error(problem);
      e.target.value = ''; // so re-picking the same file fires change again
      return;
    }

    setUploading(true);
    try {
      const data = await uploadImage<CoverUrls>(`/books/${bookId}/cover-image`, file);
      onUploaded({ cover_image_url: data.cover_image_url, cover_thumbnail_url: data.cover_thumbnail_url });
      toast.success({ title: 'Cover updated' });
    } catch (err) {
      toast.error({
        title: 'Cover upload failed',
        description: err instanceof Error ? err.message : 'Please try again.',
      });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div data-slot="book-cover-upload" className="mb-4 flex items-end gap-4">
      {coverSrc ? (
        <Image
          src={coverSrc}
          alt="Book cover"
          width={128}
          height={192}
          unoptimized
          className="h-48 w-32 rounded border border-border object-cover shadow-sm"
        />
      ) : (
        <div className="h-48 w-32 rounded border border-dashed border-border bg-muted" aria-hidden="true" />
      )}
      <div>
        <input
          ref={inputRef}
          type="file"
          accept={IMAGE_ACCEPT}
          className="hidden"
          onChange={handleFile}
          aria-label="Upload book cover"
        />
        <Button
          type="button"
          variant="outline"
          // Not `disabled`: that would drop keyboard focus to the page body mid-upload.
          onClick={() => !uploading && inputRef.current?.click()}
          disabled={false}
          aria-disabled={uploading || undefined}
          busy={uploading}
          aria-describedby={hintId}
        >
          <HugeiconsIcon icon={ImageUpload01Icon} size={16} aria-hidden="true" />
          {uploading ? 'Uploading…' : coverSrc ? 'Change cover' : 'Upload cover'}
        </Button>
        <p id={hintId} className="mt-1 text-xs text-muted-foreground">
          JPEG, PNG, WebP or GIF, up to 5MB.
        </p>
      </div>
    </div>
  );
}

export default BookCoverUpload;
