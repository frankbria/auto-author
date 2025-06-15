export default function HelpPage() {
  return (
    <div className="container max-w-4xl py-8">
      <h1 className="text-3xl font-bold mb-6">Help & Support</h1>
      
      <div className="space-y-6">
        <section>
          <h2 className="text-2xl font-semibold mb-3">Getting Started</h2>
          <p className="text-muted-foreground">
            Welcome to Auto Author! This AI-assisted book writing platform helps you create
            compelling content through guided interviews and intelligent draft generation.
          </p>
        </section>
        
        <section>
          <h2 className="text-2xl font-semibold mb-3">Key Features</h2>
          <ul className="list-disc list-inside space-y-2 text-muted-foreground">
            <li>Create and manage multiple books</li>
            <li>Generate table of contents with AI assistance</li>
            <li>Write chapters with a rich text editor</li>
            <li>Generate AI drafts from interview questions</li>
            <li>Track your writing progress</li>
          </ul>
        </section>
        
        <section>
          <h2 className="text-2xl font-semibold mb-3">How to Use AI Draft Generation</h2>
          <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
            <li>Open a chapter in the editor</li>
            <li>Click the &quot;Generate AI Draft&quot; button in the toolbar</li>
            <li>Answer the interview questions about your chapter</li>
            <li>Select your preferred writing style and target length</li>
            <li>Click &quot;Generate Draft&quot; and wait for the AI to create content</li>
            <li>Review and edit the generated draft before using it</li>
          </ol>
        </section>
        
        <section>
          <h2 className="text-2xl font-semibold mb-3">Need More Help?</h2>
          <p className="text-muted-foreground">
            If you need additional assistance, please contact our support team at support@autoauthor.com
          </p>
        </section>
      </div>
    </div>
  );
}