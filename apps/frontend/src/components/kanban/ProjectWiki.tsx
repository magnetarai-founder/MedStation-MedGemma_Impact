import { useState, useEffect, useRef } from 'react'
import { X, Plus, FileText, Wifi, WifiOff, Save } from 'lucide-react'
import toast from 'react-hot-toast'
import * as Y from 'yjs'
import * as kanbanApi from '@/lib/kanbanApi'
import type { WikiItem } from '@/lib/kanbanApi'
import { createProviders } from '@/lib/collab/yProvider'
import { useYTextBinding } from '@/lib/collab/useYTextBinding'

interface ProjectWikiProps {
  projectId: string
  onClose: () => void
}

export function ProjectWiki({ projectId, onClose }: ProjectWikiProps) {
  const [pages, setPages] = useState<WikiItem[]>([])
  const [selectedPage, setSelectedPage] = useState<WikiItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [connected, setConnected] = useState(false)
  const [editTitle, setEditTitle] = useState('')

  // Yjs refs
  const ydocRef = useRef<Y.Doc | null>(null)
  const ytextRef = useRef<Y.Text | null>(null)
  const providerRef = useRef<any>(null)

  useEffect(() => {
    loadPages()
  }, [projectId])

  // Initialize Yjs for selected page
  useEffect(() => {
    if (!selectedPage) {
      // Cleanup on page deselect
      if (providerRef.current) {
        providerRef.current.destroy?.()
        providerRef.current = null
      }
      if (ydocRef.current) {
        ydocRef.current.destroy()
        ydocRef.current = null
      }
      ytextRef.current = null
      setConnected(false)
      return
    }

    // Initialize Y.Doc for this page
    const ydoc = new Y.Doc()
    ydocRef.current = ydoc

    const providers = createProviders(`wiki:${selectedPage.page_id}`, ydoc)
    providerRef.current = providers

    // Monitor connection status
    providers.wsProvider.on('status', (event: { status: string }) => {
      setConnected(event.status === 'connected')
    })

    const ytext = ydoc.getText('content')
    ytextRef.current = ytext

    // Seed Y.Text from REST if empty
    const isEmpty = ytext.length === 0
    if (isEmpty && selectedPage.content) {
      ytext.insert(0, selectedPage.content)
    }

    // Initialize edit title
    setEditTitle(selectedPage.title)

    return () => {
      // Cleanup on page change or unmount
      if (providerRef.current) {
        providerRef.current.destroy?.()
        providerRef.current = null
      }
      if (ydocRef.current) {
        ydocRef.current.destroy()
        ydocRef.current = null
      }
      ytextRef.current = null
    }
  }, [selectedPage])

  const loadPages = async () => {
    try {
      const data = await kanbanApi.listWiki(projectId)
      setPages(data)
    } catch (err) {
      toast.error('Failed to load wiki pages')
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePage = async () => {
    const title = prompt('Page title:')
    if (!title) return

    try {
      const page = await kanbanApi.createWiki(projectId, title, '# ' + title)
      setPages([...pages, page])
      setSelectedPage(page)
      toast.success('Page created')
    } catch (err) {
      toast.error('Failed to create page')
    }
  }

  const handleSave = async () => {
    if (!selectedPage || !ytextRef.current) return

    try {
      const content = ytextRef.current.toString()
      const updatedPage = await kanbanApi.updateWiki(
        selectedPage.page_id,
        editTitle,
        content
      )

      // Update pages list
      setPages(pages.map(p => p.page_id === updatedPage.page_id ? updatedPage : p))
      setSelectedPage(updatedPage)
      toast.success('Page saved')
    } catch (err) {
      toast.error('Failed to save page')
    }
  }

  // Use Y.Text binding hook
  const { value: content, onChange: onContentChange } = useYTextBinding(ytextRef.current)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[80vh] flex"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sidebar */}
        <div className="w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Wiki Pages</h3>
            <button
              onClick={handleCreatePage}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <Plus size={18} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {pages.map(page => (
              <button
                key={page.page_id}
                onClick={() => setSelectedPage(page)}
                className={`w-full p-3 text-left rounded-lg mb-1 flex items-center gap-2 ${
                  selectedPage?.page_id === page.page_id
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                }`}
              >
                <FileText size={16} />
                <span className="text-sm truncate">{page.title}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1">
              {selectedPage ? (
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="text-xl font-semibold text-gray-900 dark:text-gray-100 bg-transparent border-none outline-none focus:ring-0 px-0"
                  placeholder="Page title"
                />
              ) : (
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Select a page
                </h2>
              )}

              {/* Connection status */}
              {selectedPage && (
                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  {connected ? (
                    <>
                      <Wifi size={14} className="text-green-500" />
                      <span>Live</span>
                    </>
                  ) : (
                    <>
                      <WifiOff size={14} className="text-gray-400" />
                      <span>Offline</span>
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              {selectedPage && (
                <button
                  onClick={handleSave}
                  className="px-3 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center gap-2"
                >
                  <Save size={16} />
                  Save
                </button>
              )}
              <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                <X size={20} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {selectedPage ? (
              <textarea
                value={content}
                onChange={(e) => onContentChange(e.target.value)}
                className="w-full h-full min-h-[400px] p-4 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Start writing..."
              />
            ) : (
              <div className="text-center text-gray-500 dark:text-gray-400 mt-12">
                Select a page from the sidebar or create a new one
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
