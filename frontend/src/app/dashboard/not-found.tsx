/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="container mx-auto p-6 flex flex-col items-center justify-center min-h-[70vh]">
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold text-indigo-500">404</h1>
        <h2 className="text-2xl font-semibold text-zinc-200">Page Not Found</h2>
        <p className="text-zinc-400 max-w-md mx-auto">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link 
          href="/dashboard"
          className="inline-block px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md transition"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
