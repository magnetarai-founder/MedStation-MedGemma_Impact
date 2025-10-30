import toast, { Toast } from 'react-hot-toast'

/**
 * Centralized toast notification system for ElohimOS
 * Provides consistent styling and behavior across the app
 */

// Standard toast helpers
export const showToast = {
  success: (message: string, duration: number = 3000) => {
    return toast.success(message, {
      duration,
      style: {
        background: 'rgba(16, 185, 129, 0.1)',
        color: '#059669',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        padding: '16px',
        borderRadius: '12px',
      },
      iconTheme: {
        primary: '#059669',
        secondary: '#fff',
      },
    })
  },

  error: (message: string, duration: number = 4000) => {
    return toast.error(message, {
      duration,
      style: {
        background: 'rgba(239, 68, 68, 0.1)',
        color: '#dc2626',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        padding: '16px',
        borderRadius: '12px',
      },
      iconTheme: {
        primary: '#dc2626',
        secondary: '#fff',
      },
    })
  },

  info: (message: string, duration: number = 3000) => {
    return toast(message, {
      duration,
      icon: 'ℹ️',
      style: {
        background: 'rgba(59, 130, 246, 0.1)',
        color: '#2563eb',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        padding: '16px',
        borderRadius: '12px',
      },
    })
  },

  warning: (message: string, duration: number = 3500) => {
    return toast(message, {
      duration,
      icon: '⚠️',
      style: {
        background: 'rgba(245, 158, 11, 0.1)',
        color: '#d97706',
        border: '1px solid rgba(245, 158, 11, 0.3)',
        padding: '16px',
        borderRadius: '12px',
      },
    })
  },

  loading: (message: string) => {
    return toast.loading(message, {
      style: {
        background: 'rgba(156, 163, 175, 0.1)',
        color: '#6b7280',
        border: '1px solid rgba(156, 163, 175, 0.3)',
        padding: '16px',
        borderRadius: '12px',
      },
    })
  },

  // Promise-based toast (auto-updates on resolve/reject)
  promise: <T,>(
    promise: Promise<T>,
    messages: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((err: any) => string)
    }
  ) => {
    return toast.promise(promise, messages, {
      style: {
        padding: '16px',
        borderRadius: '12px',
      },
    })
  },

  // Dismiss a specific toast
  dismiss: (toastId?: string) => {
    toast.dismiss(toastId)
  },

  // Dismiss all toasts
  dismissAll: () => {
    toast.dismiss()
  },
}

/**
 * Toast with undo action (5-second timeout by default)
 * Useful for reversible actions like delete, archive, etc.
 */
export const showUndoToast = (
  message: string,
  onUndo: () => void | Promise<void>,
  options: {
    duration?: number
    undoText?: string
  } = {}
) => {
  const { duration = 5000, undoText = 'Undo' } = options

  return toast.success(
    (t) => (
      <div className="flex items-center gap-4 justify-between min-w-[280px]">
        <span className="text-sm font-medium">{message}</span>
        <button
          onClick={async () => {
            toast.dismiss(t.id)
            try {
              await onUndo()
              showToast.success('Action undone')
            } catch (error) {
              showToast.error('Failed to undo action')
            }
          }}
          className="px-3 py-1 text-sm font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline transition-colors"
        >
          {undoText}
        </button>
      </div>
    ),
    {
      duration,
      style: {
        background: 'rgba(16, 185, 129, 0.1)',
        color: '#059669',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        padding: '12px 16px',
        borderRadius: '12px',
      },
      icon: '✓',
    }
  )
}

/**
 * Toast with custom action button
 * For actions that aren't undo (e.g., "View", "Open", "Retry")
 */
