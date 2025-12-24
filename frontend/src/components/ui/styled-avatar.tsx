'use client';

import React from 'react';
import Image from 'next/image';
import useOptimizedClerkImage from '@/hooks/useOptimizedClerkImage';
import { cn } from '@/lib/utils';

interface StyledAvatarProps {
  imageUrl: string;
  firstName?: string | null;
  lastName?: string | null;
  fullName?: string | null;
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap = {
  sm: {
    container: 'w-16 h-16',
    pixels: 64,
    fontSize: 'text-base',
  },
  md: {
    container: 'w-24 h-24',
    pixels: 96,
    fontSize: 'text-xl',
  },
  lg: {
    container: 'w-32 h-32',
    pixels: 128,
    fontSize: 'text-2xl',
  },
};

export function StyledAvatar({
  imageUrl,
  firstName,
  lastName,
  fullName,
  size = 'md',
}: StyledAvatarProps) {
  const { getOptimizedImageUrl } = useOptimizedClerkImage();
  const { container, pixels, fontSize } = sizeMap[size];

  return (
    <div
      data-slot="avatar"
      className={cn(
        'styled-avatar rounded-full border-2 border-primary overflow-hidden flex-shrink-0 transition-all',
        container
      )}
    >
      {imageUrl ? (
        <Image
          src={getOptimizedImageUrl(imageUrl, pixels)}
          alt={fullName || "User"}
          width={pixels}
          height={pixels}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className={cn(
          'flex w-full h-full items-center justify-center bg-gray-800 text-gray-100',
          fontSize
        )}>
          {firstName?.[0]}{lastName?.[0]}
        </div>
      )}
    </div>
  );
}

export default StyledAvatar;
