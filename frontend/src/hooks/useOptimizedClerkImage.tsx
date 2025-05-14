'use client';

/**
 * Hook to optimize Clerk image URLs for use in the application
 * Ensures images are served at the appropriate resolution
 */
export function useOptimizedClerkImage() {
  /**
   * Get an optimized image URL from a Clerk image URL
   * 
   * @param imageUrl - The original Clerk image URL
   * @param width - Desired width in pixels
   * @param height - Desired height in pixels (defaults to same as width)
   * @returns Optimized image URL with size parameters
   */
  const getOptimizedImageUrl = (imageUrl: string, width: number, height: number = width): string => {
    if (!imageUrl) return '';
    
    // Check if the URL already has query parameters
    const hasQueryParams = imageUrl.includes('?');
    
    // Add width and height parameters appropriately
    return hasQueryParams
      ? `${imageUrl}&width=${width}&height=${height}`
      : `${imageUrl}?width=${width}&height=${height}`;
  };

  return { getOptimizedImageUrl };
}

export default useOptimizedClerkImage;
