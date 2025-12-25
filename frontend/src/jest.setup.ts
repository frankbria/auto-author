// src/jest.setup.ts
import '@testing-library/jest-dom';

// Add TextEncoder/TextDecoder polyfills for Node.js environment
if (typeof global.TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

// Clear localStorage before each test to prevent JSON parse errors
beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

// Mock window.matchMedia for responsive component tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Add a fetch polyfill for tests
global.fetch = jest.fn().mockImplementation(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    status: 200,
    statusText: 'OK',
    headers: new Headers(),
    clone: function() { return this; }
  })
);

// Mock Speech Recognition API
class MockSpeechRecognition {
  public onresult: ((event: any) => void) | null = null;
  public onerror: ((event: any) => void) | null = null;
  public onend: (() => void) | null = null;
  public onspeechend: (() => void) | null = null;
  public onstart: (() => void) | null = null;
  public continuous = false;
  public interimResults = false;
  public lang = 'en-US';

  start = jest.fn();
  stop = jest.fn();
  abort = jest.fn();
}

// @ts-expect-error - Mocking global Speech Recognition
window.SpeechRecognition = MockSpeechRecognition;
// @ts-expect-error - Mocking global webkit Speech Recognition
window.webkitSpeechRecognition = MockSpeechRecognition;

// Mock Media Devices API
Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: jest.fn().mockResolvedValue({
      getAudioTracks: () => [{
        kind: 'audio',
        id: 'mock-audio-track',
        enabled: true,
        stop: jest.fn(),
      }],
      getTracks: () => [{
        kind: 'audio',
        id: 'mock-audio-track',
        enabled: true,
        stop: jest.fn(),
      }],
    }),
    enumerateDevices: jest.fn().mockResolvedValue([
      { kind: 'audioinput', deviceId: 'default', label: 'Default Microphone' }
    ]),
  },
});

// Ensure DOM is properly set up for React Testing Library
if (typeof document !== 'undefined') {
  // Ensure we have a proper DOM container
  if (!document.body) {
    document.body = document.createElement('body');
  }
}

// Mock web-vitals to unblock 68 failing tests
jest.mock('web-vitals', () => ({
  onCLS: jest.fn(),
  onFID: jest.fn(),
  onFCP: jest.fn(),
  onLCP: jest.fn(),
  onTTFB: jest.fn(),
}), { virtual: true });

// Mock date-fns for DataRecoveryModal tests
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '5 minutes ago'),
  format: jest.fn((date) => new Date(date).toISOString()),
}), { virtual: true });

// Mock hasPointerCapture for Radix UI Select components
if (typeof Element.prototype.hasPointerCapture === 'undefined') {
  Element.prototype.hasPointerCapture = jest.fn().mockReturnValue(false);
}

if (typeof Element.prototype.setPointerCapture === 'undefined') {
  Element.prototype.setPointerCapture = jest.fn();
}

if (typeof Element.prototype.releasePointerCapture === 'undefined') {
  Element.prototype.releasePointerCapture = jest.fn();
}

// Mock scrollIntoView for Radix UI Select components
if (typeof Element.prototype.scrollIntoView === 'undefined') {
  Element.prototype.scrollIntoView = jest.fn();
}

// Mock ResizeObserver for Radix UI components
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock Next.js navigation for components using useRouter, usePathname, useSearchParams
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  })),
  usePathname: jest.fn(() => '/'),
  useSearchParams: jest.fn(() => new URLSearchParams()),
  useParams: jest.fn(() => ({})),
  redirect: jest.fn(),
  notFound: jest.fn(),
}));

// Mock Radix UI Dialog Portal to work in jsdom (portals don't work properly)
jest.mock('@radix-ui/react-dialog', () => {
  const React = require('react');
  const actual = jest.requireActual('@radix-ui/react-dialog');

  return {
    ...actual,
    // Replace Portal with direct rendering (no createPortal)
    Portal: ({ children }: any) => children,
  };
});

