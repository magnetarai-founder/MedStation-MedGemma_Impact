/**
 * TagInput Component
 *
 * Tag input with hash pills, hover-to-remove, ENTER-to-add behavior, and max tags limit
 */

import { useState } from 'react'
import { X, Hash } from 'lucide-react'

interface TagInputProps {
  tags: string[]
  onChange: (tags: string[]) => void
  maxTags?: number
}

export function TagInput({ tags, onChange, maxTags = 3 }: TagInputProps) {
  const [inputValue, setInputValue] = useState('')
  const [hoveredTag, setHoveredTag] = useState<number | null>(null)

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault()
      if (tags.length >= maxTags) {
        alert(`Maximum ${maxTags} tags allowed`)
        return
      }
      const newTag = inputValue.trim().toLowerCase().replace(/^#+/, '') // Remove leading #
      if (!tags.includes(newTag)) {
        onChange([...tags, newTag])
      }
      setInputValue('')
    }
  }

  const removeTag = (index: number) => {
    onChange(tags.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 mb-2">
        {tags.map((tag, idx) => (
          <div
            key={idx}
            className="group relative inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-sm font-medium transition-all"
            onMouseEnter={() => setHoveredTag(idx)}
            onMouseLeave={() => setHoveredTag(null)}
          >
            <Hash className="w-3 h-3" />
            <span>{tag}</span>
            {hoveredTag === idx && (
              <button
                onClick={() => removeTag(idx)}
                className="ml-1 p-0.5 rounded-full hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                title="Remove tag"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        ))}
      </div>
      {tags.length < maxTags && (
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Add tag (${tags.length}/${maxTags})... Press Enter`}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
        />
      )}
    </div>
  )
}
