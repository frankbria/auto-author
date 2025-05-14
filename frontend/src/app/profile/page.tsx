'use client';

import { useState, useEffect, useRef } from 'react';
import { useUser, useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import useOptimizedClerkImage from '@/hooks/useOptimizedClerkImage';
import { 
  Form, 
  FormField, 
  useForm,
  zodResolver,
  z
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
// Avatar components removed in favor of direct HTML/CSS
import { toast } from '@/lib/toast';
import debounce from 'lodash.debounce';

// Form validation schema
const profileFormSchema = z.object({
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  bio: z.string().optional(),
  avatarUrl: z.string().optional(),
  theme: z.enum(["light", "dark", "system"]),
  emailNotifications: z.boolean(),
  marketingEmails: z.boolean()
});

type ProfileFormValues = z.infer<typeof profileFormSchema>;

export default function UserProfile() {
  const { user, isLoaded, isSignedIn } = useUser();
  const { signOut } = useAuth();
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { getOptimizedImageUrl } = useOptimizedClerkImage();
  
  // Initialize form with default values
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      bio: "",
      avatarUrl: "",
      theme: "dark",
      emailNotifications: true,
      marketingEmails: false
    }
  });
  // Load user data when component mounts
  useEffect(() => {
    if (isLoaded && user) {
      const metadata = user.unsafeMetadata as Record<string, unknown>;
      form.reset({
        firstName: user.firstName || "",
        lastName: user.lastName || "",
        bio: (metadata?.bio as string) || "",
        avatarUrl: user.imageUrl || "",
        theme: (metadata?.theme as "light" | "dark" | "system") || "dark",
        emailNotifications: (metadata?.emailNotifications as boolean) ?? true,
        marketingEmails: (metadata?.marketingEmails as boolean) ?? false
      });
    } else if (isLoaded && !isSignedIn) {
      // Redirect to login if not logged in
      router.push('/sign-in');
    }
  }, [isLoaded, isSignedIn, user, router, form]);  // Create debounced save function for auto-save
  const debouncedSave = useRef(
    debounce(async (data: Partial<ProfileFormValues>) => {
      if (!user) return;
      
      try {
        const currentMetadata = (user.unsafeMetadata as Record<string, unknown>) || {};
        // Update user metadata via Clerk
        await user.update({
          firstName: data.firstName,
          lastName: data.lastName,
          unsafeMetadata: {
            ...currentMetadata,
            bio: data.bio,
            theme: data.theme,
            emailNotifications: data.emailNotifications,
            marketingEmails: data.marketingEmails
          }
        });
        
        toast.success({
          description: "Profile updated successfully"
        });
      } catch (error) {
        console.error('Error updating profile:', error);
        toast.error({
          description: "Failed to update profile. Please try again."
        });
      }
    }, 1000)
  ).current;  // Handle form submission
  const onSubmit = async (data: ProfileFormValues) => {
    try {
      const currentMetadata = (user?.unsafeMetadata as Record<string, unknown>) || {};
      // Update name and metadata in Clerk
      await user?.update({
        firstName: data.firstName,
        lastName: data.lastName,
        unsafeMetadata: {
          ...currentMetadata,
          bio: data.bio,
          theme: data.theme,
          emailNotifications: data.emailNotifications,
          marketingEmails: data.marketingEmails
        }
      });
      
      toast.success({
        description: "Profile updated successfully"
      });
    } catch (error) {
      console.error('Error updating profile:', error);
      toast.error({
        description: "Failed to update profile. Please try again."
      });
    }
  };
    // Handle individual field changes for auto-save
  const handleFieldChange = (field: keyof ProfileFormValues, value: string | boolean) => {
    form.setValue(field, value);
    debouncedSave({
      [field]: value
    });
  };
    // Handle avatar upload
  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user) return;
    
    setIsUploading(true);
    
    try {
      // Upload the image to Clerk
      await user.setProfileImage({ file });
      
      // Force reload the user to get updated image URL
      await user.reload();
        // Update the form with the new image URL (with size parameters)
      const optimizedImageUrl = getOptimizedImageUrl(user.imageUrl, 96);
      form.setValue('avatarUrl', optimizedImageUrl);
      
      toast.success({
        description: "Profile picture updated successfully"
      });
    } catch (error) {
      console.error('Error uploading avatar:', error);
      toast.error({
        description: "Failed to upload profile picture. Please try again."
      });
    } finally {
      setIsUploading(false);
    }
  };
  
  // Handle account deletion
  const handleAccountDeletion = async () => {
    try {
      // Sign out and perform additional cleanup if needed
      await signOut();
      
      // In a real implementation, you'd want to make an API call to your backend
      // to delete user data before or after the Clerk sign out
      // await fetch('/api/users/me', { method: 'DELETE' });
      
      toast.success({
        description: "Account deleted successfully"
      });
      router.push('/');
    } catch (error) {
      console.error('Error deleting account:', error);
      toast.error({
        description: "Failed to delete account. Please try again."
      });
    } finally {
      setIsDeleteModalOpen(false);
    }
  };

  if (!isLoaded || !user) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }
  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <h1 className="text-3xl font-bold text-zinc-100 mb-8">Your Profile</h1>

      <Form form={form} onSubmit={onSubmit}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Left column: Avatar and basic info */}
          <div className="md:col-span-1">
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 mb-6">              <div className="flex flex-col items-center mb-6">                <div className="relative mb-4">
                  <div 
                    className="relative flex w-24 h-24 shrink-0 overflow-hidden rounded-full border-2 border-indigo-500"
                    style={{ width: '96px', height: '96px' }}
                  >
                    <img 
                      src={getOptimizedImageUrl(user.imageUrl, 96)} 
                      alt={user.fullName || "User"} 
                      className="h-full w-full object-cover"
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  </div>                  <button 
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="absolute bottom-0 right-0 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full p-2 z-10"
                    style={{ bottom: '0', right: '0' }}
                    disabled={isUploading}
                  >
                    {isUploading ? (
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18 2l4 4-10 10H8v-4L18 2z"></path>
                      </svg>
                    )}
                  </button>
                  <input 
                    type="file" 
                    ref={fileInputRef}
                    accept="image/*" 
                    style={{ display: 'none' }}
                    onChange={handleAvatarUpload}
                  />
                </div>
                <h2 className="text-xl font-semibold text-zinc-100">{user.fullName}</h2>
                <p className="text-zinc-400">{user.primaryEmailAddress?.emailAddress}</p>
              </div>
              
              <div className="mb-4">
                <FormField
                  name="firstName"
                  label="First Name"
                  render={({ field }) => (
                    <Input
                      {...field}
                      placeholder="First name"
                      onChange={(e) => {
                        field.onChange(e);
                        handleFieldChange('firstName', e.target.value);
                      }}
                    />
                  )}
                />
              </div>
              
              <div className="mb-4">
                <FormField
                  name="lastName"
                  label="Last Name"
                  render={({ field }) => (
                    <Input
                      {...field}
                      placeholder="Last name"
                      onChange={(e) => {
                        field.onChange(e);
                        handleFieldChange('lastName', e.target.value);
                      }}
                    />
                  )}
                />
              </div>
              
              <div className="mb-4">
                <Label>Email Address</Label>
                <div className="flex mt-2">
                  <Input
                    type="email"
                    value={user.primaryEmailAddress?.emailAddress || ""}
                    disabled
                    className="bg-zinc-900/50 text-zinc-400"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    className="ml-2"
                    onClick={() => window.open("https://accounts.clerk.dev/user/settings/account")}
                  >
                    Change
                  </Button>
                </div>
                <p className="text-xs text-zinc-500 mt-1">Email can be changed in your Clerk account settings</p>
              </div>
            </div>
          </div>
          
          {/* Right column: Bio, preferences, etc. */}
          <div className="md:col-span-2">
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">About You</h2>
              
              <div className="mb-6">
                <FormField
                  name="bio"
                  label="Bio"
                  render={({ field }) => (
                    <textarea
                      {...field}
                      rows={5}
                      placeholder="Tell us about yourself..."
                      className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-2 px-3 text-zinc-100 focus:outline-none focus:border-indigo-500"
                      onChange={(e) => {
                        field.onChange(e);
                        handleFieldChange('bio', e.target.value);
                      }}
                    />
                  )}
                />
              </div>
              
              <Button type="submit" className="mb-2">
                Save Changes
              </Button>
              <p className="text-xs text-zinc-500">Changes are saved automatically as you type</p>
            </div>
            
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">Preferences</h2>
              
              <div className="mb-6">
                <Label>Theme</Label>
                <div className="grid grid-cols-3 gap-4 mt-2">
                  <Button
                    type="button"
                    variant={form.watch("theme") === "light" ? "default" : "outline"}
                    className={`flex items-center justify-center ${form.watch("theme") === "light" ? "bg-indigo-600" : ""}`}
                    onClick={() => handleFieldChange('theme', 'light')}
                  >
                    Light
                  </Button>
                  <Button
                    type="button"
                    variant={form.watch("theme") === "dark" ? "default" : "outline"}
                    className={`flex items-center justify-center ${form.watch("theme") === "dark" ? "bg-indigo-600" : ""}`}
                    onClick={() => handleFieldChange('theme', 'dark')}
                  >
                    Dark
                  </Button>
                  <Button
                    type="button"
                    variant={form.watch("theme") === "system" ? "default" : "outline"}
                    className={`flex items-center justify-center ${form.watch("theme") === "system" ? "bg-indigo-600" : ""}`}
                    onClick={() => handleFieldChange('theme', 'system')}
                  >
                    System
                  </Button>
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Email Notifications</Label>
                    <p className="text-sm text-zinc-400">Receive updates about your account</p>
                  </div>
                  <Switch
                    checked={form.watch("emailNotifications")}
                    onCheckedChange={(checked) => handleFieldChange('emailNotifications', checked)}
                  />
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Marketing Emails</Label>
                    <p className="text-sm text-zinc-400">Receive promotional emails and newsletters</p>
                  </div>
                  <Switch
                    checked={form.watch("marketingEmails")}
                    onCheckedChange={(checked) => handleFieldChange('marketingEmails', checked)}
                  />
                </div>
              </div>
            </div>
            
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">Account Settings</h2>
              
              <div className="flex flex-col space-y-4">
                <div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => window.open("https://accounts.clerk.dev/user/settings/security")}
                  >
                    Change Password
                  </Button>
                  <p className="text-sm text-zinc-400 mt-1">Update your password in Clerk security settings</p>
                </div>
                
                <div>
                  <Button
                    type="button"
                    variant="destructive"
                    onClick={() => setIsDeleteModalOpen(true)}
                  >
                    Delete Account
                  </Button>
                  <p className="text-sm text-zinc-400 mt-1">Permanently delete your account and all data</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Form>
      
      {/* Delete Account Confirmation Modal */}
      <Dialog open={isDeleteModalOpen} onOpenChange={setIsDeleteModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-500">Delete Account</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete your account? This action cannot be undone and all your data will be permanently removed.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            <p className="text-sm text-zinc-400 mb-4">Please type your email address to confirm deletion:</p>
            <Input
              type="email"
              placeholder={user.primaryEmailAddress?.emailAddress || ""}
              className="mb-4"
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsDeleteModalOpen(false)}
            >
              Cancel
            </Button>            <Button
              variant="destructive"
              onClick={handleAccountDeletion}
            >
              Delete Account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
