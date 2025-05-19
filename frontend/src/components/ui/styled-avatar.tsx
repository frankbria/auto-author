'use client';

import React from 'react';
import Image from 'next/image';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import useOptimizedClerkImage from '@/hooks/useOptimizedClerkImage';

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
  },
  md: {
    container: 'w-24 h-24',
    pixels: 96,
  },
  lg: {
    container: 'w-32 h-32',
    pixels: 128,
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
  const { container, pixels } = sizeMap[size];

  const containerStyles = {
    width: `${pixels}px`,
    height: `${pixels}px`,
    borderRadius: '9999px',
    borderWidth: '2px',
    borderColor: 'rgb(99, 102, 241)',
    overflow: 'hidden',
    position: 'relative',
    flexShrink: 0,
    display: 'flex',
  } as React.CSSProperties;

  const imageStyles = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  } as React.CSSProperties;

  return (
    <div style={containerStyles} className={`styled-avatar ${container} rounded-full border-2 border-indigo-500`}>
        <Image
          src={getOptimizedImageUrl(imageUrl, pixels)}
          alt={fullName || "User"}
          width={pixels}
          height={pixels}
          style={imageStyles}
        />
      ) : (
        <div style={{
          display: 'flex',
          width: '100%',
          height: '100%',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgb(39, 39, 42)',
          color: 'rgb(228, 228, 231)',
          fontSize: size === 'lg' ? '1.5rem' : size === 'md' ? '1.25rem' : '1rem',
        }}>
          {firstName?.[0]}{lastName?.[0]}
        </div>
    </div>
  );
}

export default StyledAvatar;
