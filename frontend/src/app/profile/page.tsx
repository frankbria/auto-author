'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useSession } from '@/lib/auth-client';
import useProfileApi from '@/hooks/useProfileApi';
import { FormField } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { toast } from '@/lib/toast';
import ProfilePictureUpload from '@/components/profile/ProfilePictureUpload';

const BIO_MAX = 1000;

const profileSchema = z.object({
  firstName: z.string().min(1, 'First name is required').max(50, 'Max 50 characters'),
  lastName: z.string().min(1, 'Last name is required').max(50, 'Max 50 characters'),
  bio: z.string().max(BIO_MAX, `Max ${BIO_MAX} characters`).optional(),
  theme: z.enum(['light', 'dark', 'system']),
  emailNotifications: z.boolean(),
  marketingEmails: z.boolean(),
});

type ProfileFormValues = z.infer<typeof profileSchema>;

export default function UserProfile() {
  const router = useRouter();
  const { data: session } = useSession();
  const user = session?.user;
  const { getUserProfile, updateUserProfile, deleteUserAccount } = useProfileApi();

  const [avatarUrl, setAvatarUrl] = useState<string | null>(user?.image ?? null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      firstName: '',
      lastName: '',
      bio: '',
      theme: 'system',
      emailNotifications: true,
      marketingEmails: false,
    },
  });

  // Seed from the session immediately, then hydrate full profile (bio, prefs)
  // from the backend when available. getUserProfile can be absent in tests.
  useEffect(() => {
    const [firstName = '', ...rest] = (user?.name ?? '').trim().split(' ');
    const lastName = rest.join(' ');
    form.reset({
      firstName,
      lastName,
      bio: '',
      theme: 'system',
      emailNotifications: true,
      marketingEmails: false,
    });
    if (user?.image) setAvatarUrl(user.image);

    if (getUserProfile) {
      getUserProfile()
        .then((p) => {
          form.reset({
            firstName: p.first_name ?? firstName,
            lastName: p.last_name ?? lastName,
            bio: p.bio ?? '',
            theme: p.preferences?.theme ?? 'system',
            emailNotifications: p.preferences?.email_notifications ?? true,
            marketingEmails: p.preferences?.marketing_emails ?? false,
          });
          if (p.avatar_url) setAvatarUrl(p.avatar_url);
        })
        .catch(() => {
          /* keep session-seeded defaults */
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  const onSubmit = async (values: ProfileFormValues) => {
    try {
      await updateUserProfile({
        first_name: values.firstName,
        last_name: values.lastName,
        bio: values.bio,
        preferences: {
          theme: values.theme,
          email_notifications: values.emailNotifications,
          marketing_emails: values.marketingEmails,
        },
      });
      toast.success({ title: 'Profile updated', description: 'Your changes have been saved.' });
    } catch (err) {
      toast.error({
        title: 'Update failed',
        description: err instanceof Error ? err.message : 'Could not save your profile.',
      });
    }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    try {
      await deleteUserAccount();
      toast.success({ title: 'Account deleted' });
      router?.push?.('/');
    } catch (err) {
      toast.error({
        title: 'Delete failed',
        description: err instanceof Error ? err.message : 'Could not delete your account.',
      });
    } finally {
      setDeleting(false);
      setDeleteOpen(false);
    }
  };

  // Read validation errors off the live control state. This works with both the
  // real react-hook-form Control and the mocked form used in unit tests.
  const controlState = (
    form.control as unknown as { _formState?: { errors?: Record<string, { message?: string }> } }
  )?._formState;
  const errors = controlState?.errors ?? {};
  const bioValue = (form.watch('bio') as string) ?? '';

  return (
    <div className="container mx-auto max-w-2xl py-8">
      <h1 className="mb-8 text-3xl font-bold">Profile</h1>

      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-8">
        {/* Avatar */}
        <section className="space-y-2">
          <Label>Profile picture</Label>
          <ProfilePictureUpload currentAvatarUrl={avatarUrl} onUploaded={setAvatarUrl} />
        </section>

        {/* Basic info */}
        <section className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" value={user?.email ?? ''} disabled readOnly />
          </div>

          <FormField
            control={form.control}
            name="firstName"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="firstName">First name</Label>
                <Input id="firstName" {...field} />
                {errors.firstName?.message && (
                  <p role="alert" className="text-destructive text-sm">
                    {String(errors.firstName.message)}
                  </p>
                )}
              </div>
            )}
          />

          <FormField
            control={form.control}
            name="lastName"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="lastName">Last name</Label>
                <Input id="lastName" {...field} />
                {errors.lastName?.message && (
                  <p role="alert" className="text-destructive text-sm">
                    {String(errors.lastName.message)}
                  </p>
                )}
              </div>
            )}
          />

          <FormField
            control={form.control}
            name="bio"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="bio">Bio</Label>
                <textarea
                  id="bio"
                  className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="Tell readers about yourself. Markdown is supported."
                  {...field}
                />
                <p className="text-muted-foreground text-right text-xs">
                  {bioValue.length}/{BIO_MAX}
                </p>
              </div>
            )}
          />
        </section>

        {/* Preferences */}
        <section className="space-y-4">
          <h2 className="text-lg font-semibold">Preferences</h2>

          <FormField
            control={form.control}
            name="theme"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="theme">Theme</Label>
                <select
                  id="theme"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={field.value}
                  onChange={field.onChange}
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
              </div>
            )}
          />

          <FormField
            control={form.control}
            name="emailNotifications"
            render={({ field }) => (
              <div className="flex items-center justify-between">
                <Label htmlFor="emailNotifications">Email notifications</Label>
                <Switch
                  id="emailNotifications"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </div>
            )}
          />

          <FormField
            control={form.control}
            name="marketingEmails"
            render={({ field }) => (
              <div className="flex items-center justify-between">
                <Label htmlFor="marketingEmails">Marketing emails</Label>
                <Switch
                  id="marketingEmails"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </div>
            )}
          />
        </section>

        <div className="flex items-center justify-between">
          <Button type="button" variant="destructive" onClick={() => setDeleteOpen(true)}>
            Delete Account
          </Button>
          <Button type="submit">Save Changes</Button>
        </div>
      </form>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete account</DialogTitle>
            <DialogDescription>
              This permanently deletes your account and all your books. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteAccount}
              disabled={deleting}
            >
              {deleting ? 'Deleting…' : 'Delete account'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
