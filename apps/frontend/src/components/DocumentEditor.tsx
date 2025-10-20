/**
 * Document Editor
 *
 * Universal editor that handles:
 * - Doc: Rich text editing
 * - Sheet: Spreadsheet editing
 * - Insight: Voice transcription + AI analysis
 */

import { useState, useEffect, useRef } from 'react'
import { useDocsStore, type Document } from '@/stores/docsStore'
import { Save, Lock, Unlock, Shield, Upload, Sparkles, Loader2, Menu } from 'lucide-react'
import toast from 'react-hot-toast'
import { SpreadsheetEditor } from './SpreadsheetEditor'

interface DocumentEditorProps {
  document: Document
  onToggleSidebar?: () => void
  isSidebarCollapsed?: boolean
}

export function DocumentEditor({ document, onToggleSidebar, isSidebarCollapsed }: DocumentEditorProps) {
  const { updateDocument, lockDocument, unlockDocument, lockedDocuments } = useDocsStore()
  const [content, setContent] = useState(document.content)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isLocked = lockedDocuments.has(document.id)

  useEffect(() => {
    setContent(document.content)
    setHasUnsavedChanges(false)
  }, [document.id])

  const handleContentChange = (newContent: any) => {
    setContent(newContent)
    setHasUnsavedChanges(true)
  }

  const handleSave = () => {
    updateDocument(document.id, { content })
    setHasUnsavedChanges(false)
  }

  const handleToggleLock = () => {
    if (isLocked) {
      // TODO: Implement Touch ID authentication before unlocking
      unlockDocument(document.id)
    } else {
      lockDocument(document.id)
    }
  }

  const handleVoiceUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Check file type
    const validTypes = ['audio/m4a', 'audio/mp4', 'audio/x-m4a', 'audio/mpeg', 'audio/wav', 'audio/webm']
    if (!validTypes.includes(file.type) && !file.name.endsWith('.m4a')) {
      toast.error('Please upload an audio file (.m4a, .mp3, .wav, .webm)')
      return
    }

    setIsTranscribing(true)
    toast.loading('Transcribing audio...', { id: 'transcribe' })

    try {
      const formData = new FormData()
      formData.append('audio_file', file)

      const response = await fetch('/api/v1/insights/transcribe', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Transcription failed')
      }

      const data = await response.json()

      // Update content with transcribed text
      const newContent = {
        ...content,
        raw: (content?.raw || '') + (content?.raw ? '\n\n' : '') + data.transcript,
        audio_file: file.name,
      }

      handleContentChange(newContent)
      handleSave()

      toast.success('Audio transcribed successfully!', { id: 'transcribe' })
    } catch (error) {
      console.error('Transcription error:', error)
      toast.error('Failed to transcribe audio', { id: 'transcribe' })
    } finally {
      setIsTranscribing(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleAnalyzeWithAI = async () => {
    if (!content?.raw || content.raw.trim().length === 0) {
      toast.error('Please add a transcript first')
      return
    }

    setIsAnalyzing(true)
    toast.loading('Analyzing with AI...', { id: 'analyze' })

    try {
      const response = await fetch('/api/v1/insights/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: content.raw,
          document_title: document.title,
        }),
      })

      if (!response.ok) {
        throw new Error('Analysis failed')
      }

      const data = await response.json()

      // Update content with AI analysis
      const newContent = {
        ...content,
        analysis: data.analysis,
      }

      handleContentChange(newContent)
      handleSave()

      toast.success('Analysis complete!', { id: 'analyze' })
    } catch (error) {
      console.error('Analysis error:', error)
      toast.error('Failed to analyze transcript', { id: 'analyze' })
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Render different editors based on document type
  const renderEditor = () => {
    if (isLocked) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Lock className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Document Locked
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              {document.type === 'insight'
                ? 'This insight is locked for your privacy'
                : 'This document is locked'}
            </p>
            <button
              onClick={handleToggleLock}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium"
            >
              Unlock with Touch ID
            </button>
          </div>
        </div>
      )
    }

    switch (document.type) {
      case 'doc':
        return (
          <div className="flex-1 overflow-auto p-8">
            <div className="max-w-4xl mx-auto">
              <textarea
                value={typeof content === 'string' ? content : ''}
                onChange={(e) => handleContentChange(e.target.value)}
                placeholder="Start writing..."
                className="w-full min-h-[600px] p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              />
            </div>
          </div>
        )

      case 'sheet':
        return (
          <SpreadsheetEditor
            data={content || { rows: [], columns: [] }}
            onChange={handleContentChange}
            onSave={handleSave}
          />
        )

      case 'insight':
        return (
          <div className="flex-1 overflow-auto p-8">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-2 gap-6">
                {/* Raw Input */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Raw Transcript
                    </h3>
                    <div className="flex items-center gap-2">
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="audio/*,.m4a"
                        onChange={handleVoiceUpload}
                        className="hidden"
                      />
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isTranscribing}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Upload voice memo (.m4a, .mp3, .wav)"
                      >
                        {isTranscribing ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>Transcribing...</span>
                          </>
                        ) : (
                          <>
                            <Upload className="w-3.5 h-3.5" />
                            <span>Upload Audio</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                  <textarea
                    value={typeof content?.raw === 'string' ? content.raw : ''}
                    onChange={(e) =>
                      handleContentChange({ ...content, raw: e.target.value })
                    }
                    placeholder="Paste your transcript or upload an audio file..."
                    className="w-full h-[500px] p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none text-sm"
                    disabled={isTranscribing}
                  />
                </div>

                {/* AI Analysis */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      AI Analysis
                    </h3>
                    <button
                      onClick={handleAnalyzeWithAI}
                      disabled={isAnalyzing || !content?.raw || content.raw.trim().length === 0}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Analyze transcript with AI"
                    >
                      {isAnalyzing ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Analyzing...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Analyze with AI</span>
                        </>
                      )}
                    </button>
                  </div>
                  {content?.analysis ? (
                    <textarea
                      value={content.analysis}
                      readOnly
                      className="w-full h-[500px] p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none text-sm select-text cursor-text"
                      placeholder="Analysis will appear here..."
                    />
                  ) : (
                    <div className="h-[500px] p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800/50 overflow-auto">
                      <div className="text-center text-gray-400 py-8">
                        <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        <p className="text-sm">No analysis yet</p>
                        <p className="text-xs mt-2">
                          Add transcript and click "Analyze with AI"
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-gray-600 dark:text-gray-400"
              title={isSidebarCollapsed ? "Show sidebar" : "Hide sidebar"}
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          <input
            type="text"
            value={document.title}
            onChange={(e) => updateDocument(document.id, { title: e.target.value })}
            className="text-lg font-semibold bg-transparent border-none focus:outline-none text-gray-900 dark:text-gray-100"
            disabled={isLocked}
          />
          {document.is_private && (
            <div className="flex items-center gap-1 px-2 py-1 bg-amber-100 dark:bg-amber-900/30 rounded text-xs text-amber-700 dark:text-amber-400">
              <Shield className="w-3 h-3" />
              <span>Private</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {hasUnsavedChanges && (
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-all"
            >
              <Save className="w-4 h-4" />
              <span>Save</span>
            </button>
          )}

          {document.type === 'insight' && (
            <button
              onClick={handleToggleLock}
              className={`p-2 rounded-lg transition-all ${
                isLocked
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
              title={isLocked ? 'Unlock' : 'Lock'}
            >
              {isLocked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Editor */}
      {renderEditor()}
    </div>
  )
}
