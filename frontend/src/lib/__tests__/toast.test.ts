/**
 * Tests for src/lib/toast.ts
 * Covers the toast() wrapper and all sub-method helpers (success, error, warning, info).
 */

jest.mock('sonner', () => {
  const fn = jest.fn()
  fn.success = jest.fn()
  fn.error = jest.fn()
  fn.warning = jest.fn()
  fn.info = jest.fn()
  fn.promise = jest.fn()
  return { toast: fn }
})

import * as sonnerModule from 'sonner'
import { toast } from '@/lib/toast'

// Typed handle for the mocked sonner toast
const sonnerToast = sonnerModule.toast as jest.MockedFunction<typeof sonnerModule.toast> & {
  success: jest.Mock
  error: jest.Mock
  warning: jest.Mock
  info: jest.Mock
  promise: jest.Mock
}

beforeEach(() => {
  jest.clearAllMocks()
})

describe('toast() — main function', () => {
  it('calls sonnerToast directly for the default variant', () => {
    toast({ title: 'Hello' })
    expect(sonnerToast).toHaveBeenCalledWith('Hello', expect.objectContaining({ duration: 5000 }))
  })

  it('uses description as message when title is absent', () => {
    toast({ description: 'Only description' })
    expect(sonnerToast).toHaveBeenCalledWith('Only description', expect.objectContaining({ duration: 5000 }))
  })

  it('passes description in options when both title and description are present', () => {
    toast({ title: 'Title', description: 'Detail' })
    expect(sonnerToast).toHaveBeenCalledWith(
      'Title',
      expect.objectContaining({ description: 'Detail', duration: 5000 })
    )
  })

  it('does NOT include description in options when only title is given', () => {
    toast({ title: 'Title only' })
    const [, options] = (sonnerToast as jest.Mock).mock.calls[0]
    expect(options.description).toBeUndefined()
  })

  it('calls sonnerToast.error for the "destructive" variant', () => {
    toast({ title: 'Oops', variant: 'destructive' })
    expect(sonnerToast.error).toHaveBeenCalledWith('Oops', expect.objectContaining({ duration: 5000 }))
    expect(sonnerToast).not.toHaveBeenCalled()
  })

  it('calls sonnerToast.success for the "success" variant', () => {
    toast({ title: 'Done', variant: 'success' })
    expect(sonnerToast.success).toHaveBeenCalledWith('Done', expect.objectContaining({ duration: 5000 }))
    expect(sonnerToast).not.toHaveBeenCalled()
  })

  it('respects a custom duration', () => {
    toast({ title: 'Hi', duration: 2000 })
    expect(sonnerToast).toHaveBeenCalledWith('Hi', expect.objectContaining({ duration: 2000 }))
  })

  it('uses an empty string as message when neither title nor description is given', () => {
    toast({})
    expect(sonnerToast).toHaveBeenCalledWith('', expect.anything())
  })

  it('forwards extra props to sonner', () => {
    toast({ title: 'Test', action: { label: 'Retry', onClick: jest.fn() } } as any)
    expect(sonnerToast).toHaveBeenCalledWith('Test', expect.objectContaining({ action: expect.anything() }))
  })
})

describe('toast.success()', () => {
  it('calls sonnerToast.success with the given title', () => {
    toast.success({ title: 'Saved!' })
    expect(sonnerToast.success).toHaveBeenCalledWith('Saved!', expect.objectContaining({ duration: 4000 }))
  })

  it('defaults title to "Success" when omitted', () => {
    toast.success({})
    expect(sonnerToast.success).toHaveBeenCalledWith('Success', expect.objectContaining({ duration: 4000 }))
  })

  it('passes description through', () => {
    toast.success({ title: 'OK', description: 'All good' })
    expect(sonnerToast.success).toHaveBeenCalledWith('OK', expect.objectContaining({ description: 'All good' }))
  })

  it('respects custom duration', () => {
    toast.success({ title: 'Fast', duration: 1000 })
    expect(sonnerToast.success).toHaveBeenCalledWith('Fast', expect.objectContaining({ duration: 1000 }))
  })
})

describe('toast.error()', () => {
  it('calls sonnerToast.error with the given title', () => {
    toast.error({ title: 'Failed!' })
    expect(sonnerToast.error).toHaveBeenCalledWith('Failed!', expect.objectContaining({ duration: 5000 }))
  })

  it('defaults title to "Error" when omitted', () => {
    toast.error({})
    expect(sonnerToast.error).toHaveBeenCalledWith('Error', expect.objectContaining({ duration: 5000 }))
  })

  it('passes description through', () => {
    toast.error({ title: 'Bad', description: 'Something went wrong' })
    expect(sonnerToast.error).toHaveBeenCalledWith('Bad', expect.objectContaining({ description: 'Something went wrong' }))
  })
})

describe('toast.warning()', () => {
  it('calls sonnerToast.warning with the given title', () => {
    toast.warning({ title: 'Careful!' })
    expect(sonnerToast.warning).toHaveBeenCalledWith('Careful!', expect.objectContaining({ duration: 5000 }))
  })

  it('defaults title to "Warning" when omitted', () => {
    toast.warning({})
    expect(sonnerToast.warning).toHaveBeenCalledWith('Warning', expect.objectContaining({ duration: 5000 }))
  })

  it('passes description through', () => {
    toast.warning({ title: 'Notice', description: 'Be careful' })
    expect(sonnerToast.warning).toHaveBeenCalledWith('Notice', expect.objectContaining({ description: 'Be careful' }))
  })

  it('respects custom duration', () => {
    toast.warning({ duration: 3000 })
    expect(sonnerToast.warning).toHaveBeenCalledWith('Warning', expect.objectContaining({ duration: 3000 }))
  })
})

describe('toast.info()', () => {
  it('calls sonnerToast.info with the given title', () => {
    toast.info({ title: 'FYI' })
    expect(sonnerToast.info).toHaveBeenCalledWith('FYI', expect.objectContaining({ duration: 4000 }))
  })

  it('defaults title to "Info" when omitted', () => {
    toast.info({})
    expect(sonnerToast.info).toHaveBeenCalledWith('Info', expect.objectContaining({ duration: 4000 }))
  })

  it('passes description through', () => {
    toast.info({ title: 'Note', description: 'For your info' })
    expect(sonnerToast.info).toHaveBeenCalledWith('Note', expect.objectContaining({ description: 'For your info' }))
  })

  it('respects custom duration', () => {
    toast.info({ duration: 6000 })
    expect(sonnerToast.info).toHaveBeenCalledWith('Info', expect.objectContaining({ duration: 6000 }))
  })
})

describe('toast.promise', () => {
  it('is the same reference as sonnerToast.promise', () => {
    expect(toast.promise).toBe(sonnerToast.promise)
  })
})
