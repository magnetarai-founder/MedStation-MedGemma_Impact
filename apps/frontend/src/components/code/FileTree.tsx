import { ChevronRight, File, Folder } from 'lucide-react'

interface FileTreeItem {
  path: string
  name: string
  isDir: boolean
}

interface FileTreeProps {
  rootPath: string
  items: FileTreeItem[]
  activePath?: string
  onOpen: (path: string, name: string) => void
}

export function FileTree({ rootPath, items, activePath, onOpen }: FileTreeProps) {
  // Minimal flat list rendering (replace with a real recursive tree later)
  return (
    <div className="p-2 text-sm">
      <div className="text-xs text-gray-500 mb-1 truncate" title={rootPath}>{rootPath || 'Workspace'}</div>
      <div className="space-y-0.5">
        {items.map((it) => (
          <button
            key={it.path}
            onClick={() => !it.isDir && onOpen(it.path, it.name)}
            className={`w-full flex items-center gap-2 px-2 py-1 rounded text-left hover:bg-gray-100 dark:hover:bg-gray-800 ${
              activePath === it.path ? 'bg-gray-100 dark:bg-gray-800' : ''
            } ${it.isDir ? 'cursor-default' : ''}`}
          >
            {it.isDir ? <ChevronRight className="w-3.5 h-3.5 opacity-60" /> : <File className="w-3.5 h-3.5 opacity-60" />}
            <span className="truncate" title={it.path}>{it.name}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

