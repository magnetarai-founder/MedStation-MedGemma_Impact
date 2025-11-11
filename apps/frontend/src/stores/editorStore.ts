import { createWithEqualityFn } from 'zustand/traditional'

type ContentType = 'sql' | 'json' | null

interface EditorState {
  code: string
  contentType: ContentType
  hasExecuted: boolean

  setCode: (code: string) => void
  setContentType: (type: ContentType) => void
  setHasExecuted: (executed: boolean) => void
  loadQuery: (code: string, type: ContentType) => void
  reset: () => void
}

export const useEditorStore = createWithEqualityFn<EditorState>((set) => ({
  code: '',
  contentType: null,
  hasExecuted: false,

  setCode: (code) => set({ code }),
  setContentType: (type) => set({ contentType: type }),
  setHasExecuted: (executed) => set({ hasExecuted: executed }),
  loadQuery: (code, type) => set({ code, contentType: type }),
  reset: () => set({ code: '', contentType: null, hasExecuted: false }),
}))
