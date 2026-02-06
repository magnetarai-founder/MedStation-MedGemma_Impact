//
//  ChannelView.swift
//  MagnetarStudio
//
//  Individual channel view — message history, thread replies, composer.
//  Used by TeamNotesPanel for channel-based communication.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ChannelView")

struct ChannelView: View {
    let channel: LocalChannel
    let messages: [LocalMessage]
    @Binding var messageText: String
    let onSend: () -> Void

    @State private var showChannelInfo = false

    var body: some View {
        VStack(spacing: 0) {
            // Channel header
            channelHeader

            Divider()

            // Messages
            messageList

            Divider()

            // Composer
            messageComposer
        }
        .background(Color.surfacePrimary)
    }

    // MARK: - Channel Header

    private var channelHeader: some View {
        HStack(spacing: 10) {
            // Channel icon + name
            HStack(spacing: 6) {
                Image(systemName: channel.isPrivate ? "lock.fill" : "number")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(.secondary)

                Text(channel.name)
                    .font(.system(size: 15, weight: .semibold))
            }

            if !channel.topic.isEmpty {
                Text("—")
                    .foregroundStyle(.quaternary)
                Text(channel.topic)
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer()

            // Channel info button
            Button {
                showChannelInfo.toggle()
            } label: {
                Image(systemName: "info.circle")
                    .font(.system(size: 14))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
            .popover(isPresented: $showChannelInfo, arrowEdge: .bottom) {
                channelInfoPopover
            }
        }
        .padding(.horizontal, 16)
        .frame(height: HubLayout.headerHeight)
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    private var channelInfoPopover: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 6) {
                Image(systemName: channel.isPrivate ? "lock.fill" : "number")
                    .foregroundStyle(.secondary)
                Text(channel.name)
                    .font(.system(size: 14, weight: .semibold))
            }

            if !channel.topic.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Topic")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(.secondary)
                    Text(channel.topic)
                        .font(.system(size: 13))
                }
            }

            Divider()

            HStack {
                Text("Created")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                Spacer()
                Text(channel.createdAt, style: .date)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }

            HStack {
                Text("Messages")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                Spacer()
                Text("\(messages.count)")
                    .font(.system(size: 11, weight: .medium))
            }
        }
        .padding(16)
        .frame(width: 260)
    }

    // MARK: - Message List

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    // Channel start marker
                    channelStartMarker
                        .padding(.bottom, 16)

                    // Group messages by date
                    ForEach(groupedMessages, id: \.date) { group in
                        dateDivider(group.date)

                        ForEach(group.messages) { message in
                            TeamMessageBubble(message: message)
                                .id(message.id)
                        }
                    }
                }
                .padding(16)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .onChange(of: messages.count) { _, _ in
                if let lastMsg = messages.last {
                    withAnimation(.easeOut(duration: 0.2)) {
                        proxy.scrollTo(lastMsg.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    private var channelStartMarker: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: channel.isPrivate ? "lock.fill" : "number")
                    .font(.system(size: 24))
                    .foregroundStyle(.secondary)
                Text(channel.name)
                    .font(.system(size: 20, weight: .bold))
            }

            Text("This is the start of #\(channel.name)")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)

            if !channel.topic.isEmpty {
                Text(channel.topic)
                    .font(.system(size: 13))
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.top, 12)
    }

    private func dateDivider(_ date: String) -> some View {
        HStack {
            VStack { Divider() }
            Text(date)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(.secondary)
                .padding(.horizontal, 12)
            VStack { Divider() }
        }
        .padding(.vertical, 8)
    }

    // MARK: - Message Composer

    private var messageComposer: some View {
        HStack(spacing: 10) {
            // Attach button
            Button {
                // File attachment
            } label: {
                Image(systemName: "plus.circle")
                    .font(.system(size: 18))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)

            // Text field
            TextField("Message #\(channel.name)...", text: $messageText)
                .textFieldStyle(.plain)
                .font(.system(size: 14))
                .onSubmit {
                    if !messageText.isEmpty { onSend() }
                }

            // Emoji button
            Button {
                // Emoji picker
            } label: {
                Image(systemName: "face.smiling")
                    .font(.system(size: 16))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)

            // Send button
            Button {
                if !messageText.isEmpty { onSend() }
            } label: {
                Image(systemName: "paperplane.fill")
                    .font(.system(size: 14))
                    .foregroundColor(messageText.isEmpty ? .gray : Color.magnetarPrimary)
            }
            .buttonStyle(.plain)
            .disabled(messageText.isEmpty)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    // MARK: - Message Grouping

    private struct MessageGroup: Identifiable {
        var id: String { date }
        let date: String
        let messages: [LocalMessage]
    }

    private var groupedMessages: [MessageGroup] {
        let formatter = DateFormatter()
        formatter.doesRelativeDateFormatting = true
        formatter.dateStyle = .medium
        formatter.timeStyle = .none

        let grouped = Dictionary(grouping: messages) { msg in
            formatter.string(from: msg.timestamp)
        }

        return grouped.map { MessageGroup(date: $0.key, messages: $0.value) }
            .sorted { ($0.messages.first?.timestamp ?? .distantPast) < ($1.messages.first?.timestamp ?? .distantPast) }
    }
}

// MARK: - Team Message Bubble

struct TeamMessageBubble: View {
    let message: LocalMessage

    @State private var isHovered = false

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            // Avatar
            Circle()
                .fill(avatarColor.opacity(0.15))
                .frame(width: 36, height: 36)
                .overlay(
                    Text(String(message.senderName.prefix(1)).uppercased())
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(avatarColor)
                )

            VStack(alignment: .leading, spacing: 3) {
                // Author + time
                HStack(spacing: 8) {
                    Text(message.senderName)
                        .font(.system(size: 13, weight: .semibold))

                    Text(formatTime(message.timestamp))
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)

                    if message.isEdited {
                        Text("(edited)")
                            .font(.system(size: 10))
                            .foregroundStyle(.quaternary)
                    }
                }

                // Content
                Text(message.content)
                    .font(.system(size: 14))
                    .foregroundStyle(.primary)
                    .textSelection(.enabled)
            }

            Spacer()

            // Hover actions
            if isHovered {
                HStack(spacing: 2) {
                    messageActionButton("face.smiling")
                    messageActionButton("arrowshape.turn.up.left")
                    messageActionButton("doc.on.doc")
                }
                .padding(2)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.surfaceTertiary)
                        .shadow(color: .black.opacity(0.1), radius: 2, y: 1)
                )
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isHovered ? Color.white.opacity(0.03) : Color.clear)
        )
        .onHover { isHovered = $0 }
    }

    private func messageActionButton(_ icon: String) -> some View {
        Button {} label: {
            Image(systemName: icon)
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
                .frame(width: 26, height: 26)
        }
        .buttonStyle(.plain)
    }

    private var avatarColor: Color {
        let colors: [Color] = [.blue, .purple, .orange, .green, .pink, .cyan, .indigo]
        let hash = abs(message.senderName.hashValue)
        return colors[hash % colors.count]
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: date)
    }
}
