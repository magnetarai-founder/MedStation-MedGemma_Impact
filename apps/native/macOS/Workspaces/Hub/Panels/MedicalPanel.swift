//
//  MedicalPanel.swift
//  MedStation
//
//  Medical workspace panel for patient intake and MedGemma-powered agentic workflows.
//  Displays case list, intake details, workflow progress, and structured results.
//
//  MedGemma Impact Challenge (Kaggle 2026).
//

import SwiftUI
import UniformTypeIdentifiers
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "MedicalPanel")

// MARK: - Medical Panel

struct MedicalPanel: View {
    @State private var cases: [MedicalCase] = []
    @State private var selectedCaseID: UUID?
    @State private var isLoading = true
    @State private var showCheckInFlow = false
    @State private var searchText = ""
    @FocusState private var isSearchFocused: Bool
    @AppStorage("medical.onboarding.shown") private var hasShownOnboarding = false
    @State private var showOnboarding = false
    @State private var showBenchmark = false
    @State private var benchmarkHarness = MedicalBenchmarkHarness()
    @State private var showAnalytics = false
    @State private var sidebarFilter: SidebarFilter = .active

    private enum SidebarFilter: String, CaseIterable {
        case active = "All Messages"
        case archived = "Archived"
        case deleted = "Recently Deleted"

        var icon: String {
            switch self {
            case .active: return "tray.full"
            case .archived: return "archivebox"
            case .deleted: return "trash"
            }
        }
    }

    var body: some View {
        HStack(spacing: 0) {
            casesSidebar
                .frame(width: 280)

            Divider()

            if let caseID = selectedCaseID,
               let caseIndex = cases.firstIndex(where: { $0.id == caseID }) {
                MedicalCaseDetailView(
                    medicalCase: $cases[caseIndex],
                    onUpdate: { saveCaseToFile($0) }
                )
            } else {
                EmptyState(
                    icon: "cross.case",
                    title: "Select a Case",
                    message: "Choose a medical case from the sidebar or create a new one",
                    action: { showCheckInFlow = true },
                    actionLabel: "New Case"
                )
            }
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                HStack(spacing: 8) {
                    Button {
                        showBenchmark = true
                    } label: {
                        Label("Benchmark", systemImage: "chart.bar.doc.horizontal")
                    }
                    .accessibilityLabel("Run evaluation benchmark")

                    Button {
                        showCheckInFlow = true
                    } label: {
                        Label("New Case", systemImage: "plus.circle.fill")
                    }
                    .accessibilityLabel("Create new medical case")
                }
            }
        }
        .sheet(isPresented: $showCheckInFlow) {
            PatientCheckInFlow { completedCase in
                addCompletedCase(completedCase)
            }
        }
        .sheet(isPresented: $showBenchmark) {
            BenchmarkSheet(harness: benchmarkHarness)
        }
        .task {
            await loadCases()
            if !hasShownOnboarding {
                try? await Task.sleep(for: .seconds(0.5))
                showOnboarding = true
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .focusPanelSearch)) { _ in
            isSearchFocused = true
        }
        .alert("MedGemma Medical Assistant", isPresented: $showOnboarding) {
            Button("Get Started") {
                hasShownOnboarding = true
                // Auto-select the demo case so the user sees it immediately
                if let demoCase = cases.first(where: { $0.intake.patientId == "DEMO-001" }) {
                    selectedCaseID = demoCase.id
                }
            }
        } message: {
            Text("""
            Welcome to the AI-powered medical triage assistant.

            \u{2022} Enter patient symptoms and vital signs
            \u{2022} AI performs 5-step clinical reasoning (MedGemma 4B)
            \u{2022} Outputs triage level, differential diagnoses, and recommendations
            \u{2022} HAI-DEF compliant safety validation and audit logging
            \u{2022} 100% on-device inference — no patient data leaves your Mac

            Try the demo case to see the full workflow in action.
            """)
        }
    }

    // MARK: - Sidebar

    private var filteredCases: [MedicalCase] {
        let byStatus = cases.filter { medicalCase in
            switch sidebarFilter {
            case .active:
                return medicalCase.status != .archived && medicalCase.status != .deleted
            case .archived:
                return medicalCase.status == .archived
            case .deleted:
                return medicalCase.status == .deleted
            }
        }
        guard !searchText.isEmpty else { return byStatus }
        let query = searchText.lowercased()
        return byStatus.filter {
            $0.intake.patientId.lowercased().contains(query) ||
            $0.intake.chiefComplaint.lowercased().contains(query) ||
            $0.intake.symptoms.contains(where: { $0.lowercased().contains(query) })
        }
    }

    private func countForFilter(_ filter: SidebarFilter) -> Int {
        cases.filter { medicalCase in
            switch filter {
            case .active:
                return medicalCase.status != .archived && medicalCase.status != .deleted
            case .archived:
                return medicalCase.status == .archived
            case .deleted:
                return medicalCase.status == .deleted
            }
        }.count
    }

    private var casesSidebar: some View {
        VStack(spacing: 0) {
            HStack(spacing: 6) {
                Text(sidebarFilter.rawValue)
                    .font(.headline)
                Spacer()

                Menu {
                    ForEach(SidebarFilter.allCases, id: \.self) { filter in
                        Button {
                            sidebarFilter = filter
                        } label: {
                            Label {
                                Text("\(filter.rawValue) (\(countForFilter(filter)))")
                            } icon: {
                                Image(systemName: filter.icon)
                            }
                        }
                        .disabled(sidebarFilter == filter)
                    }
                } label: {
                    Image(systemName: sidebarFilter == .active
                          ? "line.3.horizontal.decrease.circle"
                          : "line.3.horizontal.decrease.circle.fill")
                        .font(.system(size: 14))
                        .foregroundStyle(sidebarFilter == .active ? Color.secondary : Color.accentColor)
                }
                .menuStyle(.borderlessButton)
                .menuIndicator(.hidden)
                .frame(width: 24)
                .help("Filter cases")
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.tertiary)
                    .accessibilityHidden(true)
                TextField("Search cases...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                    .focused($isSearchFocused)
                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Clear search")
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)

            Divider()

            if isLoading {
                ProgressView()
                    .frame(maxHeight: .infinity)
            } else if filteredCases.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: emptyStateIcon)
                        .font(.system(size: 40))
                        .foregroundStyle(.tertiary)
                        .accessibilityHidden(true)
                    Text(emptyStateTitle)
                        .font(.headline)
                        .foregroundStyle(.secondary)
                    Text(emptyStateMessage)
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                        .multilineTextAlignment(.center)

                    if sidebarFilter == .deleted {
                        Text("Deleted cases can be restored or permanently removed.")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }
                }
                .frame(maxHeight: .infinity)
                .padding(.horizontal, 16)
            } else {
                ScrollView {
                    LazyVStack(spacing: 1) {
                        ForEach(filteredCases) { medicalCase in
                            CaseListItem(
                                medicalCase: medicalCase,
                                isSelected: selectedCaseID == medicalCase.id,
                                onSelect: { selectedCaseID = medicalCase.id }
                            )
                            .contextMenu {
                                contextMenuItems(for: medicalCase)
                            }
                        }
                    }
                }
            }

            // Impact Analytics
            if !cases.isEmpty {
                Divider()
                impactAnalyticsSection
            }
        }
        .background(Color(NSColor.controlBackgroundColor))
    }

    // MARK: - Impact Analytics

    private var impactAnalyticsSection: some View {
        VStack(spacing: 0) {
            Button {
                withAnimation(.easeInOut(duration: 0.15)) { showAnalytics.toggle() }
            } label: {
                HStack {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 9, weight: .bold))
                        .rotationEffect(.degrees(showAnalytics ? 90 : 0))
                    Text("Impact Analytics")
                    Spacer()
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .font(.system(size: 11, weight: .medium))
            .foregroundStyle(.secondary)

            if showAnalytics {
                let completedCases = cases.filter { $0.result != nil }
                let emergencyCount = completedCases.filter { $0.result?.triageLevel == .emergency }.count
                let times = completedCases.compactMap { $0.result?.performanceMetrics?.totalWorkflowMs }
                let avgTriageMs = times.isEmpty ? 0.0 : times.reduce(0, +) / Double(times.count)
                let feedbackCases = cases.compactMap(\.feedback)
                let accuratePct: Double = feedbackCases.isEmpty ? 0 :
                    Double(feedbackCases.filter { $0.rating == .accurate }.count) / Double(feedbackCases.count) * 100

                VStack(spacing: 6) {
                    analyticsRow("Cases Analyzed", "\(completedCases.count)")
                    analyticsRow("Emergency Detected", "\(emergencyCount)")
                    analyticsRow("Avg Triage Time", avgTriageMs > 0 ? String(format: "%.1fs", avgTriageMs / 1000) : "—")
                    if !feedbackCases.isEmpty {
                        analyticsRow("Feedback Accuracy", String(format: "%.0f%%", accuratePct))
                    }
                }
                .padding(.top, 6)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }

    private func analyticsRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)
            Spacer()
            Text(value)
                .font(.system(size: 10, weight: .semibold).monospaced())
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Data

    private func loadCases() async {
        defer { isLoading = false }

        let dir = Self.storageDirectory
        let files: [URL]
        do {
            files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
                .filter { $0.pathExtension == "json" }
        } catch {
            logger.error("Failed to list medical cases: \(error.localizedDescription)")
            return
        }

        var loaded: [MedicalCase] = []
        for file in files {
            if let mc = PersistenceHelpers.load(MedicalCase.self, from: file, label: "medical case") {
                loaded.append(mc)
            }
        }

        if loaded.isEmpty {
            let demoIntake = PatientIntake(
                patientId: "DEMO-001",
                age: 58,
                sex: .male,
                chiefComplaint: "Severe chest pain radiating to left arm, onset 20 minutes ago",
                symptoms: ["chest pain", "shortness of breath", "nausea", "diaphoresis"],
                onsetTime: "20 minutes ago",
                severity: .severe,
                vitalSigns: VitalSigns(
                    heartRate: 110,
                    bloodPressure: "150/95",
                    temperature: 98.6,
                    respiratoryRate: 22,
                    oxygenSaturation: 94,
                    weight: 195,
                    height: 70
                ),
                medicalHistory: ["Hypertension", "Type 2 Diabetes"],
                currentMedications: ["Metformin", "Lisinopril"],
                allergies: ["Penicillin"]
            )
            let demoCase = MedicalCase(intake: demoIntake)
            loaded.append(demoCase)
            saveCaseToFile(demoCase)
            logger.info("Created demo medical case for first launch")
        }

        cases = loaded.sorted { $0.updatedAt > $1.updatedAt }
        logger.info("Loaded \(loaded.count) medical cases")
    }

    private func createNewCase(intake: PatientIntake) {
        let newCase = MedicalCase(intake: intake)
        cases.insert(newCase, at: 0)
        selectedCaseID = newCase.id
        saveCaseToFile(newCase)
        showCheckInFlow = false
    }

    private func addCompletedCase(_ medicalCase: MedicalCase) {
        cases.insert(medicalCase, at: 0)
        selectedCaseID = medicalCase.id
        saveCaseToFile(medicalCase)
        showCheckInFlow = false
    }

    private func saveCaseToFile(_ medicalCase: MedicalCase) {
        var updated = medicalCase
        updated.updatedAt = Date()

        if let index = cases.firstIndex(where: { $0.id == medicalCase.id }) {
            cases[index] = updated
        }

        let file = Self.storageDirectory.appendingPathComponent("\(medicalCase.id.uuidString).json")
        PersistenceHelpers.save(updated, to: file, label: "medical case")
    }

    private var emptyStateIcon: String {
        switch sidebarFilter {
        case .active: return "cross.case"
        case .archived: return "archivebox"
        case .deleted: return "trash"
        }
    }

    private var emptyStateTitle: String {
        switch sidebarFilter {
        case .active: return "No Cases"
        case .archived: return "No Archived Cases"
        case .deleted: return "Trash Is Empty"
        }
    }

    private var emptyStateMessage: String {
        switch sidebarFilter {
        case .active: return "Create your first medical case"
        case .archived: return "Archived cases will appear here"
        case .deleted: return "Deleted cases will appear here"
        }
    }

    @ViewBuilder
    private func contextMenuItems(for medicalCase: MedicalCase) -> some View {
        switch medicalCase.status {
        case .pending, .analyzing, .completed:
            Button {
                archiveCase(medicalCase.id)
            } label: {
                Label("Archive", systemImage: "archivebox")
            }
            Button(role: .destructive) {
                softDeleteCase(medicalCase.id)
            } label: {
                Label("Delete", systemImage: "trash")
            }
        case .archived:
            Button {
                restoreCase(medicalCase.id)
            } label: {
                Label("Move to Active", systemImage: "tray.and.arrow.up")
            }
            Button(role: .destructive) {
                softDeleteCase(medicalCase.id)
            } label: {
                Label("Delete", systemImage: "trash")
            }
        case .deleted:
            Button {
                restoreCase(medicalCase.id)
            } label: {
                Label("Restore", systemImage: "arrow.uturn.backward")
            }
            Button(role: .destructive) {
                permanentlyDeleteCase(medicalCase.id)
            } label: {
                Label("Delete Forever", systemImage: "trash.slash")
            }
        }
    }

    private func archiveCase(_ id: UUID) {
        guard let index = cases.firstIndex(where: { $0.id == id }) else { return }
        cases[index].status = .archived
        saveCaseToFile(cases[index])
        if selectedCaseID == id { selectedCaseID = nil }
        logger.info("Archived medical case \(id.uuidString.prefix(8))")
    }

    private func softDeleteCase(_ id: UUID) {
        guard let index = cases.firstIndex(where: { $0.id == id }) else { return }
        cases[index].status = .deleted
        saveCaseToFile(cases[index])
        if selectedCaseID == id { selectedCaseID = nil }
        logger.info("Soft-deleted medical case \(id.uuidString.prefix(8))")
    }

    private func restoreCase(_ id: UUID) {
        guard let index = cases.firstIndex(where: { $0.id == id }) else { return }
        cases[index].status = cases[index].result != nil ? .completed : .pending
        saveCaseToFile(cases[index])
        logger.info("Restored medical case \(id.uuidString.prefix(8))")
    }

    private func permanentlyDeleteCase(_ id: UUID) {
        let file = Self.storageDirectory.appendingPathComponent("\(id.uuidString).json")
        PersistenceHelpers.remove(at: file, label: "medical case")
        cases.removeAll { $0.id == id }
        if selectedCaseID == id { selectedCaseID = nil }
        logger.info("Permanently deleted medical case \(id.uuidString.prefix(8))")
    }

    private static var storageDirectory: URL {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MedStation/workspace/medical", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "medical cases storage")
        return dir
    }
}