export const showActionToast = (
  message: string,
  actionText: string,
  onAction: () => void | Promise<void>,
  options: {
    type?: 'success' | 'info' | 'warning' | 'error'
    duration?: number
  } = {}
) => {
  const { type = 'info', duration = 4000 } = options

  const typeStyles = {
    success: {
      background: 'rgba(16, 185, 129, 0.1)',
      color: '#059669',
      border: '1px solid rgba(16, 185, 129, 0.3)',
      icon: '✓',
    },
    info: {
      background: 'rgba(59, 130, 246, 0.1)',
      color: '#2563eb',
      border: '1px solid rgba(59, 130, 246, 0.3)',
      icon: 'ℹ️',
    },
    warning: {
      background: 'rgba(245, 158, 11, 0.1)',
      color: '#d97706',
      border: '1px solid rgba(245, 158, 11, 0.3)',
      icon: '⚠️',
    },
    error: {
      background: 'rgba(239, 68, 68, 0.1)',
      color: '#dc2626',
      border: '1px solid rgba(239, 68, 68, 0.3)',
      icon: '✕',
    },
  }

  const style = typeStyles[type]

  return toast(
    (t) => (
      <div className="flex items-center gap-4 justify-between min-w-[280px]">
        <span className="text-sm font-medium">{message}</span>
        <button
          onClick={async () => {
            toast.dismiss(t.id)
            try {
              await onAction()
            } catch (error) {
              showToast.error('Action failed')
            }
          }}
          className="px-3 py-1 text-sm font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline transition-colors"
        >
          {actionText}
        </button>
      </div>
    ),
    {
      duration,
      icon: style.icon,
      style: {
        background: style.background,
        color: style.color,
        border: style.border,
        padding: '12px 16px',
        borderRadius: '12px',
      },
    }
  )
}

/**
 * Chat notification toast (for new messages)
 * Shows sender name and preview of message
 */
export const showChatNotification = (
  sender: string,
  messagePreview: string,
  onView?: () => void
) => {
  return toast(
    (t) => (
      <div className="flex flex-col gap-1 min-w-[300px]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">
            {sender}
          </span>
          <span className="text-xs text-gray-500">sent a message</span>
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
          {messagePreview}
        </p>
        {onView && (
          <button
            onClick={() => {
              toast.dismiss(t.id)
              onView()
            }}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline self-start mt-1"
          >
            View message →
          </button>
        )}
      </div>
    ),
    {
      duration: 5000,
      icon: '💬',
      style: {
        background: 'rgba(59, 130, 246, 0.1)',
        color: '#2563eb',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        padding: '12px 16px',
        borderRadius: '12px',
      },
    }
  )
}

/**
 * Workflow notification toast (for automation updates)
 */
export const showWorkflowNotification = (
  workflowName: string,
  status: 'started' | 'completed' | 'failed',
  onView?: () => void
) => {
  const statusConfig = {
    started: {
      icon: '▶️',
      color: '#2563eb',
      background: 'rgba(59, 130, 246, 0.1)',
      border: '1px solid rgba(59, 130, 246, 0.3)',
      message: 'Workflow started',
    },
    completed: {
      icon: '✅',
      color: '#059669',
      background: 'rgba(16, 185, 129, 0.1)',
      border: '1px solid rgba(16, 185, 129, 0.3)',
      message: 'Workflow completed',
    },
    failed: {
      icon: '❌',
      color: '#dc2626',
      background: 'rgba(239, 68, 68, 0.1)',
      border: '1px solid rgba(239, 68, 68, 0.3)',
      message: 'Workflow failed',
    },
  }

  const config = statusConfig[status]

  return toast(
    (t) => (
      <div className="flex flex-col gap-1 min-w-[280px]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold">{config.message}</span>
        </div>
        <p className="text-sm font-medium">{workflowName}</p>
        {onView && (
          <button
            onClick={() => {
              toast.dismiss(t.id)
              onView()
            }}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline self-start mt-1"
          >
            View details →
          </button>
        )}
      </div>
    ),
    {
      duration: 4000,
      icon: config.icon,
      style: {
        background: config.background,
        color: config.color,
        border: config.border,
        padding: '12px 16px',
        borderRadius: '12px',
      },
    }
  )
}

/**
 * Backup notification toast
 */
export const showBackupNotification = (
  type: 'started' | 'completed' | 'failed',
  onRestore?: () => void
) => {
  const config = {
    started: {
      icon: '💾',
      message: 'Backup in progress...',
      type: 'loading' as const,
    },
    completed: {
      icon: '✅',
      message: 'Backup completed successfully',
      type: 'success' as const,
    },
    failed: {
      icon: '❌',
      message: 'Backup failed',
      type: 'error' as const,
    },
  }

  const { icon, message, type: toastType } = config[type]

  if (type === 'completed' && onRestore) {
    return showActionToast(message, 'Restore', onRestore, { type: toastType })
  }

  if (toastType === 'loading') {
    return showToast.loading(message)
  }

  return showToast[toastType](message)
}