// Mock Radix UI Select with simple HTML <select> for testing
// Radix UI Select uses portals which don't work properly in jsdom
jest.mock('@/components/ui/select', () => {
  const React = require('react');

  // Context to pass options and onValueChange from Select to SelectTrigger
  const SelectContext = React.createContext<any>(null);

  const Select = ({ children, value, onValueChange, defaultValue, ...props }: any) => {
    // Recursively collect all SelectItem children
    const options: any[] = [];

    const collectOptions = (node: any): void => {
      if (!node) return;

      if (node?.type?.displayName === 'SelectItem') {
        options.push({
          value: node.props.value,
          label: node.props.children,
        });
        return;
      }

      if (node.props?.children) {
        React.Children.forEach(node.props.children, collectOptions);
      }
    };

    React.Children.forEach(children, collectOptions);

    return React.createElement(
      SelectContext.Provider,
      { value: { options, onValueChange, selectValue: value || defaultValue } },
      children
    );
  };

  // SelectTrigger will render the actual <select> element with props from FormControl
  const SelectTrigger = React.forwardRef(({ children, ...props }: any, ref: any) => {
    const context = React.useContext(SelectContext);

    if (!context) {
      return children;
    }

    const handleChange = (e: any) => {
      context.onValueChange?.(e.target.value);
    };

    return React.createElement(
      'select',
      {
        ref,
        value: context.selectValue,
        onChange: handleChange,
        ...props, // This includes id, aria-describedby from FormControl
      },
      [
        React.createElement('option', { key: 'empty', value: '' }, 'Select...'),
        ...context.options.map((opt: any) =>
          React.createElement('option', { key: opt.value, value: opt.value }, opt.label)
        ),
      ]
    );
  });
  SelectTrigger.displayName = 'SelectTrigger';

  const SelectContent = ({ children }: any) => children;
  SelectContent.displayName = 'SelectContent';

  const SelectItem = ({ value, children }: any) => null;
  SelectItem.displayName = 'SelectItem';

  return {
    Select,
    SelectGroup: ({ children }: any) => children,
    SelectValue: ({ placeholder }: any) => null, // Not needed in native <select>
    SelectTrigger,
    SelectContent: React.forwardRef((props: any, ref: any) =>
      React.createElement(SelectContent, { ...props, ref })
    ),
    SelectItem,
    SelectScrollUpButton: () => null,
    SelectScrollDownButton: () => null,
  };
});

