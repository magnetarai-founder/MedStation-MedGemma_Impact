/**
 * MessageInput Component
 * Message composition area with formatting toolbar, file upload, and emoji picker
 */

import React from 'react'
import { Send, Smile, Paperclip, Bold, Italic, Code, Link as LinkIcon, AtSign, X } from 'lucide-react'
import { EmojiPicker } from './EmojiPicker'

interface MessageInputProps {
  mode: 'solo' | 'p2p'
  messageInput: string
  onChangeMessageInput: (value: string) => void
  onSendMessage: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
  uploadedFile: File | null
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void
  onFileUploadClick: () => void
  onRemoveFile: () => void
  onToggleEmojiPicker: () => void
  showEmojiPicker: boolean
  inputRef: React.RefObject<HTMLTextAreaElement>
  fileInputRef: React.RefObject<HTMLInputElement>
  onInsertMention: () => void
  onBold: () => void
  onItalic: () => void
  onCode: () => void
  onLink: () => void
  activeChannelName: string
  selectedEmojiIndex: number
  onSelectEmoji: (emoji: string) => void
  onChangeEmojiIndex: (index: number) => void
  emojiPickerRef: React.RefObject<HTMLDivElement>
}

export function MessageInput({
  mode,
  messageInput,
  onChangeMessageInput,
  onSendMessage,
  onKeyDown,
  uploadedFile,
  onFileSelect,
  onFileUploadClick,
  onRemoveFile,
  onToggleEmojiPicker,
  showEmojiPicker,
  inputRef,
  fileInputRef,
  onInsertMention,
  onBold,
  onItalic,
  onCode,
  onLink,
  activeChannelName,
  selectedEmojiIndex,
  onSelectEmoji,
  onChangeEmojiIndex,
  emojiPickerRef
}: MessageInputProps) {
  return (
    <div className="flex-shrink-0 px-4 pb-6 relative">
      <div className="border-2 border-gray-300 dark:border-gray-700 rounded-lg focus-within:border-gray-400 dark:focus-within:border-gray-600 transition-colors">
        {/* Formatting toolbar */}
        <div className="flex items-center gap-1 px-2 py-1.5 border-b border-gray-200 dark:border-gray-700">
          <button onClick={onBold} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Bold">
            <Bold size={16} />
          </button>
          <button onClick={onItalic} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Italic">
            <Italic size={16} />
          </button>
          <button onClick={onCode} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Code">
            <Code size={16} />
          </button>
          <button onClick={onLink} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Link">
            <LinkIcon size={16} />
          </button>
          <div className="flex-1"></div>
          <button onClick={onToggleEmojiPicker} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Emoji">
            <Smile size={16} />
          </button>
          <button onClick={onFileUploadClick} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Attach file">
            <Paperclip size={16} />
          </button>
        </div>

        {/* Emoji Picker */}
        <EmojiPicker
          visible={showEmojiPicker}
          selectedIndex={selectedEmojiIndex}
          onSelect={onSelectEmoji}
          onChangeIndex={onChangeEmojiIndex}
          pickerRef={emojiPickerRef}
          onClose={() => onToggleEmojiPicker()}
        />

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          onChange={onFileSelect}
          className="hidden"
        />

        {/* File preview */}
        {uploadedFile && (
          <div className="px-3 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <Paperclip size={16} className="text-gray-500 dark:text-gray-400" />
              <span className="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">
                {uploadedFile.name}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {(uploadedFile.size / 1024).toFixed(1)} KB
              </span>
              <button
                onClick={onRemoveFile}
                className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded"
                title="Remove file"
              >
                <X size={14} className="text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          </div>
        )}

        {/* Input area */}
        <div className="relative">
          <textarea
            ref={inputRef}
            value={messageInput}
            onChange={(e) => onChangeMessageInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={`Message #${activeChannelName}`}
            className="w-full px-3 py-2.5 bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none resize-none"
            rows={1}
            style={{
              minHeight: '44px',
              maxHeight: '200px',
            }}
          />
        </div>

        {/* Bottom actions */}
        <div className="flex items-center justify-between px-2 py-1.5 border-t border-gray-200 dark:border-gray-700">
          <button onClick={onInsertMention} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors text-xs font-medium" title="Mention someone">
            <AtSign size={14} className="inline mr-1" />
          </button>

          <button
            onClick={onSendMessage}
            disabled={!messageInput.trim() && !uploadedFile}
            className="p-1.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 dark:disabled:bg-gray-800 disabled:cursor-not-allowed rounded text-white transition-colors"
            title="Send message"
          >
            <Send size={16} />
          </button>
        </div>
      </div>

      <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 px-1">
        <span className="font-semibold">⌘B</span> bold · <span className="font-semibold">⌘I</span> italic · <span className="font-semibold">⌘K</span> link · <span className="font-semibold">⌘⌃Space</span> emoji · <span className="font-semibold">Enter</span> send · <span className="font-semibold">⇧Enter</span> new line
      </p>
    </div>
  )
}
