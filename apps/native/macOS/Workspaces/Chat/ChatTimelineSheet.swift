//
//  ChatTimelineSheet.swift
//  MagnetarStudio (macOS)
//
//  Chat timeline modal - Extracted from ChatWorkspace.swift (Phase 6.17)
//

import SwiftUI

struct ChatTimelineSheet: View {
    let session: ChatSession?
    let messages: [ChatMessage]  // Messages from ChatStore (session.messages may be empty)
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            timelineHeader
            Divider()
            timelineContent
        }
        .frame(width: 500, height: 600)
    }

    private var timelineHeader: some View {
        HStack {
            Text("Session Timeline")
                .font(.system(size: 18, weight: .bold))
            Spacer()
            Button("Done") {
                dismiss()
            }
            .buttonStyle(.bordered)
        }
        .padding(20)
    }

    @ViewBuilder
    private var timelineContent: some View {
        if let session = session {
            SessionTimelineDetails(session: session, messages: messages)
        } else {
            emptyTimelineView
        }
    }

    private var emptyTimelineView: some View {
        VStack(spacing: 16) {
            Image(systemName: "clock")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("No session selected")
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

private struct SessionTimelineDetails: View {
    let session: ChatSession
    let messages: [ChatMessage]  // Use messages from ChatStore, not session.messages

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                sessionInfoCard
                if !messages.isEmpty {
                    messageHistoryList
                }
            }
            .padding(20)
        }
    }

    private var sessionInfoCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Session Details", systemImage: "info.circle")
                .font(.system(size: 14, weight: .semibold))

            InfoRow(label: "Title:", value: session.title)
            InfoRow(label: "Mode:", value: "Multi-model")  // Sessions use orchestrator per-query

            HStack {
                Text("Created:")
                    .foregroundStyle(.secondary)
                Text(session.createdAt, style: .date)
                Text(session.createdAt, style: .time)
            }
            .font(.system(size: 13))

            InfoRow(label: "Messages:", value: "\(messages.count)")
        }
        .padding(16)
        .background(Color.surfaceSecondary.opacity(0.3))
        .cornerRadius(10)
    }

    private var messageHistoryList: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Message History", systemImage: "clock.arrow.circlepath")
                .font(.system(size: 14, weight: .semibold))

            ForEach(Array(messages.enumerated()), id: \.element.id) { index, message in
                TimelineMessageRow(index: index, message: message)
            }
        }
    }
}

private struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)
            Text(value)
        }
        .font(.system(size: 13))
    }
}

private struct TimelineMessageRow: View {
    let index: Int
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Text("#\(index + 1)")
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(.secondary)
                .frame(width: 30, alignment: .leading)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(message.role.displayName)
                        .font(.system(size: 12, weight: .semibold))
                    Spacer()
                    Text(message.createdAt, style: .time)
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }

                Text(message.content)
                    .font(.system(size: 12))
                    .lineLimit(3)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(12)
        .background(Color.surfaceSecondary.opacity(0.2))
        .cornerRadius(8)
    }
}