// Mock TipTap editor for ChapterEditor tests
// TipTap is a complex React editor that doesn't work properly in jsdom
jest.mock('@tiptap/react', () => {
  const React = require('react');

  // Create mock editor instance with all required methods
  const createMockEditor = (config: any) => {
    let content = config?.content || '';
    const updateHandler = config?.onUpdate;

    const mockEditor = {
      // Core properties
      isDestroyed: false,
      isFocused: false,

      // State management
      state: {},
      view: {},
      schema: {},

      // Storage for extensions - DYNAMIC character count
      storage: {
        characterCount: {
          characters: jest.fn(() => {
            // Strip HTML tags and return character count
            const textContent = content.replace(/<[^>]*>/g, '');
            return textContent.length;
          }),
          words: jest.fn(() => {
            const textContent = content.replace(/<[^>]*>/g, '');
            return textContent.split(/\s+/).filter(Boolean).length;
          }),
        },
      },

      // Content methods
      getHTML: jest.fn(() => content),
      getText: jest.fn(() => content.replace(/<[^>]*>/g, '')),
      getJSON: jest.fn(() => ({ type: 'doc', content: [] })),
      isEmpty: jest.fn(() => !content || content === '<p></p>'),

      // Command chain API
      chain: jest.fn(() => ({
        focus: jest.fn(() => ({
          toggleBold: jest.fn(() => ({ run: jest.fn(() => true) })),
          toggleItalic: jest.fn(() => ({ run: jest.fn(() => true) })),
          toggleUnderline: jest.fn(() => ({ run: jest.fn(() => true) })),
          toggleStrike: jest.fn(() => ({ run: jest.fn(() => true) })),
          toggleHeading: jest.fn(() => ({ run: jest.fn(() => true) })),
          toggleBulletList: jest.fn(() => ({ run: jest.fn(() => true) })),
          toggleOrderedList: jest.fn(() => ({ run: jest.fn(() => true) })),
          toggleBlockquote: jest.fn(() => ({ run: jest.fn(() => true) })),
          toggleCodeBlock: jest.fn(() => ({ run: jest.fn(() => true) })),
          setHorizontalRule: jest.fn(() => ({ run: jest.fn(() => true) })),
          insertContent: jest.fn((newContent: string) => ({
            run: jest.fn(() => {
              content += newContent;
              if (updateHandler) {
                updateHandler({ editor: mockEditor });
              }
              return true;
            }),
          })),
          setContent: jest.fn((newContent: string) => ({
            run: jest.fn(() => {
              content = newContent;
              if (updateHandler) {
                updateHandler({ editor: mockEditor });
              }
              return true;
            }),
          })),
          undo: jest.fn(() => ({ run: jest.fn(() => true) })),
          redo: jest.fn(() => ({ run: jest.fn(() => true) })),
          run: jest.fn(() => true),
        })),
      })),

      // Direct command access
      commands: {
        setContent: jest.fn((newContent: string) => {
          content = newContent;
          if (updateHandler) {
            updateHandler({ editor: mockEditor });
          }
          return true;
        }),
        insertContent: jest.fn((newContent: string) => {
          content += newContent;
          if (updateHandler) {
            updateHandler({ editor: mockEditor });
          }
          return true;
        }),
        focus: jest.fn(() => true),
        blur: jest.fn(() => true),
        clearContent: jest.fn(() => {
          content = '';
          if (updateHandler) {
            updateHandler({ editor: mockEditor });
          }
          return true;
        }),
      },

      // Capability checking
      can: jest.fn(() => ({
        chain: jest.fn(() => ({
          focus: jest.fn(() => ({
            undo: jest.fn(() => ({ run: jest.fn(() => true) })),
            redo: jest.fn(() => ({ run: jest.fn(() => true) })),
          })),
        })),
      })),

      // Active state checking
      isActive: jest.fn((name: string, attrs?: any) => {
        if (name === 'heading' && attrs?.level) {
          return content.includes(`<h${attrs.level}>`);
        }
        return content.includes(`<${name}>`);
      }),

      // Lifecycle methods
      destroy: jest.fn(() => {
        mockEditor.isDestroyed = true;
      }),
      on: jest.fn(() => mockEditor),
      off: jest.fn(() => mockEditor),

      // Event emitter
      emit: jest.fn(),

      // Selection
      state: {
        selection: {
          from: 0,
          to: 0,
        },
      },
    };

    return mockEditor;
  };

  // Mock useEditor hook
  const useEditor = jest.fn((config?: any) => {
    const [editor] = React.useState(() => createMockEditor(config));
    // Force re-render when editor content changes by tracking update count
    const [, forceUpdate] = React.useReducer((x) => x + 1, 0);

    // Wrap the original onUpdate handler to force component re-render
    React.useEffect(() => {
      const originalOnUpdate = config?.onUpdate;
      if (originalOnUpdate && editor) {
        // Override the setContent command to also force re-render
        const originalSetContent = editor.commands.setContent;
        editor.commands.setContent = jest.fn((newContent: string) => {
          const result = originalSetContent(newContent);
          // Force parent component to re-render after content change
          forceUpdate();
          return result;
        });
      }
    }, [editor, config?.onUpdate, forceUpdate]);

    // Update content when initialContent changes
    React.useEffect(() => {
      if (config?.content && editor.getHTML() !== config.content) {
        editor.commands.setContent(config.content);
      }
    }, [config?.content, editor]);

    return editor;
  });

  // Mock EditorContent component - render a simple textarea with role="textbox"
  // CRITICAL: This component must trigger onUpdate when user types
  const EditorContent = React.forwardRef(({ editor, className, ...props }: any, ref: any) => {
    const [value, setValue] = React.useState(editor?.getHTML() || '');

    React.useEffect(() => {
      if (editor) {
        setValue(editor.getHTML());
      }
    }, [editor]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value;
      setValue(newValue);

      // CRITICAL FIX: Call setContent which triggers onUpdate callback
      if (editor?.commands?.setContent) {
        editor.commands.setContent(newValue);
      }
    };

    return React.createElement('div', {
      ref,
      className: className,
      'data-testid': 'editor-content',
    }, [
      React.createElement('textarea', {
        key: 'editor-textarea',
        value: value,
        onChange: handleChange,
        className: 'w-full h-full min-h-[200px] p-2 border rounded',
        role: 'textbox',
        'aria-label': 'Chapter content editor',
        'data-testid': 'tiptap-editor',
      }),
    ]);
  });
  EditorContent.displayName = 'EditorContent';

  return {
    useEditor,
    EditorContent,
  };
});