// MARK: - Case List Item

private struct CaseListItem: View {
    let medicalCase: MedicalCase
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(medicalCase.intake.patientId.isEmpty ? "Anonymous" : medicalCase.intake.patientId)
                        .font(.system(size: 13, weight: .medium))
                        .lineLimit(1)

                    Spacer()

                    Text(medicalCase.status.rawValue)
                        .font(.system(size: 9, weight: .semibold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(statusColor.opacity(0.2))
                        .foregroundStyle(statusColor)
                        .clipShape(Capsule())
                        .accessibilityLabel("Status: \(medicalCase.status.rawValue)")
                }

                Text(medicalCase.intake.chiefComplaint)
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
                    .lineLimit(2)

                HStack {
                    Image(systemName: "calendar")
                        .font(.system(size: 10))
                        .accessibilityHidden(true)
                    Text(medicalCase.createdAt, style: .date)
                        .font(.system(size: 10))

                    Spacer()

                    if let result = medicalCase.result {
                        triagePill(result.triageLevel)
                            .accessibilityLabel("Triage level: \(triageShort(result.triageLevel))")
                    }
                }
                .foregroundStyle(.tertiary)
                .accessibilityElement(children: .combine)
            }
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(isSelected ? Color.accentColor.opacity(0.1) : Color.clear)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private var statusColor: Color {
        switch medicalCase.status {
        case .pending: return .orange
        case .analyzing: return .blue
        case .completed: return .green
        case .archived: return .gray
        case .deleted: return .red
        }
    }

    private func triagePill(_ level: MedicalWorkflowResult.TriageLevel) -> some View {
        HStack(spacing: 3) {
            Circle()
                .fill(triageColor(level))
                .frame(width: 6, height: 6)
            Text(triageShort(level))
                .font(.system(size: 9, weight: .medium))
        }
    }
}

// MARK: - Case Detail View

private struct MedicalCaseDetailView: View {
    @Binding var medicalCase: MedicalCase
    let onUpdate: (MedicalCase) -> Void

    @State private var aiService = MedicalAIService.shared
    @State private var isRunningWorkflow = false
    @State private var currentStep: ReasoningStep?
    @State private var workflowError: String?
    @State private var showDisclaimerConfirm = false
    @State private var exportError: String?

    // Follow-up Q&A chat (persisted via MedicalCase.followUpMessages)
    @State private var chatMessages: [FollowUpMessage] = []
    @State private var chatInput = ""
    @State private var isChatStreaming = false
    @State private var showChat = false

