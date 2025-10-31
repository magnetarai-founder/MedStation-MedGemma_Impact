/**
 * Slash Command Menu Component
 *
 * Notion-style slash command menu for rich text editing
 * Triggered by typing "/" at the start of a line or after a space
 */

import { useState, useEffect, useRef } from 'react'
import {
  Hash,
  List,
  ListOrdered,
  CheckSquare,
  Code,
  Quote,
  Image,
  Table,
  Minus,
  AlertCircle,
  FileText,
  Type,
} from 'lucide-react'

export interface SlashCommand {
  id: string
  name: string
  label: string
  icon: any
  description: string
  aliases?: string[]
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    id: 'h1',
    name: '/h1',
    label: 'Heading 1',
    icon: Hash,
    description: 'Large section heading',
    aliases: ['/heading1', '/title'],
  },
  {
    id: 'h2',
    name: '/h2',
    label: 'Heading 2',
    icon: Hash,
    description: 'Medium section heading',
    aliases: ['/heading2', '/subtitle'],
  },
  {
    id: 'h3',
    name: '/h3',
    label: 'Heading 3',
    icon: Hash,
    description: 'Small section heading',
    aliases: ['/heading3'],
  },
  {
    id: 'bullet',
    name: '/bullet',
    label: 'Bullet List',
    icon: List,
    description: 'Create a bulleted list',
    aliases: ['/ul', '/list'],
  },
  {
    id: 'numbered',
    name: '/numbered',
    label: 'Numbered List',
    icon: ListOrdered,
    description: 'Create a numbered list',
    aliases: ['/ol', '/1'],
  },
  {
    id: 'todo',
    name: '/todo',
    label: 'Todo List',
    icon: CheckSquare,
    description: 'Track tasks with checkboxes',
    aliases: ['/checkbox', '/task'],
  },
  {
    id: 'code',
    name: '/code',
    label: 'Code Block',
    icon: Code,
    description: 'Insert a code block',
    aliases: ['/codeblock'],
  },
  {
    id: 'quote',
    name: '/quote',
    label: 'Quote',
    icon: Quote,
    description: 'Insert a quote block',
    aliases: ['/blockquote'],
  },
  {
    id: 'image',
    name: '/image',
    label: 'Image',
    icon: Image,
    description: 'Upload or embed an image',
    aliases: ['/img', '/picture'],
  },
  {
    id: 'table',
    name: '/table',
    label: 'Table',
    icon: Table,
    description: 'Insert a table',
  },
  {
    id: 'divider',
    name: '/divider',
    label: 'Divider',
    icon: Minus,
    description: 'Insert a horizontal divider',
    aliases: ['/hr', '/line'],
  },
  {
    id: 'callout',
    name: '/callout',
    label: 'Callout',
    icon: AlertCircle,
    description: 'Create a highlighted callout box',
    aliases: ['/info', '/note'],
  },
]

interface SlashCommandMenuProps {
  position: { x: number; y: number }
  searchQuery?: string
  onSelect: (command: SlashCommand) => void
  onClose: () => void
}

export function SlashCommandMenu({
  position,
  searchQuery = '',
  onSelect,
  onClose,
}: SlashCommandMenuProps) {
  const [selectedIndex, setSelectedIndex] = useState(0)
  const menuRef = useRef<HTMLDivElement>(null)

  // Filter commands based on search query
  const filteredCommands = SLASH_COMMANDS.filter((cmd) => {
    const query = searchQuery.toLowerCase()
    return (
      cmd.name.toLowerCase().includes(query) ||
      cmd.label.toLowerCase().includes(query) ||
      cmd.description.toLowerCase().includes(query) ||
      cmd.aliases?.some((alias) => alias.toLowerCase().includes(query))
    )
  })

  // Reset selected index when filtered commands change
  useEffect(() => {
    setSelectedIndex(0)
  }, [searchQuery])

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (filteredCommands.length === 0) {
        if (e.key === 'Escape') {
          onClose()
        }
        return
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((i) => (i + 1) % filteredCommands.length)
          break

        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((i) => (i - 1 + filteredCommands.length) % filteredCommands.length)
          break

        case 'Enter':
          e.preventDefault()
          onSelect(filteredCommands[selectedIndex])
          break

        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedIndex, filteredCommands, onSelect, onClose])

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  // Scroll selected item into view
  useEffect(() => {
    const selectedElement = menuRef.current?.children[selectedIndex] as HTMLElement
    selectedElement?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [selectedIndex])

  if (filteredCommands.length === 0) {
    return (
      <div
        ref={menuRef}
        className="absolute z-50 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 p-4"
        style={{ top: `${position.y}px`, left: `${position.x}px` }}
      >
        <div className="text-center text-gray-500 dark:text-gray-400 text-sm">
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No commands found</p>
          <p className="text-xs mt-1">Try a different search term</p>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={menuRef}
      className="absolute z-50 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 max-h-96 overflow-y-auto"
      style={{ top: `${position.y}px`, left: `${position.x}px` }}
    >
      <div className="p-2">
        <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Basic Blocks
        </div>
        {filteredCommands.map((cmd, index) => {
          const Icon = cmd.icon
          const isSelected = index === selectedIndex

          return (
            <button
              key={cmd.id}
              onClick={() => onSelect(cmd)}
              onMouseEnter={() => setSelectedIndex(index)}
              className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                isSelected
                  ? 'bg-blue-50 dark:bg-blue-900/30'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
              }`}
            >
              <div
                className={`p-2 rounded-lg ${
                  isSelected
                    ? 'bg-blue-100 dark:bg-blue-900/50'
                    : 'bg-gray-100 dark:bg-gray-700'
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                    isSelected
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                />
              </div>

              <div className="flex-1 min-w-0">
                <div
                  className={`text-sm font-medium ${
                    isSelected
                      ? 'text-blue-900 dark:text-blue-100'
                      : 'text-gray-900 dark:text-gray-100'
                  }`}
                >
                  {cmd.label}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                  {cmd.description}
                </div>
              </div>

              <div className="text-xs text-gray-400 dark:text-gray-500 font-mono">
                {cmd.name}
              </div>
            </button>
          )
        })}
      </div>

      {/* Footer hint */}
      <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>↑↓ Navigate</span>
          <span>↵ Select</span>
          <span>Esc Close</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Hook to manage slash command menu state
 */
export function useSlashCommandMenu() {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [searchQuery, setSearchQuery] = useState('')

  function openMenu(pos: { x: number; y: number }) {
    setPosition(pos)
    setIsOpen(true)
    setSearchQuery('')
  }

  function closeMenu() {
    setIsOpen(false)
    setSearchQuery('')
  }

  function updateSearch(query: string) {
    setSearchQuery(query)
  }

  return {
    isOpen,
    position,
    searchQuery,
    openMenu,
    closeMenu,
    updateSearch,
  }
}

/**
 * Convert slash command to markdown/HTML
 */
export function getCommandInsertion(commandId: string): string {
  switch (commandId) {
    case 'h1':
      return '# '
    case 'h2':
      return '## '
    case 'h3':
      return '### '
    case 'bullet':
      return '- '
    case 'numbered':
      return '1. '
    case 'todo':
      return '- [ ] '
    case 'code':
      return '```\n\n```'
    case 'quote':
      return '> '
    case 'image':
      return '![alt text](url)'
    case 'table':
      return '| Column 1 | Column 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |'
    case 'divider':
      return '\n---\n'
    case 'callout':
      return '> ℹ️ **Note:** '
    default:
      return ''
  }
}
