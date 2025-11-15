import { useEffect, useMemo, useState } from 'react'
import { MiniAIChatModal } from '@/components/code/MiniAIChatModal'
import { FileTree } from '@/components/code/FileTree'
import { EditorTabs } from '@/components/code/EditorTabs'
import { Bot, Folder, Loader2, TerminalSquare } from 'lucide-react'

type OpenFile = { path: string; name: string; language?: string; content?: string }

export function CodePage() {
  const [loading, setLoading] = useState(true)
  const [rootPath, setRootPath] = useState<string>('')
  const [files, setFiles] = useState<{ path: string; name: string; isDir: boolean }[]>([])
  const [openFiles, setOpenFiles] = useState<OpenFile[]>([])
  const [activePath, setActivePath] = useState<string>('')
  const [showAI, setShowAI] = useState(false)

  useEffect(() => {
    // TODO: Replace with real workspace + file listing API
    // Placeholder: set a mock file list
    setTimeout(() => {
      setRootPath('/workspace')
      setFiles([
        { path: '/workspace/README.md', name: 'README.md', isDir: false },
        { path: '/workspace/src', name: 'src', isDir: true },
        { path: '/workspace/src/main.ts', name: 'main.ts', isDir: false },
        { path: '/workspace/src/App.tsx', name: 'App.tsx', isDir: false },
      ])
      setLoading(false)
    }, 300)
  }, [])

  const activeFile = useMemo(() => openFiles.find(f => f.path === activePath), [openFiles, activePath])

  const openFile = (path: string, name: string) => {
    if (!openFiles.some(f => f.path === path)) {
      setOpenFiles(prev => [...prev, { path, name, language: inferLanguage(name), content: '' }])
    }
    setActivePath(path)
  }

  const closeFile = (path: string) => {
    setOpenFiles(prev => prev.filter(f => f.path !== path))
    if (activePath === path) {
      const next = openFiles.find(f => f.path !== path)
      setActivePath(next?.path || '')
    }
  }

  const inferLanguage = (name: string) => {
    if (name.endsWith('.ts') || name.endsWith('.tsx')) return 'typescript'
    if (name.endsWith('.js') || name.endsWith('.jsx')) return 'javascript'
    if (name.endsWith('.py')) return 'python'
    if (name.endsWith('.rs')) return 'rust'
    if (name.endsWith('.md')) return 'markdown'
    return 'plaintext'
  }

  return (
    <div className="h-full w-full flex">
      {/* Left: File Tree */}
      <div className="w-64 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 bg-gray-50/70 dark:bg-gray-900/40">
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2 text-sm">
          <Folder className="w-4 h-4" />
          <span className="font-medium">Explorer</span>
        </div>
        {loading ? (
          <div className="p-3 text-sm text-gray-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading files…</div>
        ) : (
          <FileTree
            rootPath={rootPath}
            items={files}
            activePath={activePath}
            onOpen={openFile}
          />
        )}
      </div>

      {/* Right: Editor + Toolbar */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Toolbar */}
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
          <button
            onClick={() => setShowAI(true)}
            className="px-2.5 py-1.5 text-xs rounded bg-primary-600 hover:bg-primary-700 text-white flex items-center gap-1.5"
            title="Code with AI"
          >
            <Bot className="w-3.5 h-3.5" />
            <span>Code with AI</span>
          </button>
          <button className="px-2.5 py-1.5 text-xs rounded border bg-white hover:bg-gray-50 dark:bg-gray-900 dark:border-gray-700 flex items-center gap-1.5">
            <TerminalSquare className="w-3.5 h-3.5" />
            <span>Terminal</span>
          </button>
        </div>

        {/* Tabs */}
        <EditorTabs
          files={openFiles}
          activePath={activePath}
          onActivate={setActivePath}
          onClose={closeFile}
        />

        {/* Editor placeholder */}
        <div className="flex-1 min-h-0">
          {activeFile ? (
            <div className="h-full w-full p-3 text-sm text-gray-600 dark:text-gray-300">
              {/* TODO: integrate Monaco; for now, show placeholder */}
              <div className="text-xs text-gray-500 mb-1">{activeFile.path}</div>
              <div className="h-full rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-2">
                <pre className="text-xs opacity-60">Monaco editor placeholder</pre>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm">Open a file from Explorer</div>
          )}
        </div>
      </div>

      {showAI && (
        <MiniAIChatModal
          isOpen={showAI}
          onClose={() => setShowAI(false)}
          context={{ filePath: activeFile?.path || '', language: activeFile?.language || 'plaintext' }}
        />
      )}
    </div>
  )
}

