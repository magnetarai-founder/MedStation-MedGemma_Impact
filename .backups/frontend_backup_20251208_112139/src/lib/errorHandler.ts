/**
 * Frontend Error Handler for ElohimOS
 * Handles structured error responses from the backend API
 */

import { toast } from 'react-hot-toast';

/**
 * Structured error response from backend
 */
export interface AppError {
  error_code: string;
  error_id: string;
  message: string;
  suggestion: string;
  technical?: string;
  context?: Record<string, any>;
}

/**
 * Error notification options
 */
export interface ErrorNotificationOptions {
  type?: 'error' | 'warning' | 'info';
  duration?: number;
  showCode?: boolean;
  showSuggestion?: boolean;
}

/**
 * Handle API error responses and display user-friendly notifications
 *
 * @param error - Axios error object or Error instance
 * @param options - Notification customization options
 */
export function handleApiError(
  error: any,
  options: ErrorNotificationOptions = {}
): void {
  const {
    type = 'error',
    duration = 6000,
    showCode = true,
    showSuggestion = true
  } = options;

  // Extract structured error from response
  const appError: AppError = extractAppError(error);

  // Build notification message
  let message = appError.message;

  if (showSuggestion && appError.suggestion) {
    message += `\n\n${appError.suggestion}`;
  }

  if (showCode && appError.error_code) {
    message += `\n\n(Error Code: ${appError.error_code})`;
  }

  // Log technical details to console in development
  if (import.meta.env.DEV) {
    console.group(`[${appError.error_code}] ${appError.error_id}`);
    console.error('Message:', appError.message);
    console.error('Suggestion:', appError.suggestion);
    if (appError.technical) {
      console.error('Technical:', appError.technical);
    }
    if (appError.context) {
      console.error('Context:', appError.context);
    }
    console.error('Original Error:', error);
    console.groupEnd();
  }

  // Show notification
  if (type === 'error') {
    toast.error(message, { duration });
  } else if (type === 'warning') {
    toast(message, { icon: '⚠️', duration });
  } else {
    toast(message, { icon: 'ℹ️', duration });
  }
}

/**
 * Extract AppError from various error formats
 */
function extractAppError(error: any): AppError {
  // Structured API error from backend
  if (error.response?.data?.error_code) {
    return error.response.data as AppError;
  }

  // Axios error with detail field (legacy format)
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;

    // If detail is already an AppError object
    if (typeof detail === 'object' && detail.error_code) {
      return detail as AppError;
    }

    // Legacy string detail
    return {
      error_code: getErrorCodeFromStatus(error.response.status),
      error_id: 'unknown',
      message: typeof detail === 'string' ? detail : 'An error occurred',
      suggestion: getDefaultSuggestion(error.response.status)
    };
  }

  // Network error (no response)
  if (error.request && !error.response) {
    return {
      error_code: 'ERR-6001',
      error_id: 'network-error',
      message: 'Network connection failed',
      suggestion: 'Check your internet connection and try again.'
    };
  }

  // Generic error
  return {
    error_code: 'ERR-9002',
    error_id: 'unknown',
    message: error.message || 'An unexpected error occurred',
    suggestion: 'Please try again. If the problem persists, contact support.'
  };
}

/**
 * Map HTTP status codes to generic error codes
 */
function getErrorCodeFromStatus(status: number): string {
  const statusMap: Record<number, string> = {
    400: 'ERR-9006', // SYSTEM_INVALID_REQUEST
    401: 'ERR-1001', // AUTH_INVALID_CREDENTIALS
    403: 'ERR-1003', // AUTH_INSUFFICIENT_PERMISSIONS
    404: 'ERR-4004', // DB_RECORD_NOT_FOUND
    409: 'ERR-4005', // DB_DUPLICATE_ENTRY
    422: 'ERR-9007', // SYSTEM_VALIDATION_FAILED
    429: 'ERR-1004', // AUTH_RATE_LIMIT_EXCEEDED
    500: 'ERR-9002', // SYSTEM_INTERNAL_ERROR
    503: 'ERR-9004', // SYSTEM_MAINTENANCE_MODE
  };

  return statusMap[status] || 'ERR-9002';
}

/**
 * Get default suggestion based on HTTP status code
 */
function getDefaultSuggestion(status: number): string {
  const suggestionMap: Record<number, string> = {
    400: 'Check the data you entered and try again.',
    401: 'Please log in again to continue.',
    403: 'You don\'t have permission to perform this action.',
    404: 'The requested resource was not found.',
    429: 'Too many requests. Please wait a moment and try again.',
    500: 'A server error occurred. Please try again later.',
    503: 'The service is temporarily unavailable. Please try again later.',
  };

  return suggestionMap[status] || 'Please try again or contact support.';
}

/**
 * Handle specific error codes with custom behavior
 */
export function handleSpecificError(error: any): boolean {
  const appError = extractAppError(error);

  // Handle session expiration
  if (appError.error_code === 'ERR-1002' || appError.error_code === 'ERR-1009') {
    toast.error('Your session has expired. Please log in again.');
    // Redirect to login (customize based on your routing)
    window.location.href = '/login';
    return true;
  }

  // Handle panic mode
  if (appError.error_code === 'ERR-8007') {
    toast.error(appError.message, { duration: 10000 });
    return true;
  }

  // Handle rate limiting with retry countdown
  if (appError.error_code === 'ERR-1004') {
    const retryAfter = appError.context?.retry_after || 60;
    toast.error(`${appError.message}\n\nRetry in ${retryAfter} seconds.`, {
      duration: Math.min(retryAfter * 1000, 10000)
    });
    return true;
  }

  return false;
}

/**
 * Wrapper for async operations with automatic error handling
 *
 * @param operation - Async function to execute
 * @param options - Error handling options
 * @returns Promise that resolves to the operation result or null on error
 */
export async function withErrorHandling<T>(
  operation: () => Promise<T>,
  options: ErrorNotificationOptions = {}
): Promise<T | null> {
  try {
    return await operation();
  } catch (error) {
    // Try specific error handlers first
    if (!handleSpecificError(error)) {
      // Fall back to generic error handling
      handleApiError(error, options);
    }
    return null;
  }
}

/**
 * Create a custom error notification
 *
 * @param message - Error message
 * @param suggestion - Suggestion for fixing the error
 * @param errorCode - Optional error code
 */
export function showErrorNotification(
  message: string,
  suggestion?: string,
  errorCode?: string
): void {
  let fullMessage = message;

  if (suggestion) {
    fullMessage += `\n\n${suggestion}`;
  }

  if (errorCode) {
    fullMessage += `\n\n(Error Code: ${errorCode})`;
  }

  toast.error(fullMessage, { duration: 6000 });
}

/**
 * Check if error is a specific error code
 */
export function isErrorCode(error: any, code: string): boolean {
  const appError = extractAppError(error);
  return appError.error_code === code;
}

/**
 * Get user-friendly error message from error object
 */
export function getErrorMessage(error: any): string {
  const appError = extractAppError(error);
  return appError.message;
}

/**
 * Get error suggestion from error object
 */
export function getErrorSuggestion(error: any): string {
  const appError = extractAppError(error);
  return appError.suggestion;
}
