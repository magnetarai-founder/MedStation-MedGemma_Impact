import { create } from 'zustand'

interface JsonConversionResult {
  preview: any[]
  total_rows: number
  sheets: string[]
  columns: string[]
  output_file: string
}

interface JsonFileData {
  filename: string
  columns: string[]
  content?: string
  preview?: any[]
  fullFile?: File  // Store the actual file for conversion
}

interface JsonStore {
  conversionResult: JsonConversionResult | null
  setConversionResult: (result: JsonConversionResult | null) => void
  isConverting: boolean
  setIsConverting: (isConverting: boolean) => void
  abortController: AbortController | null
  setAbortController: (controller: AbortController | null) => void
  jsonFileData: JsonFileData | null
  setJsonFileData: (data: JsonFileData | null) => void
  jsonContent: string
  setJsonContent: (content: string) => void
  actualJsonContent: string  // Store the full content for conversion
  setActualJsonContent: (content: string) => void
}

export const useJsonStore = create<JsonStore>((set) => ({
  conversionResult: null,
  setConversionResult: (result) => set({ conversionResult: result }),
  isConverting: false,
  setIsConverting: (isConverting) => set({ isConverting }),
  abortController: null,
  setAbortController: (controller) => set({ abortController: controller }),
  jsonFileData: null,
  setJsonFileData: (data) => set({ jsonFileData: data }),
  jsonContent: `{
  "example": "Paste your JSON here",
  "array": [1, 2, 3],
  "nested": {
    "key": "value"
  }
}`,
  setJsonContent: (content) => set({ jsonContent: content }),
  actualJsonContent: `{
  "example": "Paste your JSON here",
  "array": [1, 2, 3],
  "nested": {
    "key": "value"
  }
}`,
  setActualJsonContent: (content) => set({ actualJsonContent: content }),
}))