// src/jest.setup.ts
import '@testing-library/jest-dom';

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
