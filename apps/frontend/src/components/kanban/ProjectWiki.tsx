import { useState, useEffect } from 'react'
import { X, Plus, FileText } from 'lucide-react'
import toast from 'react-hot-toast'
import * as kanbanApi from '@/lib/kanbanApi'
import type { WikiItem } from '@/lib/kanbanApi'

interface ProjectWikiProps {
  projectId: string
  onClose: () => void
}

export function ProjectWiki({ projectId, onClose }: ProjectWikiProps) {
  const [pages, setPages] = useState<WikiItem[]>([])
  const [selectedPage, setSelectedPage] = useState<WikiItem | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPages()
  }, [projectId])

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
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {selectedPage?.title || 'Select a page'}
            </h2>
            <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
              <X size={20} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {selectedPage ? (
              <div className="prose dark:prose-invert max-w-none">
                <pre className="whitespace-pre-wrap text-sm">{selectedPage.content}</pre>
              </div>
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
