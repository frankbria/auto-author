'use client';

import Image from 'next/image';
import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { toast } from '@/lib/toast';
import { IMAGE_ACCEPT, imageFileProblem, uploadImage, uploadUrl } from '@/lib/api/imageUpload';

interface ProfilePictureUploadProps {
  currentAvatarUrl: string | null;
  onUploaded: (url: string) => void;
}

/**
 * Avatar display + upload. Posts multipart form-data to POST /users/me/avatar
 * (raw fetch so the browser sets the multipart boundary; cookie-authenticated).
 */
export function ProfilePictureUpload({ currentAvatarUrl, onUploaded }: ProfilePictureUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const avatarSrc = uploadUrl(currentAvatarUrl);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const problem = imageFileProblem(file);
    if (problem) {
      toast.error(problem);
      return;
    }

    setUploading(true);
    try {
      const data = await uploadImage<{ avatar_url: string }>('/users/me/avatar', file);
      onUploaded(data.avatar_url);
      toast.success({ title: 'Profile picture updated' });
    } catch (err) {
      toast.error({
        title: 'Upload failed',
        description: err instanceof Error ? err.message : 'Please try again.',
      });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div className="flex items-center gap-4">
      {avatarSrc ? (
        <Image
          src={avatarSrc}
          alt="Profile picture"
          width={80}
          height={80}
          unoptimized
          className="h-20 w-20 rounded-full object-cover"
        />
      ) : (
        <div className="h-20 w-20 rounded-full bg-muted" aria-hidden="true" />
      )}
      <input
        ref={inputRef}
        type="file"
        accept={IMAGE_ACCEPT}
        className="hidden"
        onChange={handleFile}
        data-testid="avatar-input"
        aria-label="Upload profile picture"
      />
      <Button
        type="button"
        variant="outline"
        onClick={() => inputRef.current?.click()}
        disabled={uploading} busy={uploading}
      >
        {uploading ? 'Uploading…' : 'Change photo'}
      </Button>
    </div>
  );
}

export default ProfilePictureUpload;
