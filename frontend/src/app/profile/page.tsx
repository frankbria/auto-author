'use client';

import { useState, useEffect } from 'react';
import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

export default function UserProfile() {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const [isEditing, setIsEditing] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [bio, setBio] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  // Load user data when component mounts
  useEffect(() => {
    if (isLoaded && user) {
      setFullName(user.fullName || '');
      setEmail(user.primaryEmailAddress?.emailAddress || '');
      // Bio would come from your custom backend
      setBio('');
    } else if (isLoaded && !user) {
      // Redirect to login if not logged in
      router.push('/sign-in');
    }
  }, [isLoaded, user, router]);

  if (!isLoaded || !user) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      // Update name in Clerk
      await user.update({
        firstName: fullName.split(' ')[0],
        lastName: fullName.split(' ').slice(1).join(' ')
      });
      
      // Email changes would require verification through Clerk
      // Bio would be saved to your custom backend
      
      setMessage({ type: 'success', text: 'Profile updated successfully!' });
      setIsEditing(false);
    } catch (error) {
      console.error('Error updating profile:', error);
      setMessage({ type: 'error', text: 'Failed to update profile. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <h1 className="text-3xl font-bold text-zinc-100 mb-8">Your Profile</h1>
      
      {message.text && (
        <div className={`p-4 mb-6 rounded-lg ${message.type === 'success' ? 'bg-green-900/20 border border-green-700 text-green-400' : 'bg-red-900/20 border border-red-700 text-red-400'}`}>
          {message.text}
        </div>
      )}
      
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold text-zinc-100">Personal Information</h2>
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md"
          >
            {isEditing ? 'Cancel' : 'Edit Profile'}
          </button>
        </div>
        
        {isEditing ? (
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-zinc-400 mb-2" htmlFor="fullName">Full Name</label>
              <input
                type="text"
                id="fullName"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-2 px-3 text-zinc-100"
                required
              />
            </div>
            
            <div className="mb-4">
              <label className="block text-zinc-400 mb-2" htmlFor="email">Email Address</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-2 px-3 text-zinc-100"
                disabled
              />
              <p className="text-xs text-zinc-500 mt-1">To change your email, visit your account settings.</p>
            </div>
            
            <div className="mb-6">
              <label className="block text-zinc-400 mb-2" htmlFor="bio">Bio</label>
              <textarea
                id="bio"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                rows={4}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-2 px-3 text-zinc-100"
              ></textarea>
            </div>
            
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : 'Save Changes'}
            </button>
          </form>
        ) : (
          <div>
            <div className="mb-4">
              <h3 className="text-zinc-400 text-sm mb-1">Full Name</h3>
              <p className="text-zinc-100">{fullName || 'Not specified'}</p>
            </div>
            
            <div className="mb-4">
              <h3 className="text-zinc-400 text-sm mb-1">Email Address</h3>
              <p className="text-zinc-100">{email}</p>
            </div>
            
            <div className="mb-4">
              <h3 className="text-zinc-400 text-sm mb-1">Bio</h3>
              <p className="text-zinc-100">{bio || 'No bio provided'}</p>
            </div>
          </div>
        )}
      </div>
      
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
        <h2 className="text-2xl font-semibold text-zinc-100 mb-6">Account Settings</h2>
        
        <div className="flex flex-col space-y-4">
          <a 
            href="/user/change-password" 
            className="text-indigo-400 hover:text-indigo-300"
          >
            Change Password
          </a>
          
          <a 
            href="/user/notifications" 
            className="text-indigo-400 hover:text-indigo-300"
          >
            Notification Preferences
          </a>
          
          <button 
            className="text-red-500 hover:text-red-400 text-left"
            onClick={() => {
              if (window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
                // Handle account deletion logic here
              }
            }}
          >
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
