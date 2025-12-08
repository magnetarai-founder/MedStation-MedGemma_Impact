/**
 * EmojiPicker Component
 * Emoji selector overlay with keyboard navigation support
 */

import React from 'react'
import { X } from 'lucide-react'

interface EmojiPickerProps {
  visible: boolean
  selectedIndex: number
  onSelect: (emoji: string) => void
  onChangeIndex: (index: number) => void
  pickerRef: React.RefObject<HTMLDivElement>
  onClose: () => void
}

const EMOJIS = [
  '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂',
  '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩',
  '😘', '😗', '😚', '😙', '😋', '😛', '😜', '🤪',
  '😎', '🤓', '🧐', '🤨', '🤔', '🤗', '🤭', '🤫',
  '🤥', '😶', '😐', '😑', '😬', '🙄', '😏', '😌',
  '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢',
  '👍', '👎', '👌', '✌️', '🤞', '🤝', '👏', '🙌',
  '❤️', '💙', '💚', '💛', '🧡', '💜', '🖤', '🤍',
  '✅', '❌', '⭐', '🔥', '💯', '🎉', '🎊', '🚀'
]

export function EmojiPicker({
  visible,
  selectedIndex,
  onSelect,
  onChangeIndex,
  pickerRef,
  onClose
}: EmojiPickerProps) {
  if (!visible) return null

  return (
    <div
      ref={pickerRef}
      className="absolute bottom-full mb-2 right-20 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl p-3 z-50"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Emoji</span>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-900 rounded"
        >
          <X size={14} className="text-gray-500 dark:text-gray-400" />
        </button>
      </div>
      <div className="grid grid-cols-8 gap-1 max-w-xs">
        {EMOJIS.map((emoji, index) => (
          <button
            key={emoji}
            onClick={() => onSelect(emoji)}
            className={`text-xl p-1.5 rounded transition-colors ${
              index === selectedIndex
                ? 'bg-primary-500 text-white'
                : 'hover:bg-gray-100 dark:hover:bg-gray-900'
            }`}
          >
            {emoji}
          </button>
        ))}
      </div>
    </div>
  )
}

// Export emoji list for keyboard navigation
export { EMOJIS }
