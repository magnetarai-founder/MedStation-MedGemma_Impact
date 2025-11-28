//
//  SlackStyleDocsSidebar.swift
//  MagnetarStudio
//
//  Slack-inspired sidebar with collapsible sections
//

import SwiftUI

struct SlackStyleDocsSidebar: View {
    @Binding var activeDocument: TeamDocument?
    let documents: [TeamDocument]
    let onNewDocument: () -> Void

    @AppStorage("docs.sidebarOrganization") private var organizationMode: SidebarOrganizationMode = .byType
    @AppStorage("docs.collapsedSections") private var collapsedSectionsData: String = ""

    @State private var collapsedSections: Set<String> = []

    var body: some View {
        VStack(spacing: 0) {
            // Header
            sidebarHeader

            Divider()

            // Sections
            ScrollView {
                LazyVStack(spacing: 0, pinnedViews: .sectionHeaders) {
                    ForEach(organizedSections, id: \.id) { section in
                        sectionView(section)
                    }
                }
            }
        }
        .background(Color(nsColor: .controlBackgroundColor))
        .onAppear {
            loadCollapsedSections()
        }
    }

    // MARK: - Header

    private var sidebarHeader: some View {
        VStack(spacing: 12) {
            HStack(spacing: 8) {
                Text("Documents")
                    .font(.system(size: 14, weight: .semibold))

                Spacer()

                // Organization mode toggle
                Menu {
                    Button {
                        organizationMode = .byType
                    } label: {
                        Label("By Type", systemImage: organizationMode == .byType ? "checkmark" : "")
                    }

                    Button {
                        organizationMode = .byDate
                    } label: {
                        Label("By Date", systemImage: organizationMode == .byDate ? "checkmark" : "")
                    }

                    Button {
                        organizationMode = .alphabetical
                    } label: {
                        Label("Alphabetical", systemImage: organizationMode == .alphabetical ? "checkmark" : "")
                    }
                } label: {
                    Image(systemName: "line.3.horizontal.decrease.circle")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                }
                .menuStyle(.borderlessButton)
            }

            // New Document button
            Button {
                onNewDocument()
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "plus")
                        .font(.system(size: 14))
                    Text("New Document")
                        .font(.system(size: 13, weight: .medium))
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(LinearGradient.magnetarGradient)
                )
            }
            .buttonStyle(.plain)
        }
        .padding(12)
    }

    // MARK: - Section View

    private func sectionView(_ section: DocSection) -> some View {
        Section {
            if !isSectionCollapsed(section.id) {
                ForEach(section.documents) { doc in
                    documentRow(doc)
                }
            }
        } header: {
            sectionHeader(section)
        }
    }

    private func sectionHeader(_ section: DocSection) -> some View {
        Button {
            toggleSection(section.id)
        } label: {
            HStack(spacing: 6) {
                Image(systemName: isSectionCollapsed(section.id) ? "chevron.right" : "chevron.down")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 12)

                Image(systemName: section.icon)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)

                Text(section.title)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.secondary)

                Spacer()

                Text("\(section.documents.count)")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.gray.opacity(0.05))
        }
        .buttonStyle(.plain)
    }

    private func documentRow(_ doc: TeamDocument) -> some View {
        Button {
            activeDocument = doc
        } label: {
            HStack(spacing: 8) {
                // Document type icon
                Image(systemName: getDocumentIcon(doc.type))
                    .font(.system(size: 14))
                    .foregroundColor(activeDocument?.id == doc.id ? .white : .secondary)
                    .frame(width: 20)

                // Title
                VStack(alignment: .leading, spacing: 2) {
                    Text(doc.title)
                        .font(.system(size: 13))
                        .foregroundColor(activeDocument?.id == doc.id ? .white : .primary)
                        .lineLimit(1)

                    Text(formatDate(doc.updatedAt))
                        .font(.system(size: 10))
                        .foregroundColor(activeDocument?.id == doc.id ? .white.opacity(0.7) : .secondary)
                }

                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(
                activeDocument?.id == doc.id
                    ? AnyShapeStyle(LinearGradient.magnetarGradient)
                    : AnyShapeStyle(Color.clear)
            )
            .cornerRadius(6)
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
    }

    // MARK: - Helpers

    private var organizedSections: [DocSection] {
        switch organizationMode {
        case .byType:
            return groupByType()
        case .byDate:
            return groupByDate()
        case .alphabetical:
            return groupAlphabetically()
        }
    }

    private func groupByType() -> [DocSection] {
        let grouped = Dictionary(grouping: documents, by: { $0.type })
        return grouped.map { type, docs in
            DocSection(
                id: type,
                title: getTypeName(type),
                icon: getTypeIcon(type),
                documents: docs.sorted { $0.updatedAt > $1.updatedAt }
            )
        }.sorted { $0.title < $1.title }
    }

    private func groupByDate() -> [DocSection] {
        let calendar = Calendar.current
        let now = Date()

        let today = documents.filter {
            calendar.isDateInToday(parseDate($0.updatedAt))
        }

        let thisWeek = documents.filter {
            let date = parseDate($0.updatedAt)
            return !calendar.isDateInToday(date) && calendar.isDate(date, equalTo: now, toGranularity: .weekOfYear)
        }

        let older = documents.filter {
            let date = parseDate($0.updatedAt)
            return !calendar.isDateInToday(date) && !calendar.isDate(date, equalTo: now, toGranularity: .weekOfYear)
        }

        var sections: [DocSection] = []

        if !today.isEmpty {
            sections.append(DocSection(id: "today", title: "Today", icon: "clock", documents: today))
        }

        if !thisWeek.isEmpty {
            sections.append(DocSection(id: "thisWeek", title: "This Week", icon: "calendar", documents: thisWeek))
        }

        if !older.isEmpty {
            sections.append(DocSection(id: "older", title: "Older", icon: "calendar.badge.clock", documents: older))
        }

        return sections
    }

    private func groupAlphabetically() -> [DocSection] {
        let grouped = Dictionary(grouping: documents) { doc -> String in
            let firstChar = doc.title.first?.uppercased() ?? "#"
            return firstChar.rangeOfCharacter(from: .letters) != nil ? firstChar : "#"
        }

        return grouped.map { letter, docs in
            DocSection(
                id: letter,
                title: letter,
                icon: "character",
                documents: docs.sorted { $0.title < $1.title }
            )
        }.sorted { $0.title < $1.title }
    }

    private func isSectionCollapsed(_ id: String) -> Bool {
        collapsedSections.contains(id)
    }

    private func toggleSection(_ id: String) {
        if collapsedSections.contains(id) {
            collapsedSections.remove(id)
        } else {
            collapsedSections.insert(id)
        }
        saveCollapsedSections()
    }

    private func loadCollapsedSections() {
        if let data = collapsedSectionsData.data(using: .utf8),
           let sections = try? JSONDecoder().decode(Set<String>.self, from: data) {
            collapsedSections = sections
        }
    }

    private func saveCollapsedSections() {
        if let data = try? JSONEncoder().encode(collapsedSections),
           let string = String(data: data, encoding: .utf8) {
            collapsedSectionsData = string
        }
    }

    private func getTypeName(_ type: String) -> String {
        switch type {
        case "doc": return "Documents"
        case "sheet": return "Spreadsheets"
        case "insight": return "Insights"
        case "secure_doc": return "Secure Documents"
        default: return type.capitalized
        }
    }

    private func getTypeIcon(_ type: String) -> String {
        switch type {
        case "doc": return "doc.text"
        case "sheet": return "tablecells"
        case "insight": return "chart.line.uptrend.xyaxis"
        case "secure_doc": return "lock.doc"
        default: return "doc"
        }
    }

    private func getDocumentIcon(_ type: String) -> String {
        switch type {
        case "doc": return "doc.text"
        case "sheet": return "tablecells"
        case "insight": return "chart.line.uptrend.xyaxis"
        case "secure_doc": return "lock.doc"
        default: return "doc"
        }
    }

    private func formatDate(_ dateString: String) -> String {
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: dateString) else {
            return dateString
        }

        let relativeFormatter = RelativeDateTimeFormatter()
        relativeFormatter.unitsStyle = .short
        return relativeFormatter.localizedString(for: date, relativeTo: Date())
    }

    private func parseDate(_ dateString: String) -> Date {
        let formatter = ISO8601DateFormatter()
        return formatter.date(from: dateString) ?? Date()
    }
}

// MARK: - Supporting Types

struct DocSection: Identifiable {
    let id: String
    let title: String
    let icon: String
    let documents: [TeamDocument]
}

enum SidebarOrganizationMode: String {
    case byType
    case byDate
    case alphabetical
}

// MARK: - Preview

#Preview {
    SlackStyleDocsSidebar(
        activeDocument: .constant(nil),
        documents: [
            TeamDocument(id: "1", title: "Project Plan", content: nil, type: "doc", updatedAt: ISO8601DateFormatter().string(from: Date()), createdBy: "user1"),
            TeamDocument(id: "2", title: "Budget 2024", content: nil, type: "sheet", updatedAt: ISO8601DateFormatter().string(from: Date()), createdBy: "user1"),
            TeamDocument(id: "3", title: "Q4 Analytics", content: nil, type: "insight", updatedAt: ISO8601DateFormatter().string(from: Date()), createdBy: "user1")
        ],
        onNewDocument: {}
    )
    .frame(width: 256)
}
