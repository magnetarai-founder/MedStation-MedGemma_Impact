//
//  TeamCollabIndicator.swift
//  MagnetarStudio
//
//  Shows who's editing a document or spreadsheet in team mode.
//  Quip-style presence: colored dots, "X is editing" text,
//  section lock indicators.
//

import SwiftUI

// MARK: - Collaborator Presence

struct CollaboratorPresence: Identifiable, Equatable {
    let id: String
    let name: String
    let color: Color
    var isEditing: Bool
    var editingSection: String?

    var initials: String {
        let parts = name.split(separator: " ")
        if parts.count >= 2 {
            return String(parts[0].prefix(1) + parts[1].prefix(1)).uppercased()
        }
        return String(name.prefix(2)).uppercased()
    }
}

// MARK: - Team Collab Indicator

struct TeamCollabIndicator: View {
    let collaborators: [CollaboratorPresence]
    let documentTitle: String

    @AppStorage("workspace.teamEnabled") private var teamEnabled = false

    var body: some View {
        if teamEnabled && !collaborators.isEmpty {
            HStack(spacing: 8) {
                // Avatar stack (overlapping circles)
                avatarStack

                // Editing status
                editingStatus

                Spacer()

                // Lock indicator
                if hasLockedSections {
                    lockIndicator
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.surfaceTertiary.opacity(0.5))
        }
    }

    // MARK: - Avatar Stack

    private var avatarStack: some View {
        HStack(spacing: -6) {
            ForEach(collaborators.prefix(5)) { collab in
                CollabAvatar(collab: collab)
            }

            if collaborators.count > 5 {
                overflowAvatar
            }
        }
    }

    private var overflowAvatar: some View {
        Circle()
            .fill(Color.gray.opacity(0.2))
            .frame(width: 24, height: 24)
            .overlay(
                Text("+\(collaborators.count - 5)")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(.secondary)
            )
    }

    // MARK: - Editing Status

    private var editingStatus: some View {
        Group {
            let editors = collaborators.filter(\.isEditing)
            if editors.isEmpty {
                Text("\(collaborators.count) viewing")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            } else if editors.count == 1, let editor = editors.first {
                HStack(spacing: 4) {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 6, height: 6)
                    Text("\(editor.name) is editing")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                    if let section = editor.editingSection {
                        Text("(\(section))")
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }
                }
            } else {
                HStack(spacing: 4) {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 6, height: 6)
                    Text("\(editors.count) people editing")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    // MARK: - Lock Indicator

    private var hasLockedSections: Bool {
        collaborators.contains { $0.editingSection != nil }
    }

    private var lockIndicator: some View {
        HStack(spacing: 4) {
            Image(systemName: "lock.fill")
                .font(.system(size: 10))
                .foregroundStyle(.orange)

            let lockedSections = collaborators.compactMap(\.editingSection)
            Text("\(lockedSections.count) locked")
                .font(.system(size: 10))
                .foregroundStyle(.orange)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(Color.orange.opacity(0.1))
        )
    }
}

// MARK: - Section Lock Badge

/// Small inline badge showing a section is locked by a collaborator.
/// Place this next to section headers in docs/sheets.
struct SectionLockBadge: View {
    let lockedBy: String
    let color: Color

    var body: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)
            Text(lockedBy)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
            Image(systemName: "lock.fill")
                .font(.system(size: 8))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(
            RoundedRectangle(cornerRadius: 3)
                .fill(color.opacity(0.1))
        )
    }
}

// MARK: - Collaborator Avatar

private struct CollabAvatar: View {
    let collab: CollaboratorPresence

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            Circle()
                .fill(collab.color.opacity(0.2))
                .frame(width: 24, height: 24)
                .overlay(
                    Text(collab.initials)
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(collab.color)
                )
                .overlay(
                    Circle()
                        .stroke(Color(nsColor: .windowBackgroundColor), lineWidth: 2)
                )

            if collab.isEditing {
                Circle()
                    .fill(Color.green)
                    .frame(width: 8, height: 8)
                    .overlay(
                        Circle()
                            .stroke(Color(nsColor: .windowBackgroundColor), lineWidth: 1.5)
                    )
            }
        }
    }
}

// MARK: - Preview Helpers

extension TeamCollabIndicator {
    static var previewCollaborators: [CollaboratorPresence] {
        [
            CollaboratorPresence(id: "1", name: "Alice Smith", color: .blue, isEditing: true, editingSection: "Introduction"),
            CollaboratorPresence(id: "2", name: "Bob Jones", color: .purple, isEditing: false, editingSection: nil),
            CollaboratorPresence(id: "3", name: "Carol White", color: .orange, isEditing: true, editingSection: "Summary"),
        ]
    }
}
