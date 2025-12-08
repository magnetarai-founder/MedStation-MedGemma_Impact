/**
 * LibraryModal - Backwards Compatibility Shim
 *
 * This file maintains backwards compatibility by re-exporting the new modular LibraryModal.
 * All logic has been refactored into LibraryModal/ directory.
 *
 * @deprecated Import from './LibraryModal/' instead
 */

export { LibraryModal } from './LibraryModal/LibraryModal'
export type { LibraryModalProps } from './LibraryModal/LibraryModal'