    var body: some View {
        HStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    headerSection
                    Divider()
                    intakeSection

                    if medicalCase.result == nil && !isRunningWorkflow {
                        Divider()
                        runWorkflowSection
                    }

                    if isRunningWorkflow {
                        Divider()
                        progressSection
                    }

                    if let result = medicalCase.result {
                        Divider()
                        resultsSection(result)
                        Divider()
                        feedbackSection
                    }
                }
                .padding(20)
            }

            if showChat {
                Divider()
                followUpChatPane
                    .frame(width: 360)
                    .transition(.move(edge: .trailing).combined(with: .opacity))
            }
        }
        .animation(.easeInOut(duration: 0.2), value: showChat)
        .onAppear {
            chatMessages = medicalCase.followUpMessages
        }
        .alert("Medical Disclaimer", isPresented: $showDisclaimerConfirm) {
            Button("I Understand — Run Analysis") {
                Task { await runWorkflow() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This AI analysis is for educational and informational purposes only. It is NOT a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider.")
        }
        .alert("Export Error", isPresented: Binding(get: { exportError != nil }, set: { if !$0 { exportError = nil } })) {
            Button("OK") { exportError = nil }
        } message: {
            Text(exportError ?? "Unknown error")
        }
    }

    // MARK: - Header

    private var headerSection: some View {
        HStack {
            Image(systemName: "cross.case.fill")
                .font(.title)
                .foregroundStyle(LinearGradient.medstationGradient)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 2) {
                Text("Patient: \(medicalCase.intake.patientId.isEmpty ? "Anonymous" : medicalCase.intake.patientId)")
                    .font(.title2.weight(.semibold))

                Text("Case \(medicalCase.id.uuidString.prefix(8))")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            Spacer()

            if let result = medicalCase.result {
                Button {
                    showChat.toggle()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: showChat ? "bubble.left.and.bubble.right.fill" : "bubble.left.and.bubble.right")
                            .font(.system(size: 12))
                        Text("AI Chat")
                            .font(.system(size: 12, weight: .medium))
                        if !chatMessages.isEmpty {
                            Text("\(chatMessages.count)")
                                .font(.system(size: 9, weight: .bold).monospaced())
                                .foregroundStyle(.white)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Capsule().fill(Color.purple))
                        }
                    }
                    .foregroundStyle(showChat ? .purple : .secondary)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(showChat ? "Close AI chat" : "Open AI chat")

                Menu {
                    Button {
                        exportMedicalReport(result)
                    } label: {
                        Label("Export as Text Report", systemImage: "doc.plaintext")
                    }
                    Button {
                        exportClinicalJSON(result)
                    } label: {
                        Label("Export as Clinical JSON", systemImage: "curlybraces")
                    }
                    Button {
                        exportFHIRBundle(result)
                    } label: {
                        Label("Export as FHIR R4 Bundle", systemImage: "heart.text.clipboard")
                    }
                } label: {
                    Label("Export", systemImage: "arrow.up.doc")
                        .font(.caption)
                }
                .menuStyle(.borderlessButton)
                .fixedSize()
                .accessibilityLabel("Export medical report")

                triageBadge(result.triageLevel)
                    .accessibilityLabel("Triage level: \(result.triageLevel.rawValue)")
            }
        }
    }

    // MARK: - Intake

    private var intakeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Patient Intake")
                .font(.headline)

            infoRow("Chief Complaint", medicalCase.intake.chiefComplaint)
            infoRow("Onset", medicalCase.intake.onsetTime)
            infoRow("Severity", medicalCase.intake.severity.rawValue)

            if !medicalCase.intake.symptoms.isEmpty {
                infoRow("Symptoms", medicalCase.intake.symptoms.joined(separator: ", "))
            }

            if let vitals = medicalCase.intake.vitalSigns {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Vital Signs")
                        .font(.subheadline.weight(.medium))
                    if let w = vitals.weight { infoRow("Weight", String(format: "%.0f lbs", w)) }
                    if let h = vitals.height { infoRow("Height", String(format: "%.0f in", h)) }
                    if let bp = vitals.bloodPressure { infoRow("Blood Pressure", bp) }
                    if let hr = vitals.heartRate { infoRow("Heart Rate", "\(hr) BPM") }
                    if let temp = vitals.temperature { infoRow("Temperature", String(format: "%.1f°F", temp)) }
                    if let spo2 = vitals.oxygenSaturation { infoRow("Pulse Ox", "\(spo2)%") }
                }
            }

            if !medicalCase.intake.medicalHistory.isEmpty {
                infoRow("Medical History", medicalCase.intake.medicalHistory.joined(separator: ", "))
            }
            if !medicalCase.intake.currentMedications.isEmpty {
                infoRow("Medications", medicalCase.intake.currentMedications.joined(separator: ", "))
            }
            if !medicalCase.intake.allergies.isEmpty {
                infoRow("Allergies", medicalCase.intake.allergies.joined(separator: ", "))
            }

            if !medicalCase.intake.attachedImagePaths.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Attached Images (\(medicalCase.intake.attachedImagePaths.count))")
                        .font(.subheadline.weight(.medium))

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(medicalCase.intake.attachedImagePaths, id: \.self) { path in
                                if let img = NSImage(contentsOfFile: path) {
                                    Image(nsImage: img)
                                        .resizable()
                                        .aspectRatio(contentMode: .fill)
                                        .frame(width: 60, height: 60)
                                        .clipShape(RoundedRectangle(cornerRadius: 6))
                                } else {
                                    RoundedRectangle(cornerRadius: 6)
                                        .fill(Color.gray.opacity(0.2))
                                        .frame(width: 60, height: 60)
                                        .overlay {
                                            Image(systemName: "photo")
                                                .foregroundStyle(.tertiary)
                                                .accessibilityHidden(true)
                                        }
                                }
                            }
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: - Run Workflow

    private var runWorkflowSection: some View {
        VStack(spacing: 12) {
            Button {
                showDisclaimerConfirm = true
            } label: {
                HStack {
                    Image(systemName: "wand.and.stars")
                    Text("Run Medical Analysis")
                        .font(.headline)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(LinearGradient.medstationGradient)
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Run MedGemma medical analysis workflow")

            if case .loading = aiService.modelStatus {
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Loading MedGemma 1.5 4B into memory...")
                        .font(.caption)
                }
                .padding(8)
                .background(Color.blue.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            } else if case .failed(let msg) = aiService.modelStatus {
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                            .accessibilityHidden(true)
                        Text("Model error: \(msg)")
                            .font(.caption)
                    }

                    VStack(alignment: .leading, spacing: 6) {
                        Text("Troubleshooting")
                            .font(.caption.weight(.semibold))
                        Text("MedGemma 1.5 4B runs locally via HuggingFace Transformers:")
                            .font(.caption2)
                            .foregroundStyle(.secondary)

                        VStack(alignment: .leading, spacing: 3) {
                            setupStep("1", "Ensure the backend is running (auto-starts with app)")
                            setupStep("2", "Model weights must be in .models/medgemma-1.5-4b-it/")
                            setupStep("3", "Requires 16 GB RAM (bfloat16 on Apple Silicon)")
                        }

                        Button {
                            Task { await aiService.ensureModelReady() }
                        } label: {
                            Label("Retry", systemImage: "arrow.clockwise")
                                .font(.caption)
                        }
                        .accessibilityLabel("Retry model loading")
                    }
                    .padding(8)
                    .background(Color(NSColor.controlBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }
                .padding(8)
                .background(Color.orange.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            } else if case .unknown = aiService.modelStatus {
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Image(systemName: "brain")
                            .foregroundStyle(.blue)
                            .accessibilityHidden(true)
                        Text("MedGemma 1.5 4B — on-device medical AI")
                            .font(.caption)
                    }
                    Text("Click 'Run Medical Analysis' to load the model and start inference (~8 GB, Apple Silicon MPS).")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .padding(8)
                .background(Color.blue.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            }

            if let error = workflowError {
                VStack(spacing: 8) {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.red)
                            .accessibilityHidden(true)
                        Text("Error: \(error)")
                            .font(.caption)
                        Spacer()
                    }

                    Button {
                        workflowError = nil
                        Task { await runWorkflow() }
                    } label: {
                        Label("Retry Analysis", systemImage: "arrow.clockwise")
                            .font(.caption)
                            .frame(maxWidth: .infinity)
                            .padding(6)
                            .background(Color.blue.opacity(0.1))
                            .foregroundStyle(.blue)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Retry medical analysis")
                }
                .padding(8)
                .background(Color.red.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            }
        }
    }

    // MARK: - Progress

    private var progressSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                ProgressView()
                    .scaleEffect(0.8)
                Text("Running Medical Analysis...")
                    .font(.headline)
            }

            if let step = currentStep {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("Step \(step.step) of 5:")
                            .font(.caption.weight(.semibold))
                        Text(step.title)
                            .font(.caption)
                    }
                    .foregroundStyle(.secondary)

                    Text(String(step.content.prefix(300)))
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                .padding(8)
                .background(Color(NSColor.controlBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            }
        }
        .padding()
        .background(Color.blue.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: - Follow-Up Chat

    // MARK: - Feedback (HAI-DEF user feedback loop)

    @State private var feedbackNotes = ""

    private var feedbackSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: "hand.thumbsup")
                    .foregroundStyle(.green)
                    .accessibilityHidden(true)
                Text("Triage Feedback")
                    .font(.headline)
            }

            if let feedback = medicalCase.feedback {
                HStack(spacing: 8) {
                    Image(systemName: feedback.rating == .accurate ? "checkmark.circle.fill" : feedback.rating == .incorrect ? "xmark.circle.fill" : "minus.circle.fill")
                        .foregroundStyle(feedback.rating == .accurate ? Color.green : feedback.rating == .incorrect ? Color.red : Color.orange)
                        .accessibilityHidden(true)
                    Text("Rated: \(feedback.rating.rawValue)")
                        .font(.subheadline)
                    if !feedback.notes.isEmpty {
                        Text("— \(feedback.notes)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text("Thank you for your feedback")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            } else {
                Text("Was this triage assessment helpful? Your feedback improves future accuracy.")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                HStack(spacing: 8) {
                    ForEach(TriageFeedback.FeedbackRating.allCases, id: \.self) { rating in
                        Button {
                            medicalCase.feedback = TriageFeedback(rating: rating, notes: feedbackNotes)
                            onUpdate(medicalCase)
                        } label: {
                            Text(rating.rawValue)
                                .font(.caption)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(feedbackColor(rating).opacity(0.1))
                                .foregroundStyle(feedbackColor(rating))
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Rate as \(rating.rawValue)")
                    }
                }

                TextField("Optional notes...", text: $feedbackNotes)
                    .textFieldStyle(.roundedBorder)
                    .font(.caption)
                    .accessibilityLabel("Feedback notes")
            }
        }
        .padding()
        .background(Color.green.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.green.opacity(0.15), lineWidth: 1)
        )
    }

    private func feedbackColor(_ rating: TriageFeedback.FeedbackRating) -> Color {
        switch rating {
        case .accurate: return .green
        case .partiallyHelpful: return .orange
        case .incorrect: return .red
        }
    }

    // MARK: - Follow-Up Chat Pane

    private var followUpChatPane: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 8) {
                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .font(.system(size: 13))
                    .foregroundStyle(.purple)
                    .accessibilityHidden(true)

                Text("AI Chat")
                    .font(.system(size: 14, weight: .semibold))

                Text("MedGemma 4B")
                    .font(.system(size: 9, weight: .medium))
                    .foregroundStyle(.purple.opacity(0.8))
                    .padding(.horizontal, 5)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(Color.purple.opacity(0.1)))

                Spacer()

                if isChatStreaming {
                    Button {
                        aiService.cancel()
                        isChatStreaming = false
                    } label: {
                        HStack(spacing: 4) {
                            ProgressView()
                                .controlSize(.mini)
                            Text("Stop")
                                .font(.system(size: 11, weight: .medium))
                        }
                        .foregroundStyle(.red)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Stop generating response")
                }

                Button {
                    showChat = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(.secondary)
                        .frame(width: 22, height: 22)
                        .background(Color.gray.opacity(0.1))
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Close chat pane")
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)

            Divider()

            // Scrollable messages area
            ScrollViewReader { proxy in
                ScrollView {
                    if chatMessages.isEmpty {
                        VStack(spacing: 12) {
                            Spacer(minLength: 40)
                            Image(systemName: "bubble.left.and.text.bubble.right")
                                .font(.system(size: 36))
                                .foregroundStyle(.purple.opacity(0.2))
                                .accessibilityHidden(true)
                            Text("Ask about the diagnosis")
                                .font(.system(size: 13, weight: .medium))
                                .foregroundStyle(.secondary)
                            Text("Treatment options, next steps,\nmedication concerns, or anything else")
                                .font(.system(size: 11))
                                .foregroundStyle(.tertiary)
                                .multilineTextAlignment(.center)
                            Spacer(minLength: 40)
                        }
                        .frame(maxWidth: .infinity)
                    } else {
                        LazyVStack(alignment: .leading, spacing: 0) {
                            ForEach(Array(chatMessages.enumerated()), id: \.offset) { index, msg in
                                followUpMessageRow(msg, isLast: index == chatMessages.count - 1)
                                    .id(index)
                            }
                        }
                        .padding(.vertical, 8)
                    }
                }
                .onChange(of: chatMessages.count) {
                    if let last = chatMessages.indices.last {
                        withAnimation(.easeOut(duration: 0.15)) {
                            proxy.scrollTo(last, anchor: .bottom)
                        }
                    }
                }
            }

            Divider()

            // Pinned input bar
            VStack(spacing: 6) {
                HStack(spacing: 10) {
                    TextField("Ask a question...", text: $chatInput)
                        .textFieldStyle(.plain)
                        .font(.system(size: 13))
                        .onSubmit { Task { await sendChatMessage() } }
                        .disabled(isChatStreaming)
                        .accessibilityLabel("Follow-up question")

                    Button {
                        Task { await sendChatMessage() }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 22))
                            .foregroundStyle(
                                chatInput.trimmingCharacters(in: .whitespaces).isEmpty || isChatStreaming
                                ? .gray : .purple
                            )
                    }
                    .buttonStyle(.plain)
                    .disabled(chatInput.trimmingCharacters(in: .whitespaces).isEmpty || isChatStreaming)
                    .accessibilityLabel("Send question")
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 8)

                Text("MedGemma on-device · Not medical advice")
                    .font(.system(size: 9))
                    .foregroundStyle(.tertiary)
                    .padding(.bottom, 6)
            }
        }
        .background(Color(NSColor.controlBackgroundColor))
    }

    @State private var hoveredMessageIndex: Int?

    private func followUpMessageRow(_ msg: FollowUpMessage, isLast: Bool) -> some View {
        let isUser = msg.role == "user"
        let index = chatMessages.firstIndex(where: { $0 == msg })

        return HStack(alignment: .top, spacing: 12) {
            // Avatar
            Circle()
                .fill(isUser ? Color.blue : Color.purple.opacity(0.15))
                .frame(width: 32, height: 32)
                .overlay(
                    Image(systemName: isUser ? "person.fill" : "sparkles")
                        .font(.system(size: 14))
                        .foregroundStyle(isUser ? .white : .purple)
                )

            // Content
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 8) {
                    Text(isUser ? "You" : "MedGemma")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(.secondary)

                    if !isUser {
                        Text("4B · on-device")
                            .font(.system(size: 9, weight: .medium))
                            .foregroundStyle(.purple.opacity(0.7))
                            .padding(.horizontal, 5)
                            .padding(.vertical, 1)
                            .background(Capsule().fill(Color.purple.opacity(0.08)))
                    }

                    Spacer()

                    // Copy on hover
                    if hoveredMessageIndex == index && !msg.content.isEmpty {
                        Button {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(msg.content, forType: .string)
                        } label: {
                            Image(systemName: "doc.on.doc")
                                .font(.system(size: 11))
                                .foregroundStyle(.secondary)
                                .frame(width: 22, height: 22)
                                .background(Color.gray.opacity(0.1))
                                .clipShape(RoundedRectangle(cornerRadius: 4))
                        }
                        .buttonStyle(.plain)
                        .help("Copy message")
                        .transition(.opacity)
                    }
                }

                if msg.content.isEmpty && isChatStreaming && isLast {
                    HStack(spacing: 4) {
                        ProgressView()
                            .controlSize(.mini)
                        Text("Thinking...")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                } else {
                    Text(msg.content)
                        .font(.system(size: 13))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(hoveredMessageIndex == index ? Color.gray.opacity(0.04) : Color.clear)
        )
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                hoveredMessageIndex = hovering ? index : nil
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(isUser ? "You" : "MedGemma"): \(msg.content)")
    }

    private func sendChatMessage() async {
        let question = chatInput.trimmingCharacters(in: .whitespaces)
        guard !question.isEmpty else { return }

        chatInput = ""
        chatMessages.append(FollowUpMessage(role: "user", content: question))

        // Build context from the case result
        var context = ""
        if let result = medicalCase.result {
            context = """
            Prior Analysis Summary:
            Triage: \(result.triageLevel.rawValue)
            Diagnoses: \(result.differentialDiagnoses.map(\.condition).joined(separator: ", "))
            """
        }

        isChatStreaming = true
        var streamedContent = ""
        chatMessages.append(FollowUpMessage(role: "assistant", content: ""))
        let responseIndex = chatMessages.count - 1

        do {
            try await aiService.streamMedicalResponse(
                prompt: question,
                patientContext: context,
                onToken: { token in
                    Task { @MainActor in
                        streamedContent += token
                        if responseIndex < chatMessages.count {
                            chatMessages[responseIndex] = FollowUpMessage(role: "assistant", content: streamedContent)
                        }
                    }
                },
                onDone: {
                    Task { @MainActor in
                        isChatStreaming = false
                        medicalCase.followUpMessages = chatMessages
                        onUpdate(medicalCase)
                    }
                }
            )
        } catch {
            chatMessages[responseIndex] = FollowUpMessage(role: "assistant", content: "Error: \(error.localizedDescription)")
            isChatStreaming = false
            medicalCase.followUpMessages = chatMessages
            onUpdate(medicalCase)
        }
    }

    // MARK: - Results

    private func resultsSection(_ result: MedicalWorkflowResult) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            // Safety Alerts (HAI-DEF compliance)
            if !result.safetyAlerts.isEmpty {
                safetyAlertsSection(result.safetyAlerts)
            }

            // Triage
            VStack(alignment: .leading, spacing: 8) {
                Text("Triage Assessment")
                    .font(.headline)

                Text(result.triageLevel.rawValue)
                    .font(.title3.weight(.medium))
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(triageBackgroundColor(result.triageLevel))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            // Differential Diagnoses
            VStack(alignment: .leading, spacing: 8) {
                Text("Differential Diagnosis")
                    .font(.headline)

                ForEach(result.differentialDiagnoses) { dx in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(dx.condition)
                                .font(.subheadline.weight(.medium))
                            Spacer()
                            Text(String(format: "%.0f%%", dx.probability * 100))
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)
                        }
                        if !dx.rationale.isEmpty {
                            Text(dx.rationale)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(10)
                    .background(Color(NSColor.controlBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                    .accessibilityElement(children: .combine)
                }
            }

            // Recommended Actions
            VStack(alignment: .leading, spacing: 8) {
                Text("Recommended Actions")
                    .font(.headline)

                ForEach(result.recommendedActions) { action in
                    HStack(spacing: 8) {
                        Circle()
                            .fill(priorityColor(action.priority))
                            .frame(width: 8, height: 8)
                            .accessibilityHidden(true)
                        Text(action.action)
                            .font(.subheadline)
                        Spacer()
                        Text(action.priority.rawValue)
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
                    .padding(10)
                    .background(Color(NSColor.controlBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                    .accessibilityElement(children: .combine)
                }
            }

            // Edge AI Performance Metrics
            if let metrics = result.performanceMetrics {
                edgeAIMetricsSection(metrics, steps: result.reasoning)
            }

            // Reasoning Steps
            DisclosureGroup("Clinical Reasoning (\(result.reasoning.count) steps)") {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(result.reasoning) { step in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text("Step \(step.step):")
                                    .font(.caption.weight(.semibold))
                                Text(step.title)
                                    .font(.caption.weight(.medium))
                                Spacer()
                                if step.durationMs > 0 {
                                    Text(formatDuration(step.durationMs))
                                        .font(.caption2.monospaced())
                                        .foregroundStyle(.blue)
                                }
                                Text(step.timestamp, style: .time)
                                    .font(.caption2)
                                    .foregroundStyle(.tertiary)
                            }
                            Text(step.content)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .padding(10)
                        .background(Color(NSColor.controlBackgroundColor))
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                }
                .padding(.top, 8)
            }
            .font(.headline)

            // HAI-DEF Audit Trail
            if let audit = MedicalAuditLogger.loadAuditEntry(for: result.intakeId) {
                DisclosureGroup("HAI-DEF Audit Trail") {
                    VStack(alignment: .leading, spacing: 6) {
                        auditRow("Timestamp", audit.timestamp.formatted())
                        auditRow("Model", "\(audit.modelId) (\(audit.modelVersion))")
                        auditRow("On-Device", audit.performanceMetrics.onDeviceInference ? "Yes" : "No")
                        auditRow("Safety Alerts", "\(audit.safetyAlertsGenerated)")
                        auditRow("Disclaimer Shown", audit.disclaimerPresented ? "Yes" : "No")
                        auditRow("Patient Data Hash", audit.patientDataHash)
                        auditRow("Workflow Steps", "\(audit.workflowSteps.count)")

                        ForEach(Array(audit.workflowSteps.enumerated()), id: \.offset) { _, step in
                            HStack {
                                Text("  Step \(step.stepNumber): \(step.title)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text("\(step.outputLengthChars) chars")
                                    .font(.caption2.monospaced())
                                    .foregroundStyle(.tertiary)
                            }
                        }
                    }
                    .padding(.top, 4)
                }
                .font(.caption.weight(.medium))
                .padding()
                .background(Color.purple.opacity(0.03))
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.purple.opacity(0.15), lineWidth: 1)
                )
            }

            // MedGemma Model Card (HAI-DEF requirement)
            modelCardSection

            // Disclaimer
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(.orange)
                        .accessibilityHidden(true)
                    Text("Medical Disclaimer")
                        .font(.headline)
                        .foregroundStyle(.orange)
                }
                Text(result.disclaimer)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()
            .background(Color.orange.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    // MARK: - Actions

    private func runWorkflow(disclaimerConfirmed: Bool = true) async {
        isRunningWorkflow = true
        workflowError = nil
        medicalCase.status = .analyzing
        onUpdate(medicalCase)

        do {
            let result = try await MedicalWorkflowEngine.executeWorkflow(
                intake: medicalCase.intake,
                disclaimerConfirmed: disclaimerConfirmed,
                onProgress: { step in
                    Task { @MainActor in
                        currentStep = step
                    }
                }
            )

            medicalCase.result = result
            medicalCase.status = .completed
            onUpdate(medicalCase)

            // Workflow complete - audit logged by MedicalAuditLogger

        } catch {
            logger.error("Workflow failed: \(error)")
            workflowError = error.localizedDescription
            medicalCase.status = .pending
            onUpdate(medicalCase)
        }

        isRunningWorkflow = false
        currentStep = nil
    }

    // MARK: - Helpers

    private func setupStep(_ number: String, _ text: String) -> some View {
        HStack(alignment: .top, spacing: 6) {
            Text(number)
                .font(.caption2.weight(.bold))
                .foregroundStyle(.blue)
                .frame(width: 14)
            Text(text)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }

    private func infoRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label + ":")
                .font(.caption.weight(.medium))
                .foregroundStyle(.secondary)
                .frame(width: 120, alignment: .leading)
            Text(value)
                .font(.caption)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func edgeAIMetricsSection(_ metrics: PerformanceMetrics, steps: [ReasoningStep]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: "cpu")
                    .foregroundStyle(.blue)
                    .accessibilityHidden(true)
                Text("Edge AI Performance")
                    .font(.headline)
                Spacer()
                Text("100% On-Device")
                    .font(.caption2.weight(.semibold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Color.blue.opacity(0.15))
                    .foregroundStyle(.blue)
                    .clipShape(Capsule())
            }

            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 10) {
                metricCard(
                    "Total Time",
                    formatDuration(metrics.totalWorkflowMs),
                    icon: "clock"
                )
                metricCard(
                    "Avg Step",
                    formatDuration(metrics.averageStepMs),
                    icon: "gauge.with.dots.needle.33percent"
                )
                metricCard(
                    "Model",
                    metrics.modelParameterCount,
                    icon: "brain"
                )
            }

            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 10) {
                metricCard(
                    "Thermal",
                    metrics.deviceThermalState.rawValue,
                    icon: "thermometer.medium"
                )
                metricCard(
                    "Steps",
                    "\(steps.count)",
                    icon: "list.number"
                )
                if let imgMs = metrics.imageAnalysisMs {
                    metricCard(
                        "Image Analysis",
                        formatDuration(imgMs),
                        icon: "photo"
                    )
                } else {
                    metricCard(
                        "Pipeline",
                        "Agentic",
                        icon: "arrow.triangle.branch"
                    )
                }
            }

            // Per-step breakdown
            if !metrics.stepDurations.isEmpty {
                DisclosureGroup("Step Breakdown") {
                    VStack(spacing: 4) {
                        ForEach(steps) { step in
                            HStack {
                                Text("Step \(step.step): \(step.title)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(formatDuration(step.durationMs))
                                    .font(.caption.monospaced())
                                    .foregroundStyle(.blue)
                            }
                        }
                    }
                    .padding(.top, 4)
                }
                .font(.caption.weight(.medium))
            }
        }
        .padding()
        .background(Color.blue.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.blue.opacity(0.2), lineWidth: 1)
        )
    }

    private func metricCard(_ title: String, _ value: String, icon: String) -> some View {
        VStack(spacing: 4) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .foregroundStyle(.blue)
                .accessibilityHidden(true)
            Text(value)
                .font(.system(size: 13, weight: .semibold).monospaced())
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(8)
        .background(Color(NSColor.controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title): \(value)")
    }

    private func formatDuration(_ ms: Double) -> String {
        if ms >= 60_000 {
            return String(format: "%.1fm", ms / 60_000)
        } else if ms >= 1000 {
            return String(format: "%.1fs", ms / 1000)
        } else {
            return String(format: "%.0fms", ms)
        }
    }

    private func triageBadge(_ level: MedicalWorkflowResult.TriageLevel) -> some View {
        Text(level.rawValue)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(triageBackgroundColor(level))
            .clipShape(Capsule())
    }

    private func triageBackgroundColor(_ level: MedicalWorkflowResult.TriageLevel) -> Color {
        switch level {
        case .emergency: return .red.opacity(0.2)
        case .urgent: return .orange.opacity(0.2)
        case .semiUrgent: return .yellow.opacity(0.2)
        case .nonUrgent: return .blue.opacity(0.2)
        case .selfCare: return .green.opacity(0.2)
        }
    }

    private func safetyAlertsSection(_ alerts: [SafetyAlert]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            safetyAlertsHeader

            ForEach(alerts) { alert in
                safetyAlertRow(alert)
            }
        }
        .padding()
        .background(Color.red.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.red.opacity(0.15), lineWidth: 1)
        )
    }

    private var safetyAlertsHeader: some View {
        HStack {
            Image(systemName: "shield.checkered")
                .foregroundStyle(.red)
                .accessibilityHidden(true)
            Text("Safety Alerts")
                .font(.headline)
            Spacer()
            Text("HAI-DEF")
                .font(.caption2.weight(.bold))
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.purple.opacity(0.15))
                .foregroundStyle(.purple)
                .clipShape(Capsule())
        }
    }

    private func safetyAlertRow(_ alert: SafetyAlert) -> some View {
        let color = alertColor(alert.severity)

        return HStack(alignment: .top, spacing: 10) {
            Image(systemName: alertIcon(alert.severity))
                .foregroundStyle(color)
                .font(.system(size: 16))
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 3) {
                HStack {
                    Text(alert.title)
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    Text(alert.category.rawValue)
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(color.opacity(0.1))
                        .foregroundStyle(color)
                        .clipShape(Capsule())
                }
                Text(alert.message)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                if let actionLabel = alert.actionLabel {
                    alertActionButton(actionLabel, color: color, isCritical: alert.severity == .critical)
                }
            }
        }
        .padding(10)
        .background(color.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(color.opacity(0.3), lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(alert.severity.rawValue) alert: \(alert.title). \(alert.message)")
    }

    private func alertActionButton(_ label: String, color: Color, isCritical: Bool) -> some View {
        Button {
            if label.lowercased().contains("911") {
                if let url = URL(string: "tel:911") {
                    NSWorkspace.shared.open(url)
                }
            }
        } label: {
            HStack(spacing: 4) {
                Image(systemName: isCritical ? "phone.fill" : "arrow.right.circle.fill")
                    .font(.caption2)
                    .accessibilityHidden(true)
                Text(label)
                    .font(.caption.weight(.semibold))
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(color)
            .foregroundStyle(.white)
            .clipShape(RoundedRectangle(cornerRadius: 4))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }

    private func alertIcon(_ severity: SafetyAlert.Severity) -> String {
        switch severity {
        case .critical: return "exclamationmark.octagon.fill"
        case .warning: return "exclamationmark.triangle.fill"
        case .info: return "info.circle.fill"
        }
    }

    private func alertColor(_ severity: SafetyAlert.Severity) -> Color {
        switch severity {
        case .critical: return .red
        case .warning: return .orange
        case .info: return .blue
        }
    }

    private func auditRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .font(.caption2.weight(.medium))
                .foregroundStyle(.secondary)
                .frame(width: 120, alignment: .leading)
            Text(value)
                .font(.caption2.monospaced())
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    // MARK: - Model Card (HAI-DEF)

    private var modelCardSection: some View {
        DisclosureGroup("MedGemma Model Card") {
            VStack(alignment: .leading, spacing: 10) {
                modelCardRow("Model", "MedGemma 4B (google/medgemma-4b-it)")
                modelCardRow("Architecture", "Gemma 2 4B fine-tuned on medical corpora")
                modelCardRow("Parameters", "4 billion")
                modelCardRow("Inference", "100% on-device via Ollama (no cloud)")
                modelCardRow("Quantization", "Q4_0 (GGUF) — ~2.5 GB VRAM")

                Divider()

                Text("Intended Use")
                    .font(.caption.weight(.semibold))
                Text("Educational triage screening tool. Assists in symptom assessment and urgency classification. NOT for clinical diagnosis or treatment decisions.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)

                Text("Known Limitations")
                    .font(.caption.weight(.semibold))
                Text("""
                \u{2022} Training data skews toward English-language, US/EU clinical presentations
                \u{2022} Rare diseases and atypical presentations may be under-represented
                \u{2022} Pediatric and geriatric populations may have lower accuracy
                \u{2022} No imaging diagnostic capability (uses OCR/object detection only)
                \u{2022} Probability estimates are heuristic, not calibrated confidence scores
                """)
                    .font(.caption2)
                    .foregroundStyle(.secondary)

                Text("Bias Considerations")
                    .font(.caption.weight(.semibold))
                Text("""
                \u{2022} Chest pain in women may be under-triaged (active bias detection enabled)
                \u{2022} Sex-specific conditions are cross-checked against reported biological sex
                \u{2022} Age-banded vital sign ranges reduce pediatric/geriatric misclassification
                \u{2022} Demographic bias detection alerts flag potential reasoning gaps
                """)
                    .font(.caption2)
                    .foregroundStyle(.secondary)

                Text("Safety Framework")
                    .font(.caption.weight(.semibold))
                Text("""
                \u{2022} HAI-DEF compliant: 8-category post-processing safety validation
                \u{2022} Mandatory disclaimer before every analysis
                \u{2022} SHA-256 patient data hashing in audit trail (no PII stored in logs)
                \u{2022} User feedback loop for triage accuracy tracking
                \u{2022} Emergency escalation alerts with actionable guidance
                """)
                    .font(.caption2)
                    .foregroundStyle(.secondary)

                Text("Privacy Architecture")
                    .font(.caption.weight(.semibold))
                Text("""
                \u{2022} Zero network transmission of patient data
                \u{2022} All inference runs on Apple Silicon via Ollama
                \u{2022} Data stored locally: ~/Library/Application Support/MedStation/
                \u{2022} No telemetry, no analytics, no cloud sync of medical data
                """)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            .padding(.top, 4)
        }
        .font(.caption.weight(.medium))
        .padding()
        .background(Color.teal.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.teal.opacity(0.15), lineWidth: 1)
        )
    }

    private func modelCardRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .font(.caption2.weight(.medium))
                .foregroundStyle(.secondary)
                .frame(width: 100, alignment: .leading)
            Text(value)
                .font(.caption2)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func exportMedicalReport(_ result: MedicalWorkflowResult) {
        let intake = medicalCase.intake
        var report = """
        MEDICAL ANALYSIS REPORT
        Generated: \(result.generatedAt.formatted())
        Model: MedGemma 4B (On-Device)
        ═══════════════════════════════════════

        PATIENT INFORMATION
        ───────────────────
        Patient ID: \(intake.patientId.isEmpty ? "Anonymous" : intake.patientId)
        Chief Complaint: \(intake.chiefComplaint)
        Onset: \(intake.onsetTime)
        Severity: \(intake.severity.rawValue)
        """

        if !intake.symptoms.isEmpty {
            report += "\nSymptoms: \(intake.symptoms.joined(separator: ", "))"
        }
        if !intake.medicalHistory.isEmpty {
            report += "\nMedical History: \(intake.medicalHistory.joined(separator: ", "))"
        }
        if !intake.currentMedications.isEmpty {
            report += "\nMedications: \(intake.currentMedications.joined(separator: ", "))"
        }
        if !intake.allergies.isEmpty {
            report += "\nAllergies: \(intake.allergies.joined(separator: ", "))"
        }

        report += """

        \nTRIAGE ASSESSMENT
        ─────────────────
        \(result.triageLevel.rawValue)

        DIFFERENTIAL DIAGNOSIS
        ──────────────────────
        """

        for (i, dx) in result.differentialDiagnoses.enumerated() {
            report += "\n\(i + 1). \(dx.condition) (\(String(format: "%.0f", dx.probability * 100))%)"
            if !dx.rationale.isEmpty {
                report += "\n   \(dx.rationale)"
            }
        }

        report += "\n\nRECOMMENDED ACTIONS\n───────────────────"
        for action in result.recommendedActions {
            report += "\n[\(action.priority.rawValue)] \(action.action)"
        }

        if let metrics = result.performanceMetrics {
            report += """

            \nEDGE AI PERFORMANCE
            ────────────────────
            Total Workflow: \(String(format: "%.0f", metrics.totalWorkflowMs))ms
            Average Step: \(String(format: "%.0f", metrics.averageStepMs))ms
            Model: \(metrics.modelName) (\(metrics.modelParameterCount) parameters)
            Thermal State: \(metrics.deviceThermalState.rawValue)
            Processing: 100% On-Device
            """
        }

        report += "\n\n\(result.disclaimer)"

        // Show save panel
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.plainText]
        panel.nameFieldStringValue = "MedicalReport-\(medicalCase.id.uuidString.prefix(8)).txt"

        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            try report.write(to: url, atomically: true, encoding: .utf8)
            logger.info("Exported medical report to \(url.lastPathComponent)")
        } catch {
            logger.error("Failed to export medical report: \(error.localizedDescription)")
        }
    }

    private func exportClinicalJSON(_ result: MedicalWorkflowResult) {
        let export = ClinicalExport(
            exportVersion: "1.0",
            generatedAt: Date(),
            intake: medicalCase.intake,
            result: result,
            safetyAlerts: result.safetyAlerts,
            feedback: medicalCase.feedback,
            auditEntry: MedicalAuditLogger.loadAuditEntry(for: result.intakeId)
        )

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601

        let data: Data
        do {
            data = try encoder.encode(export)
        } catch {
            logger.error("Failed to encode clinical export JSON: \(error.localizedDescription)")
            exportError = "Failed to encode clinical data: \(error.localizedDescription)"
            return
        }

        let panel = NSSavePanel()
        panel.allowedContentTypes = [.json]
        panel.nameFieldStringValue = "ClinicalExport-\(medicalCase.id.uuidString.prefix(8)).json"

        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            try data.write(to: url)
            logger.info("Exported clinical JSON to \(url.lastPathComponent)")
        } catch {
            logger.error("Failed to export clinical JSON: \(error.localizedDescription)")
        }
    }

    // MARK: - FHIR R4 Export

    private func exportFHIRBundle(_ result: MedicalWorkflowResult) {
        let intake = medicalCase.intake
        let caseId = medicalCase.id.uuidString
        let patientId = "patient-\(caseId.prefix(8))"
        let now = ISO8601DateFormatter().string(from: result.generatedAt)

        // Build FHIR R4 Bundle with Patient, Conditions, Observations, RiskAssessment
        var entries: [[String: Any]] = []

        // Patient resource
        let patient: [String: Any] = [
            "resourceType": "Patient",
            "id": patientId,
            "identifier": [["value": intake.patientId.isEmpty ? "anonymous" : intake.patientId]],
            "gender": intake.sex?.rawValue.lowercased() ?? "unknown",
            "extension": intake.age.map { [["url": "http://hl7.org/fhir/StructureDefinition/patient-age", "valueInteger": $0]] } ?? []
        ]
        entries.append(["resource": patient, "request": ["method": "POST", "url": "Patient"]])

        // Condition resources (differential diagnoses)
        for dx in result.differentialDiagnoses {
            let condition: [String: Any] = [
                "resourceType": "Condition",
                "id": "condition-\(dx.id.uuidString.prefix(8))",
                "subject": ["reference": "Patient/\(patientId)"],
                "code": ["text": dx.condition],
                "note": [["text": dx.rationale]],
                "extension": [["url": "http://medstation.app/fhir/probability", "valueDecimal": dx.probability]]
            ]
            entries.append(["resource": condition, "request": ["method": "POST", "url": "Condition"]])
        }

        // Observation resources (vital signs)
        if let vitals = intake.vitalSigns {
            func addVital(_ code: String, _ display: String, _ value: Any?, _ unit: String) {
                guard let v = value else { return }
                let obs: [String: Any] = [
                    "resourceType": "Observation",
                    "status": "final",
                    "category": [["coding": [["system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"]]]],
                    "code": ["coding": [["system": "http://loinc.org", "code": code, "display": display]]],
                    "subject": ["reference": "Patient/\(patientId)"],
                    "effectiveDateTime": now,
                    "valueQuantity": ["value": v, "unit": unit]
                ]
                entries.append(["resource": obs, "request": ["method": "POST", "url": "Observation"]])
            }
            addVital("29463-7", "Body weight", vitals.weight, "lbs")
            addVital("8302-2", "Body height", vitals.height, "in")
            addVital("8867-4", "Heart rate", vitals.heartRate, "bpm")
            addVital("8310-5", "Body temperature", vitals.temperature, "°F")
            addVital("9279-1", "Respiratory rate", vitals.respiratoryRate, "/min")
            addVital("2708-6", "Oxygen saturation", vitals.oxygenSaturation, "%")
            if let bp = vitals.bloodPressure {
                let bpObs: [String: Any] = [
                    "resourceType": "Observation",
                    "status": "final",
                    "code": ["coding": [["system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure"]]],
                    "subject": ["reference": "Patient/\(patientId)"],
                    "effectiveDateTime": now,
                    "valueString": bp
                ]
                entries.append(["resource": bpObs, "request": ["method": "POST", "url": "Observation"]])
            }
        }

        // RiskAssessment resource (triage)
        let riskLevel: String
        switch result.triageLevel {
        case .emergency: riskLevel = "critical"
        case .urgent: riskLevel = "high"
        case .semiUrgent: riskLevel = "moderate"
        case .nonUrgent: riskLevel = "low"
        case .selfCare: riskLevel = "negligible"
        }

        let riskAssessment: [String: Any] = [
            "resourceType": "RiskAssessment",
            "status": "final",
            "subject": ["reference": "Patient/\(patientId)"],
            "occurrenceDateTime": now,
            "method": ["text": "MedGemma 4B on-device agentic workflow (5-step)"],
            "prediction": result.differentialDiagnoses.map { dx -> [String: Any] in
                ["outcome": ["text": dx.condition], "probabilityDecimal": dx.probability]
            },
            "mitigation": result.triageLevel.rawValue,
            "note": [["text": result.disclaimer]],
            "extension": [["url": "http://medstation.app/fhir/triage-level", "valueCode": riskLevel]]
        ]
        entries.append(["resource": riskAssessment, "request": ["method": "POST", "url": "RiskAssessment"]])

        let bundle: [String: Any] = [
            "resourceType": "Bundle",
            "type": "transaction",
            "timestamp": now,
            "meta": ["profile": ["http://medstation.app/fhir/medgemma-triage-bundle"]],
            "entry": entries
        ]

        let data: Data
        do {
            data = try JSONSerialization.data(withJSONObject: bundle, options: [.prettyPrinted, .sortedKeys])
        } catch {
            logger.error("Failed to serialize FHIR bundle: \(error.localizedDescription)")
            exportError = "Failed to serialize FHIR bundle: \(error.localizedDescription)"
            return
        }

        let panel = NSSavePanel()
        panel.allowedContentTypes = [.json]
        panel.nameFieldStringValue = "FHIR-Bundle-\(caseId.prefix(8)).json"

        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            try data.write(to: url)
            logger.info("Exported FHIR R4 bundle to \(url.lastPathComponent)")
        } catch {
            logger.error("Failed to export FHIR bundle: \(error.localizedDescription)")
        }
    }

    private func priorityColor(_ priority: RecommendedAction.ActionPriority) -> Color {
        switch priority {
        case .immediate: return .red
        case .high: return .orange
        case .medium: return .blue
        case .low: return .green
        }
    }
}

