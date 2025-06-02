export const createMockAudioBlob = (duration: number = 5000): Blob => {
  // Create a mock audio blob
  const audioData = new Uint8Array(duration * 44.1); // Simulate 44.1kHz sample rate
  return new Blob([audioData], { type: 'audio/webm' });
};

export const createMockMediaStream = (): MediaStream => {
  const audioTrack = {
    kind: 'audio',
    id: 'mock-audio-track',
    enabled: true,
    stop: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  };
  
  return {
    getAudioTracks: () => [audioTrack],
    getTracks: () => [audioTrack],
    addTrack: jest.fn(),
    removeTrack: jest.fn(),
  } as unknown as MediaStream;
};

export const mockMediaDevices = {
  getUserMedia: jest.fn().mockResolvedValue(createMockMediaStream()),
  enumerateDevices: jest.fn().mockResolvedValue([
    { kind: 'audioinput', deviceId: 'default', label: 'Default Microphone' }
  ]),
};
