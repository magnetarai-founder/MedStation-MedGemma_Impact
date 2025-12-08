import * as Y from 'yjs'

/**
 * Operation descriptor for moving a task between columns
 */
export interface MoveOp {
  taskId: string
  fromColumnId: string
  toColumnId: string
  fromIndex: number
  toIndex: number
}

/**
 * Neighbor hints for backend position calculation
 */
export interface NeighborHints {
  before_task_id: string | undefined
  after_task_id: string | undefined
}

/**
 * Apply an optimistic move to Yjs column arrays and return a rollback function.
 *
 * Handles same-column and cross-column moves with proper index adjustment.
 *
 * @param yColumns Y.Map mapping column_id → Y.Array of task_ids
 * @param op Move operation descriptor
 * @returns rollback function to revert the change
 */
export function applyMoveWithRollback(
  yColumns: Y.Map<Y.Array<string>>,
  op: MoveOp
): () => void {
  const { taskId, fromColumnId, toColumnId, fromIndex, toIndex } = op

  const fromArray = yColumns.get(fromColumnId)
  const toArray = yColumns.get(toColumnId)

  if (!fromArray || !toArray) {
    console.warn('Column arrays not found in Y.Doc')
    return () => {} // no-op rollback
  }

  const isSameColumn = fromColumnId === toColumnId

  // Apply the move
  fromArray.delete(fromIndex, 1)

  // Adjust target index if moving down within same column
  const insertIndex = isSameColumn && toIndex > fromIndex ? toIndex - 1 : toIndex
  toArray.insert(insertIndex, [taskId])

  // Return rollback function
  return () => {
    // Remove from destination
    const currentToArray = yColumns.get(toColumnId)
    if (currentToArray) {
      const currentIndex = currentToArray.toArray().indexOf(taskId)
      if (currentIndex !== -1) {
        currentToArray.delete(currentIndex, 1)
      }
    }

    // Re-insert at original position
    const currentFromArray = yColumns.get(fromColumnId)
    if (currentFromArray) {
      currentFromArray.insert(fromIndex, [taskId])
    }
  }
}

/**
 * Get neighbor hints for a task at its current position in a column.
 *
 * @param yColumns Y.Map mapping column_id → Y.Array of task_ids
 * @param columnId Column containing the task
 * @param taskId Task to get neighbors for
 * @returns before/after task IDs for position calculation
 */
export function neighborHintsForTask(
  yColumns: Y.Map<Y.Array<string>>,
  columnId: string,
  taskId: string
): NeighborHints {
  const array = yColumns.get(columnId)
  if (!array) {
    return { before_task_id: undefined, after_task_id: undefined }
  }

  const tasks = array.toArray()
  const index = tasks.indexOf(taskId)

  if (index === -1) {
    return { before_task_id: undefined, after_task_id: undefined }
  }

  return {
    before_task_id: index > 0 ? tasks[index - 1] : undefined,
    after_task_id: index < tasks.length - 1 ? tasks[index + 1] : undefined
  }
}

/**
 * Convenience function: apply move and get neighbor hints in one call.
 *
 * @param yColumns Y.Map mapping column_id → Y.Array of task_ids
 * @param op Move operation descriptor
 * @returns rollback function and neighbor hints for backend persistence
 */
export function applyMoveAndGetHints(
  yColumns: Y.Map<Y.Array<string>>,
  op: MoveOp
): { rollback: () => void; hints: NeighborHints } {
  const rollback = applyMoveWithRollback(yColumns, op)
  const hints = neighborHintsForTask(yColumns, op.toColumnId, op.taskId)

  return { rollback, hints }
}

/**
 * Initialize column arrays from REST data if Y.Doc is empty.
 *
 * @param yColumns Y.Map to populate
 * @param columns Array of column definitions
 * @param tasks Array of tasks to distribute by column_id and position
 */
export function seedYColumnsFromREST(
  yColumns: Y.Map<Y.Array<string>>,
  columns: Array<{ column_id: string }>,
  tasks: Array<{ task_id: string; column_id: string; position: number }>
): void {
  // Only seed if empty
  if (yColumns.size > 0) return

  columns.forEach(col => {
    const columnTasks = tasks
      .filter(t => t.column_id === col.column_id)
      .sort((a, b) => a.position - b.position)
      .map(t => t.task_id)

    const yArray = new Y.Array<string>()
    yArray.push(columnTasks)
    yColumns.set(col.column_id, yArray)
  })
}
