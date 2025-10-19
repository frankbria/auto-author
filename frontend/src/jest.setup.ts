// src/jest.setup.ts
import '@testing-library/jest-dom';

// Add TextEncoder/TextDecoder polyfills for Node.js environment
if (typeof global.TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

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
