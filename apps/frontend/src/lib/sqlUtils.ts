/**
 * SQL Utility Functions for matching and normalization
 */

/**
 * Normalize SQL for exact matching
 * - Removes comments
 * - Collapses whitespace
 * - Converts to lowercase
 * - Removes trailing semicolons
 */
export function normalizeSQL(sql: string): string {
  return sql
    // Remove single-line comments (-- comment)
    .replace(/--.*$/gm, '')
    // Remove multi-line comments (/* comment */)
    .replace(/\/\*[\s\S]*?\*\//g, '')
    // Collapse all whitespace to single spaces
    .replace(/\s+/g, ' ')
    // Trim
    .trim()
    // Remove trailing semicolon
    .replace(/;+$/, '')
    // Lowercase for comparison
    .toLowerCase()
}

/**
 * Check if two SQL queries are exactly the same (ignoring formatting)
 */
export function isSQLExactMatch(sql1: string, sql2: string): boolean {
  return normalizeSQL(sql1) === normalizeSQL(sql2)
}

/**
 * Find exact match in library queries
 */
export function findExactMatch(currentSQL: string, libraryQueries: Array<{id: number, name: string, query: string}>): {id: number, name: string} | null {
  const normalizedCurrent = normalizeSQL(currentSQL)

  if (!normalizedCurrent) return null

  const match = libraryQueries.find(q =>
    normalizeSQL(q.query) === normalizedCurrent
  )

  return match ? { id: match.id, name: match.name } : null
}
