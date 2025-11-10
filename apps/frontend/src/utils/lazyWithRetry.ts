/**
 * Lazy load components with automatic retry on failure
 *
 * Fixes the "Failed to fetch dynamically imported module" error
 * that can occur during development or when cached modules are stale.
 */

import { ComponentType, lazy } from 'react';

interface RetryOptions {
  maxRetries?: number;
  delay?: number;
}

/**
 * Lazy load a component with retry logic
 *
 * @param componentImport - Function that returns a dynamic import promise
 * @param options - Retry configuration options
 * @returns Lazy-loaded component
 */
export function lazyWithRetry<T extends ComponentType<any>>(
  componentImport: () => Promise<{ default: T } | any>,
  options: RetryOptions = {}
) {
  const { maxRetries = 3, delay = 1000 } = options;

  return lazy(async () => {
    let lastError: any;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const module = await componentImport();
        return module;
      } catch (error: any) {
        lastError = error;

        // Check if this is a chunk loading error
        const isChunkError =
          error?.message?.includes('Failed to fetch') ||
          error?.message?.includes('dynamically imported module') ||
          error?.name === 'ChunkLoadError';

        if (isChunkError && attempt < maxRetries) {
          console.warn(
            `Failed to load module (attempt ${attempt + 1}/${maxRetries + 1}). Retrying in ${delay}ms...`,
            error
          );

          // Wait before retrying
          await new Promise(resolve => setTimeout(resolve, delay));

          // On first retry, try reloading the page to clear any stale cache
          if (attempt === 0 && typeof window !== 'undefined') {
            // Clear the module from the cache if possible
            if ('caches' in window) {
              caches.keys().then(names => {
                names.forEach(name => caches.delete(name));
              });
            }
          }
        } else {
          throw error;
        }
      }
    }

    // If all retries failed, throw the last error
    console.error(
      `Failed to load module after ${maxRetries + 1} attempts. You may need to refresh the page.`,
      lastError
    );
    throw lastError;
  });
}

/**
 * Helper to create a lazy-loaded component with named export
 *
 * @param importFn - Import function
 * @param exportName - Name of the export
 * @returns Lazy-loaded component
 */
export function lazyNamed<T extends ComponentType<any>>(
  importFn: () => Promise<any>,
  exportName: string,
  options?: RetryOptions
) {
  return lazyWithRetry(
    () => importFn().then(m => ({ default: m[exportName] })),
    options
  );
}
