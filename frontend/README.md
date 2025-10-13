# Auto-Author Frontend

Modern Next.js application for AI-powered book authoring with comprehensive production-ready features.

## 🚀 Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: TailwindCSS
- **UI Components**: Radix UI primitives
- **Rich Text Editor**: TipTap
- **Authentication**: Clerk
- **State Management**: React Context + hooks
- **API Client**: Custom fetch wrapper with retry logic
- **Testing**: Jest + React Testing Library + Playwright
- **Code Quality**: ESLint + Prettier
- **Performance**: web-vitals monitoring

## 📦 Key Features

### Core Functionality
- ✅ Book creation and management (CRUD)
- ✅ AI-powered Table of Contents generation
- ✅ Rich text chapter editing with TipTap
- ✅ Q&A-based content development
- ✅ AI draft generation from responses
- ✅ Export to PDF/DOCX
- ✅ Voice input via Web Speech API

### Production Features
- ✅ Auto-save with 3-second debounce
- ✅ localStorage backup on network failure
- ✅ Save status indicators
- ✅ Unified error handling with retry logic
- ✅ Type-to-confirm book deletion
- ✅ Loading states with progress indicators
- ✅ Performance monitoring (Core Web Vitals)
- ✅ Data preservation and recovery
- ✅ Responsive design (320px - desktop)
- ✅ Keyboard accessibility (WCAG 2.1 AA)
- ✅ Touch target compliance (WCAG 2.1 AAA)

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js 15 App Router
│   │   ├── (auth)/            # Authentication routes
│   │   ├── dashboard/         # Main application
│   │   └── layout.tsx         # Root layout with providers
│   ├── components/            # React components
│   │   ├── books/             # Book management
│   │   ├── chapters/          # Chapter editing
│   │   ├── errors/            # Error notifications
│   │   ├── export/            # Export functionality
│   │   ├── loading/           # Loading states
│   │   ├── recovery/          # Data recovery
│   │   ├── toc/               # Table of contents
│   │   └── ui/                # Reusable UI primitives
│   ├── lib/                   # Utilities and services
│   │   ├── api/               # API client
│   │   ├── errors/            # Error handling
│   │   ├── performance/       # Performance monitoring
│   │   ├── storage/           # Data persistence
│   │   └── testing/           # Testing utilities
│   ├── types/                 # TypeScript definitions
│   │   ├── api.ts            # Base API types
│   │   └── book.ts           # Book domain types
│   ├── hooks/                 # Custom React hooks
│   └── styles/                # Global styles
├── docs/                      # Frontend documentation
├── claudedocs/                # Technical analysis reports
├── e2e/                       # Playwright E2E tests
└── public/                    # Static assets
```

## 🛠️ Development Setup

### Prerequisites
- Node.js ≥18
- npm or yarn
- Backend API running on localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local

# Configure .env.local:
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_****
CLERK_SECRET_KEY=sk_****
```

### Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run tests
npm test
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Type checking
npm run typecheck

# Linting
npm run lint
npm run lint:fix

# Format code
npm run format
```

## 🧪 Testing

### Test Coverage Standards
- **Overall**: 86.2% (exceeds 85% requirement)
- **Critical Components**: 100% pass rate required
- **Test Types**:
  - Unit tests (Jest + RTL)
  - Integration tests
  - E2E tests (Playwright)
  - Accessibility tests (@axe-core/react)

### Running Tests

```bash
# All tests
npm test

# Watch mode
npm test -- --watch

# Coverage report
npm run test:coverage

# E2E tests
npm run test:e2e

# E2E with UI
npm run test:e2e:ui
```

## 📊 Code Quality

### TypeScript Configuration
- Strict mode enabled
- Path aliases configured (@/)
- Incremental builds
- Source maps for debugging

### ESLint Rules
- Next.js recommended
- React hooks validation
- TypeScript integration
- Accessibility checks (eslint-plugin-jsx-a11y)

### Performance Budgets
Operation budgets defined for:
- TOC generation: 3000ms
- Export operations: 5000ms
- Draft generation: 4000ms
- Auto-save: 1000ms
- Manual save: 2000ms

## 🎨 UI Component Library

### Base Components (Radix UI)
- Button, Dialog, Dropdown Menu
- Alert, Toast, Modal
- Tabs, Accordion, Popover
- Form inputs with validation

### Custom Components
- **LoadingStateManager**: Progress indicators with time estimates
- **ErrorNotification**: Unified error display with retry
- **DeleteBookModal**: Type-to-confirm deletion
- **DataRecoveryModal**: Recover unsaved changes
- **ChapterEditor**: Rich text editing with TipTap
- **TocGenerationWizard**: AI-powered TOC creation

## 🔍 Performance Monitoring

### Core Web Vitals
- **LCP** (Largest Contentful Paint): <2.5s
- **FID** (First Input Delay): <100ms
- **INP** (Interaction to Next Paint): <200ms
- **CLS** (Cumulative Layout Shift): <0.1
- **TTFB** (Time to First Byte): <800ms
- **FCP** (First Contentful Paint): <1.8s

### Custom Metrics
- Operation timing tracking
- Budget validation with warnings
- localStorage caching for offline scenarios

### Usage

```typescript
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';

