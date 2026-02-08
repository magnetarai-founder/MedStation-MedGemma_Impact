//
//  TeamChatModals.swift
//  MagnetarStudio (macOS)
//
//  Team chat modal dialogs - Extracted from TeamWorkspace.swift
//

import SwiftUI

// MARK: - New Channel Dialog

struct NewChannelDialog: View {
    @Binding var isPresented: Bool
    @State private var channelName: String = ""
    @State private var description: String = ""
    @State private var isPrivate: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Create Channel")
                    .font(.system(size: 20, weight: .bold))

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 20))
                        .foregroundStyle(.secondary)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 16)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Body
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Channel Name")
                        .font(.system(size: 13, weight: .semibold))

                    HStack(spacing: 8) {
                        Text("#")
                            .font(.system(size: 14))
                            .foregroundStyle(.secondary)

                        TextField("e.g. project-updates", text: $channelName)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                    )
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Description (optional)")
                        .font(.system(size: 13, weight: .semibold))

                    TextEditor(text: $description)
                        .font(.system(size: 14))
                        .frame(height: 80)
                        .padding(8)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                }

                Toggle(isOn: $isPrivate) {
                    Text("Make private")
                        .font(.system(size: 14))
                }
                .toggleStyle(.switch)
            }
            .padding(24)

            // Footer
            HStack(spacing: 12) {
                Button {
                    isPresented = false
                } label: {
                    Text("Cancel")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(.primary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)

                Button {
                    // Create channel
                    isPresented = false
                } label: {
                    Text("Create")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(channelName.isEmpty ? Color.gray : Color.green)
                        )
                }
                .buttonStyle(.plain)
                .disabled(channelName.isEmpty)
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 16)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .top
            )
        }
        .frame(width: 540, height: 480)
        .background(Color(.windowBackgroundColor))
        .cornerRadius(12)
    }
}

// MARK: - P2P Peer Discovery Panel

struct PeerDiscoveryPanel: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("P2P Peer Discovery")
                .font(.title2)
            Text("Peer list will appear here")
                .foregroundStyle(.secondary)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

// MARK: - P2P File Sharing Panel

struct FileSharingPanel: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("P2P File Sharing")
                .font(.title2)
            Text("File sharing interface will appear here")
                .foregroundStyle(.secondary)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}