// Mock TipTap extensions
jest.mock('@tiptap/starter-kit', () => {
  return jest.fn(() => ({ name: 'starterKit' }));
});

jest.mock('@tiptap/extension-underline', () => {
  return jest.fn(() => ({ name: 'underline' }));
});

jest.mock('@tiptap/extension-placeholder', () => {
  return {
    configure: jest.fn(() => ({ name: 'placeholder' })),
  };
});

jest.mock('@tiptap/extension-character-count', () => {
  return jest.fn(() => ({ name: 'characterCount' }));
});

// Mock better-auth for all tests
jest.mock('@/lib/auth-client', () => {
  const mockForgetPassword = jest.fn().mockResolvedValue({
    data: {},
    error: null,
  });
  const mockResetPassword = jest.fn().mockResolvedValue({
    data: {},
    error: null,
  });

  return {
    useSession: jest.fn(() => ({
      data: {
        user: {
          id: 'test-user-id',
          email: 'test@example.com',
          name: 'Test User',
          image: null,
        },
        session: {
          token: 'test-token',
          id: 'test-session-id',
          expiresAt: new Date(Date.now() + 86400000),
          fresh: true,
        },
      },
      isPending: false,
      error: null,
    })),
    authClient: {
      signIn: {
        email: jest.fn().mockResolvedValue({
          data: {
            user: {
              id: 'test-user-id',
              email: 'test@example.com',
              name: 'Test User',
            },
            session: {
              token: 'test-token',
              id: 'test-session-id',
            },
          },
          error: null,
        }),
      },
      signUp: {
        email: jest.fn().mockResolvedValue({
          data: {
            user: {
              id: 'test-user-id',
              email: 'test@example.com',
              name: 'Test User',
            },
            session: {
              token: 'test-token',
              id: 'test-session-id',
            },
          },
          error: null,
        }),
      },
      signOut: jest.fn().mockResolvedValue({
        data: {},
        error: null,
      }),
      getSession: jest.fn().mockResolvedValue({
        data: {
          user: {
            id: 'test-user-id',
            email: 'test@example.com',
            name: 'Test User',
          },
          session: {
            token: 'test-token',
            id: 'test-session-id',
          },
        },
        error: null,
      }),
      forgetPassword: mockForgetPassword,
      resetPassword: mockResetPassword,
    },
    // Direct exports for password reset methods
    forgetPassword: mockForgetPassword,
    resetPassword: mockResetPassword,
    // Re-export auth methods that match the module exports
    signIn: {
      email: jest.fn().mockResolvedValue({ data: {}, error: null }),
    },
    signUp: {
      email: jest.fn().mockResolvedValue({ data: {}, error: null }),
    },
    signOut: jest.fn().mockResolvedValue({ data: {}, error: null }),
  };
});