const { trackOperation } = usePerformanceTracking();

const result = await trackOperation(
  'toc-generation',
  async () => await generateToc(summary),
  { summaryLength: summary.length }
);
```

## ♿ Accessibility

### WCAG Compliance
- **Current**: WCAG 2.1 Level AA compliant
- **Touch Targets**: Level AAA (44x44px minimum)
- **Keyboard Navigation**: Full support
- **Screen Readers**: ARIA labels and semantics
- **Focus Management**: Visible indicators, modal traps

### Testing Tools
- @axe-core/react for automated testing
- axe DevTools browser extension
- Lighthouse accessibility audits
- Manual keyboard navigation testing
- Screen reader testing (NVDA, VoiceOver)

### Accessibility Features
- All interactive elements keyboard accessible
- Skip navigation links
- ARIA live regions for dynamic content
- Semantic HTML structure
- Proper heading hierarchy
- Form label associations

## 🔐 Authentication

### Clerk Integration
- Social login (Google, GitHub)
- Email/password authentication
- Multi-factor authentication
- Session management
- Profile management

### Protected Routes
All dashboard routes require authentication. Unauthenticated users are redirected to sign-in.

## 📡 API Integration

### API Client
- Type-safe wrapper around fetch
- Automatic retry logic for transient errors
- Error classification and handling
- Correlation ID tracking
- Request/response logging

### API Types
- **Base Types**: `ApiResponse<T>`, `ApiError`
- **Book Types**: Complete domain model (11 interfaces, 5 enums)
- **Type Guards**: Runtime validation functions
- **Helper Functions**: Business logic utilities

### Error Handling
- Transient errors: Automatic retry (network, timeout)
- Permanent errors: User notification with guidance
- System errors: Error boundary with recovery options

## 📱 Responsive Design

### Breakpoints (TailwindCSS)
- **Mobile**: 320px - 639px (sm)
- **Tablet**: 640px - 1023px (md)
- **Desktop**: 1024px+ (lg, xl, 2xl)

### Mobile Optimizations
- Touch-friendly targets (44x44px)
- Mobile-first CSS approach
- Responsive typography
- Optimized images and assets
- No horizontal scroll on any viewport

## 🚀 Deployment

### Build Process
```bash
# Production build
npm run build

# Verify build
npm run start
```

### Environment Variables (Production)
```
NEXT_PUBLIC_API_URL=https://api.auto-author.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_****
CLERK_SECRET_KEY=sk_****
```

### Deployment Checklist
- [ ] Environment variables configured
- [ ] Build succeeds without errors
- [ ] Type checking passes
- [ ] ESLint passes
- [ ] Tests pass (≥85% coverage)
- [ ] Lighthouse score ≥90
- [ ] Accessibility audit passes
- [ ] Performance budgets met

## 📚 Documentation

### Component Documentation
- JSDoc comments for all public APIs
- Usage examples in component files
- Storybook stories (planned)

### API Documentation
- Complete JSDoc for bookClient methods
- Error scenario documentation
- Request/response examples

### Guides
- [Accessibility Testing Guide](docs/accessibility_testing_guide.md)
- [API Client Documentation](docs/api_client_documentation.md)
- [Component Testing Guide](docs/component_testing_guide.md)

## 🔧 Troubleshooting

### Common Issues

**Build Errors**
```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

**Type Errors**
```bash
# Regenerate TypeScript declarations
npm run typecheck
```

**Test Failures**
```bash
# Clear Jest cache
npm test -- --clearCache
```

## 🤝 Contributing

### Code Standards
- Follow existing patterns and conventions
- Write tests for all new features
- Ensure TypeScript strict mode compliance
- Add JSDoc comments for public APIs
- Maintain ≥85% test coverage

### Pull Request Process
1. Create feature branch from `main`
2. Write code with tests
3. Run quality checks (`npm run typecheck && npm run lint && npm test`)
4. Update documentation
5. Submit PR with clear description
6. Address review feedback

## 📄 License

MIT License © 2025 Auto-Author Team
