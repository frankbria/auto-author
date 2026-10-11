export interface Subprocessor {
  name: string;
  purpose: string;
  data: string;
  /** The credentials that switch this integration on; swept by subprocessors.test.ts. */
  envKeys: readonly string[];
}

/**
 * Every third party the Service sends personal data to (#788), rendered as the
 * table in the Privacy Policy. Email and file storage each list both supported
 * providers: which one runs is a deploy-time setting, and the policy must be
 * true under either.
 */
export const SUBPROCESSORS: readonly Subprocessor[] = [
  {
    name: 'OpenAI',
    purpose: 'Generating tables of contents, interview questions, chapter drafts and text enhancements',
    data: 'The book details, answers and chapter text you submit to an AI feature',
    envKeys: ['OPENAI_API_KEY', 'OPENAI_AUTOAUTHOR_API_KEY', 'AI_API_KEY'],
  },
  {
    name: 'Stripe',
    purpose: 'Taking payments and managing subscriptions',
    data: 'Your email address, billing address, any tax ID you provide, and the card details you enter on Stripe’s own checkout page',
    envKeys: ['STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET'],
  },
  {
    name: 'MongoDB Atlas',
    purpose: 'Hosting our database',
    data: 'Your account details and everything you create in the Service',
    envKeys: ['MONGODB_URI'],
  },
  {
    name: 'Sentry',
    purpose: 'Error monitoring and diagnostics',
    data: 'Technical details of a failed request, which can include your IP address, browser type and fragments of the content being processed when the error occurred',
    envKeys: ['SENTRY_DSN', 'NEXT_PUBLIC_SENTRY_DSN'],
  },
  {
    name: 'Resend',
    purpose: 'Sending account email, such as password-reset messages',
    data: 'Your name, email address and the content of the message',
    envKeys: ['EMAIL_SERVICE_API_KEY'],
  },
  {
    name: 'SendGrid (Twilio)',
    purpose: 'Sending account email, as an alternative to Resend',
    data: 'Your name, email address and the content of the message',
    envKeys: ['EMAIL_SERVICE_API_KEY'],
  },
  {
    name: 'Amazon Web Services (S3)',
    purpose: 'Storing files you upload',
    data: 'Images you upload, such as book covers and profile pictures',
    envKeys: ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'],
  },
  {
    name: 'Cloudinary',
    purpose: 'Storing files you upload, as an alternative to Amazon S3',
    data: 'Images you upload, such as book covers and profile pictures',
    envKeys: ['CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET'],
  },
  {
    name: 'Your browser’s speech service (for example Google in Chrome, Apple in Safari)',
    purpose: 'Turning speech into text when you use voice input',
    data: 'The audio you dictate, sent by your browser directly to its vendor rather than to us',
    envKeys: [],
  },
];
