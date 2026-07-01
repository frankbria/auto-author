'use client';

import Image from 'next/image';
import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import useOptimizedClerkImage from '@/hooks/useOptimizedClerkImage';
import { toast } from '@/lib/toast';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB — matches backend

interface ProfilePictureUploadProps {
  currentAvatarUrl: string | null;
  onUploaded: (url: string) => void;
}

/**
 * Avatar display + upload. Posts multipart form-data to POST /users/me/avatar
 * (raw fetch so the browser sets the multipart boundary; cookie-authenticated).
 */
export function ProfilePictureUpload({ currentAvatarUrl, onUploaded }: ProfilePictureUploadProps) {
  const { getOptimizedImageUrl } = useOptimizedClerkImage();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const src = currentAvatarUrl ? getOptimizedImageUrl(currentAvatarUrl, 200) : '';

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!ALLOWED_TYPES.includes(file.type)) {
      toast.error({ title: 'Invalid file', description: 'Use JPEG, PNG, WebP, or GIF.' });
      return;
    }
    if (file.size > MAX_SIZE) {
      toast.error({ title: 'File too large', description: 'Maximum size is 5MB.' });
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE_URL}/users/me/avatar`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Upload failed');
      }
      const data = await res.json();
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
      {src ? (
        <Image
          src={src}
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
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={handleFile}
        data-testid="avatar-input"
        aria-label="Upload profile picture"
      />
      <Button
        type="button"
        variant="outline"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
      >
        {uploading ? 'Uploading…' : 'Change photo'}
      </Button>
    </div>
  );
}

export default ProfilePictureUpload;
