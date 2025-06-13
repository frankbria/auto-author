// Minimal mock for @tanstack/react-query to resolve module errors in tests
export const useQuery = jest.fn();
export const useMutation = jest.fn();
export const QueryClient = jest.fn();
export const QueryClientProvider = jest.fn(({ children }) => children);
