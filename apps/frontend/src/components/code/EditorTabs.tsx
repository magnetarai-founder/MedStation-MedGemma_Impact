type OpenFile = { path: string; name: string }

interface EditorTabsProps {
  files: OpenFile[]
  activePath: string
  onActivate: (path: string) => void
  onClose: (path: string) => void
}

export function EditorTabs({ files, activePath, onActivate, onClose }: EditorTabsProps) {
  return (
    <div className="flex items-center gap-1 px-2 py-1 border-b border-gray-200 dark:border-gray-700 overflow-auto">
      {files.length === 0 ? (
        <div className="text-xs text-gray-500 px-2 py-1">No file open</div>
      ) : (
        files.map((f) => (
          <button
            key={f.path}
            onClick={() => onActivate(f.path)}
            className={`px-2 py-1 rounded border text-xs flex items-center gap-2 ${
              f.path === activePath
                ? 'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700'
                : 'bg-gray-100 dark:bg-gray-800 border-transparent hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
            title={f.path}
          >
            <span className="truncate max-w-[180px]">{f.name}</span>
            <span
              onClick={(e) => {
                e.stopPropagation()
                onClose(f.path)
              }}
              className="text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
            >
              ×
            </span>
          </button>
        ))
      )}
    </div>
  )
}

