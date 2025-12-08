/**
 * Client-side audit logging utility
 *
 * Sends audit events to backend non-blockingly
 */

export const auditLog = async (
  action: string,
  details?: Record<string, any>,
  resourceId?: string
): Promise<void> => {
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) return // Not authenticated, skip audit

    // Non-blocking fire-and-forget
    fetch('/api/v1/audit/log', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action,
        resource_id: resourceId,
        details
      })
    }).catch(err => {
      // Silent failure - audit is best-effort
      console.debug('Audit log failed:', err)
    })
  } catch (error) {
    // Silent failure
    console.debug('Audit log error:', error)
  }
}

export const AuditAction = {
  TOKEN_NEAR_LIMIT_WARNING: 'session.token.near_limit',
  SUMMARIZE_CONTEXT_INVOKED: 'session.summarize.invoked',
} as const