// MARK: - Benchmark Sheet

private struct BenchmarkSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var harness: MedicalBenchmarkHarness

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if harness.isRunning {
                    benchmarkProgressView
                } else if let report = harness.report {
                    benchmarkReportView(report)
                } else {
                    benchmarkStartView
                }
            }
            .navigationTitle("Evaluation Benchmark")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
                if let report = harness.report, !harness.isRunning {
                    ToolbarItem(placement: .primaryAction) {
                        Button {
                            exportBenchmarkReport(report)
                        } label: {
                            Label("Export", systemImage: "square.and.arrow.up")
                        }
                        .accessibilityLabel("Export benchmark report")
                    }
                }
            }
        }
        .frame(width: 700, height: 600)
        .onAppear {
            if harness.report == nil {
                harness.report = MedicalBenchmarkHarness.loadLatestReport()
            }
        }
    }

    // MARK: - Start View

    private var benchmarkStartView: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "chart.bar.doc.horizontal")
                .font(.system(size: 48))
                .foregroundStyle(.teal)
                .accessibilityHidden(true)
            Text("MedGemma Evaluation Benchmark")
                .font(.title2.weight(.semibold))
            Text("Runs 10 clinically validated vignettes through the full 5-step\nagentic workflow and scores against expected outcomes.")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            VStack(alignment: .leading, spacing: 8) {
                benchmarkInfoRow("Triage Accuracy", "Exact match + partial credit for adjacent levels")
                benchmarkInfoRow("Diagnosis Recall", "Keyword overlap with expected differential")
                benchmarkInfoRow("Safety Coverage", "Required safety alert categories triggered")
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 8))

            Text("Requires MedGemma model loaded via Ollama. Each vignette takes ~30-60s.")
                .font(.caption)
                .foregroundStyle(.tertiary)

            Button {
                harness.run()
            } label: {
                Label("Run Benchmark", systemImage: "play.fill")
                    .frame(width: 180)
            }
            .controlSize(.large)
            .buttonStyle(.borderedProminent)
            .tint(.teal)
            .accessibilityHint("Runs 10 clinical vignettes through the full workflow. Takes 5-10 minutes.")

            if let error = harness.error {
                Text("Error: \(error)")
                    .font(.caption)
                    .foregroundStyle(.red)
            }

            Spacer()
        }
        .padding(30)
    }

    // MARK: - Progress View

    private var benchmarkProgressView: some View {
        VStack(spacing: 20) {
            Spacer()
            ProgressView(value: Double(harness.currentVignetteIndex), total: 10)
                .progressViewStyle(.linear)
                .frame(width: 300)

            Text("Running vignette \(harness.currentVignetteIndex + 1) of 10")
                .font(.headline)

            Text(harness.currentVignetteName)
                .font(.body)
                .foregroundStyle(.secondary)

            ProgressView()
                .controlSize(.small)

            Button("Cancel") {
                harness.cancel()
            }
            .controlSize(.small)
            .accessibilityLabel("Cancel benchmark")
            Spacer()
        }
        .padding(30)
    }

    // MARK: - Report View

    private func benchmarkReportView(_ report: BenchmarkReport) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Aggregate scores
                HStack(spacing: 16) {
                    scoreCard("Composite", report.meanCompositeScore, .teal)
                    scoreCard("Triage", report.triageAccuracy, triageScoreColor(report.triageAccuracy))
                    scoreCard("Diagnosis", report.meanDiagnosisRecall, recallScoreColor(report.meanDiagnosisRecall))
                    scoreCard("Safety", report.meanSafetyCoverage, recallScoreColor(report.meanSafetyCoverage))
                }

                HStack(spacing: 16) {
                    metricCard("Pass Rate", String(format: "%.0f%%", report.passRate * 100))
                    metricCard("Avg Workflow", String(format: "%.1fs", report.meanWorkflowMs / 1000))
                    metricCard("Total Time", String(format: "%.1fs", report.totalDurationMs / 1000))
                    metricCard("Vignettes", "\(report.vignetteCount)")
                }

                Divider()

                // Per-vignette results
                Text("Per-Vignette Results")
                    .font(.headline)

                ForEach(report.results) { result in
                    vignetteResultRow(result)
                }

                Divider()

                // Confusion matrix
                Text("Triage Confusion Matrix")
                    .font(.headline)

                confusionMatrixView(report.triageConfusion)

                // Run again button
                HStack {
                    Spacer()
                    Button {
                        harness.run()
                    } label: {
                        Label("Run Again", systemImage: "arrow.clockwise")
                    }
                    .controlSize(.small)
                    .accessibilityLabel("Run benchmark again")
                }

                // Timestamp
                Text("Benchmark run: \(report.timestamp.formatted(date: .abbreviated, time: .shortened)) — \(report.modelName)")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding(20)
        }
    }

    // MARK: - Score Cards

    private func scoreCard(_ title: String, _ score: Double, _ color: Color) -> some View {
        VStack(spacing: 4) {
            Text(String(format: "%.0f%%", score * 100))
                .font(.system(size: 24, weight: .bold).monospaced())
                .foregroundStyle(color)
            Text(title)
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(color.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title): \(String(format: "%.0f%%", score * 100))")
    }

    private func metricCard(_ title: String, _ value: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 16, weight: .semibold).monospaced())
            Text(title)
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(Color(NSColor.controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title): \(value)")
    }

    // MARK: - Vignette Row

    private func vignetteResultRow(_ result: BenchmarkVignetteResult) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: result.passed ? "checkmark.circle.fill" : "xmark.circle.fill")
                    .foregroundStyle(result.passed ? .green : .red)
                    .accessibilityHidden(true)
                Text(result.vignetteName)
                    .font(.system(size: 13, weight: .medium))
                Text(result.vignetteCategory)
                    .font(.system(size: 10))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.teal.opacity(0.15))
                    .foregroundStyle(.teal)
                    .clipShape(Capsule())
                Spacer()
                Text(String(format: "%.0f%%", result.compositeScore * 100))
                    .font(.system(size: 13, weight: .bold).monospaced())
                    .foregroundStyle(result.passed ? .green : .red)
            }

            HStack(spacing: 16) {
                vignetteMetric("Triage", result.triageScore, detail: triageCompare(result))
                vignetteMetric("Dx Recall", result.diagnosisRecall, detail: "\(result.matchedKeywords.count)/\(result.expectedKeywords.count)")
                vignetteMetric("Safety", result.safetyCoverage, detail: "\(result.triggeredSafetyCategories.count) alerts")
                vignetteMetric("Time", nil, detail: String(format: "%.1fs", result.workflowDurationMs / 1000))
            }
            .font(.system(size: 11))
        }
        .padding(10)
        .background(Color(NSColor.controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(result.vignetteName), \(result.passed ? "passed" : "failed"), \(String(format: "%.0f%%", result.compositeScore * 100)) score")
    }

    private func vignetteMetric(_ label: String, _ score: Double?, detail: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .foregroundStyle(.tertiary)
                .font(.system(size: 10))
            if let score {
                Text(String(format: "%.0f%%", score * 100))
                    .font(.system(size: 11, weight: .semibold).monospaced())
                    .foregroundStyle(score >= 0.8 ? .green : score >= 0.5 ? .orange : .red)
            }
            Text(detail)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Confusion Matrix

    private static let confusionLevels = [
        "Emergency (Call 911)", "Urgent (Seek care within 2-4 hours)",
        "Semi-Urgent (See doctor within 24 hours)", "Non-Urgent (Schedule appointment)",
        "Self-Care (Monitor at home)"
    ]
    private static let confusionLabels = ["EMG", "URG", "S-URG", "NON", "SELF"]

    private func confusionMatrixView(_ matrix: [String: [String: Int]]) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            confusionHeaderRow
            ForEach(Array(Self.confusionLabels.enumerated()), id: \.offset) { idx, label in
                confusionDataRow(label: label, level: Self.confusionLevels[idx], matrix: matrix)
            }
        }
        .padding(10)
        .background(Color(NSColor.controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 6))
    }

    private var confusionHeaderRow: some View {
        HStack(spacing: 0) {
            Text("Expected ↓  Actual →")
                .font(.system(size: 9))
                .foregroundStyle(.tertiary)
                .frame(width: 120, alignment: .leading)
            ForEach(Array(Self.confusionLabels.enumerated()), id: \.offset) { _, label in
                Text(label)
                    .font(.system(size: 9, weight: .semibold))
                    .frame(width: 50)
            }
        }
    }

    private func confusionDataRow(label: String, level: String, matrix: [String: [String: Int]]) -> some View {
        HStack(spacing: 0) {
            Text(label)
                .font(.system(size: 10, weight: .medium))
                .frame(width: 120, alignment: .leading)
            ForEach(Array(Self.confusionLevels.enumerated()), id: \.offset) { idx, actualLevel in
                confusionCell(count: matrix[level]?[actualLevel] ?? 0, isDiagonal: Self.confusionLevels[idx] == level)
            }
        }
    }

    private func confusionCell(count: Int, isDiagonal: Bool) -> some View {
        let weight: Font.Weight = count > 0 ? .bold : .regular
        let color: Color = isDiagonal ? .green : .red
        return Text(count > 0 ? "\(count)" : "·")
            .font(.system(size: 11, weight: weight).monospaced())
            .foregroundStyle(count > 0 ? AnyShapeStyle(color) : AnyShapeStyle(.quaternary))
            .frame(width: 50)
    }

    // MARK: - Helpers

    private func benchmarkInfoRow(_ title: String, _ description: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "checkmark.circle")
                .foregroundStyle(.teal)
                .font(.system(size: 12))
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.system(size: 12, weight: .semibold))
                Text(description).font(.system(size: 11)).foregroundStyle(.secondary)
            }
        }
        .accessibilityElement(children: .combine)
    }

    private func triageCompare(_ result: BenchmarkVignetteResult) -> String {
        if result.triageScore >= 1.0 { return "Exact match" }
        if result.triageScore >= 0.5 { return "Adjacent" }
        return "Mismatch"
    }

    private func triageScoreColor(_ score: Double) -> Color {
        score >= 0.8 ? .green : score >= 0.6 ? .orange : .red
    }

    private func recallScoreColor(_ score: Double) -> Color {
        score >= 0.7 ? .green : score >= 0.4 ? .orange : .red
    }

    private func exportBenchmarkReport(_ report: BenchmarkReport) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601

        let data: Data
        do {
            data = try encoder.encode(report)
        } catch {
            logger.error("Failed to encode benchmark report: \(error.localizedDescription)")
            return
        }

        let panel = NSSavePanel()
        panel.allowedContentTypes = [.json]
        panel.nameFieldStringValue = "MedGemma-Benchmark-\(report.timestamp.formatted(date: .numeric, time: .omitted)).json"
        guard panel.runModal() == .OK, let url = panel.url else { return }

        do {
            try data.write(to: url)
            logger.info("Exported benchmark report to \(url.lastPathComponent)")
        } catch {
            logger.error("Failed to export benchmark: \(error.localizedDescription)")
        }
    }
}

// MARK: - Clinical Export Model

private struct ClinicalExport: Codable {
    let exportVersion: String
    let generatedAt: Date
    let intake: PatientIntake
    let result: MedicalWorkflowResult
    let safetyAlerts: [SafetyAlert]
    let feedback: TriageFeedback?
    let auditEntry: AuditEntry?
}

// MARK: - Triage Helpers

private func triageColor(_ level: MedicalWorkflowResult.TriageLevel) -> Color {
    switch level {
    case .emergency: return .red
    case .urgent: return .orange
    case .semiUrgent: return .yellow
    case .nonUrgent: return .blue
    case .selfCare: return .green
    }
}

private func triageShort(_ level: MedicalWorkflowResult.TriageLevel) -> String {
    switch level {
    case .emergency: return "EMG"
    case .urgent: return "URG"
    case .semiUrgent: return "S-URG"
    case .nonUrgent: return "NON"
    case .selfCare: return "SELF"
    }
}
