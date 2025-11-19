/**
 * ProjectLibraryModal - Backwards Compatibility Shim
 *
 * This file maintains backwards compatibility by re-exporting the new modular ProjectLibraryModal.
 * All logic has been refactored into ProjectLibraryModal/ directory.
 *
 * @deprecated Import from './ProjectLibraryModal/' instead
 */

export { ProjectLibraryModal } from './ProjectLibraryModal/ProjectLibraryModal'
export type { ProjectLibraryModalProps } from './ProjectLibraryModal/ProjectLibraryModal'
export type { ProjectDocument } from './ProjectLibraryModal/types'
