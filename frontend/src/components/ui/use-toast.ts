// Minimal mock for use-toast for test compatibility
export function useToast() {
  return {
    toast: jest.fn()
  };
}
