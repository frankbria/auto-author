// Minimal mock for draftClient to resolve module errors in tests
export const draftClient = {
  getDraft: jest.fn(),
  saveDraft: jest.fn(),
  updateDraft: jest.fn(),
};
