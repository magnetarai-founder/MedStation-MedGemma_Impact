//
//  TeamChatMessageInput.swift
//  MagnetarStudio (macOS)
//
//  Message input with attachments - Extracted from TeamChatComponents.swift (Phase 6.13)
//

import SwiftUI

struct TeamChatMessageInput: View {
    @Binding var messageInput: String
    let onSend: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            Divider()

            HStack(spacing: 12) {
                TextField("Type a message...", text: $messageInput)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))
                    .onSubmit {
                        onSend()
                    }

                HStack(spacing: 8) {
                    Button {
                        // Attach file
                    } label: {
                        Image(systemName: "paperclip")
                            .font(.system(size: 16))
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)

                    Button {
                        // Emoji picker
                    } label: {
                        Image(systemName: "face.smiling")
                            .font(.system(size: 16))
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)

                    Button {
                        onSend()
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 24))
                            .foregroundColor(messageInput.isEmpty ? .gray : Color.magnetarPrimary)
                    }
                    .buttonStyle(.plain)
                    .disabled(messageInput.isEmpty)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }
}
