'use client';

export default function Loading() {
  return (
    <div className="container mx-auto p-6 flex flex-col items-center justify-center min-h-[70vh]">
      <div className="flex flex-col items-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
        <h2 className="text-xl font-medium text-gray-300">Loading your dashboard...</h2>
      </div>
    </div>
  );
}
