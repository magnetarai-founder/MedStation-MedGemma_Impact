//
//  MedicalPanel.swift
//  MagnetarStudio
//
//  Medical workspace panel for patient intake and MedGemma-powered agentic workflows.
//  Displays case list, intake details, workflow progress, and structured results.
//
//  MedGemma Impact Challenge (Kaggle 2026).
//

import SwiftUI
import UniformTypeIdentifiers
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "MedicalPanel")

// MARK: - Medical Panel

struct MedicalPanel: View {
    @State private var cases: [MedicalCase] = []
    @State private var selectedCaseID: UUID?
    @State private var isLoading = true
    @State private var showNewCaseSheet = false
    @State private var searchText = ""
    @AppStorage("medical.onboarding.shown") private var hasShownOnboarding = false
    @State private var showOnboarding = false

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
                    action: { showNewCaseSheet = true },
                    actionLabel: "New Case"
                )
            }
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showNewCaseSheet = true
                } label: {
                    Label("New Case", systemImage: "plus.circle.fill")
                }
                .accessibilityLabel("Create new medical case")
            }
        }
        .sheet(isPresented: $showNewCaseSheet) {
            NewCaseSheet { intake in
                createNewCase(intake: intake)
            }
        }
        .task {
            await loadCases()
            if !hasShownOnboarding {
                try? await Task.sleep(for: .seconds(0.5))
                showOnboarding = true
            }
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
        guard !searchText.isEmpty else { return cases }
        let query = searchText.lowercased()
        return cases.filter {
            $0.intake.patientId.lowercased().contains(query) ||
            $0.intake.chiefComplaint.lowercased().contains(query) ||
            $0.intake.symptoms.contains(where: { $0.lowercased().contains(query) })
        }
    }

    private var casesSidebar: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Medical Cases")
                    .font(.headline)
                Spacer()
                Text("\(cases.count)")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.tertiary)
                TextField("Search cases...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)

            Divider()

            if isLoading {
                ProgressView()
                    .frame(maxHeight: .infinity)
            } else if cases.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "cross.case")
                        .font(.system(size: 40))
                        .foregroundStyle(.tertiary)
                    Text("No Cases")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                    Text("Create your first medical case")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                .frame(maxHeight: .infinity)
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
                                if medicalCase.status != .archived {
                                    Button {
                                        archiveCase(medicalCase.id)
                                    } label: {
                                        Label("Archive Case", systemImage: "archivebox")
                                    }
                                }
                                Button(role: .destructive) {
                                    deleteCase(medicalCase.id)
                                } label: {
                                    Label("Delete Case", systemImage: "trash")
                                }
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
        let completedCases = cases.filter { $0.result != nil }
        let emergencyCount = completedCases.filter { $0.result?.triageLevel == .emergency }.count
        let avgTriageMs: Double = {
            let times = completedCases.compactMap { $0.result?.performanceMetrics?.totalWorkflowMs }
            guard !times.isEmpty else { return 0 }
            return times.reduce(0, +) / Double(times.count)
        }()
        let feedbackCases = cases.compactMap(\.feedback)
        let accuracyPct: Double = {
            guard !feedbackCases.isEmpty else { return 0 }
            let accurate = feedbackCases.filter { $0.rating == .accurate }.count
            return Double(accurate) / Double(feedbackCases.count) * 100
        }()

        return DisclosureGroup("Impact Analytics") {
            VStack(spacing: 6) {
                analyticsRow("Cases Analyzed", "\(completedCases.count)")
                analyticsRow("Emergency Detected", "\(emergencyCount)")
                analyticsRow("Avg Triage Time", avgTriageMs > 0 ? String(format: "%.1fs", avgTriageMs / 1000) : "—")
                if !feedbackCases.isEmpty {
                    analyticsRow("Feedback Accuracy", String(format: "%.0f%%", accuracyPct))
                }
            }
            .padding(.top, 4)
        }
        .font(.system(size: 11, weight: .medium))
        .foregroundStyle(.secondary)
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
                    oxygenSaturation: 94
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
        showNewCaseSheet = false
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

    private func archiveCase(_ id: UUID) {
        guard let index = cases.firstIndex(where: { $0.id == id }) else { return }
        cases[index].status = .archived
        saveCaseToFile(cases[index])
        logger.info("Archived medical case \(id.uuidString.prefix(8))")
    }

    private func deleteCase(_ id: UUID) {
        let file = Self.storageDirectory.appendingPathComponent("\(id.uuidString).json")
        PersistenceHelpers.remove(at: file, label: "medical case")
        cases.removeAll { $0.id == id }
        if selectedCaseID == id { selectedCaseID = nil }
        logger.info("Deleted medical case \(id.uuidString.prefix(8))")
    }

    private static var storageDirectory: URL {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/medical", isDirectory: true)
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

    // Follow-up Q&A chat (persisted via MedicalCase.followUpMessages)
    @State private var chatMessages: [FollowUpMessage] = []
    @State private var chatInput = ""
    @State private var isChatStreaming = false

    var body: some View {
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
                    Divider()
                    followUpChatSection
                }
            }
            .padding(20)
        }
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
    }

    // MARK: - Header

    private var headerSection: some View {
        HStack {
            Image(systemName: "cross.case.fill")
                .font(.title)
                .foregroundStyle(LinearGradient.magnetarGradient)

            VStack(alignment: .leading, spacing: 2) {
                Text("Patient: \(medicalCase.intake.patientId.isEmpty ? "Anonymous" : medicalCase.intake.patientId)")
                    .font(.title2.weight(.semibold))

                Text("Case \(medicalCase.id.uuidString.prefix(8))")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            Spacer()

            if let result = medicalCase.result {
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
                } label: {
                    Label("Export", systemImage: "arrow.up.doc")
                        .font(.caption)
                }
                .menuStyle(.borderlessButton)
                .fixedSize()
                .accessibilityLabel("Export medical report")

                triageBadge(result.triageLevel)
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
                    if let hr = vitals.heartRate { infoRow("Heart Rate", "\(hr) bpm") }
                    if let bp = vitals.bloodPressure { infoRow("Blood Pressure", bp) }
                    if let temp = vitals.temperature { infoRow("Temperature", String(format: "%.1f°F", temp)) }
                    if let rr = vitals.respiratoryRate { infoRow("Respiratory Rate", "\(rr)/min") }
                    if let spo2 = vitals.oxygenSaturation { infoRow("SpO2", "\(spo2)%") }
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
                .background(LinearGradient.magnetarGradient)
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Run MedGemma medical analysis workflow")

            if case .downloading(let progress) = aiService.modelStatus {
                HStack(spacing: 8) {
                    ProgressView(value: progress)
                        .frame(width: 100)
                    Text("Downloading MedGemma... \(Int(progress * 100))%")
                        .font(.caption)
                }
                .padding(8)
                .background(Color.orange.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            } else if case .failed(let msg) = aiService.modelStatus {
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                        Text("Model error: \(msg)")
                            .font(.caption)
                    }

                    // Ollama setup guide
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Setup Guide")
                            .font(.caption.weight(.semibold))
                        Text("MedGemma requires Ollama running locally:")
                            .font(.caption2)
                            .foregroundStyle(.secondary)

                        VStack(alignment: .leading, spacing: 3) {
                            setupStep("1", "Install Ollama from ollama.com")
                            setupStep("2", "Start Ollama (it runs in the menu bar)")
                            setupStep("3", "The model downloads automatically (~2.5 GB)")
                        }

                        HStack(spacing: 8) {
                            Button {
                                NSWorkspace.shared.open(URL(string: "https://ollama.com/download")!)
                            } label: {
                                Text("Download Ollama")
                                    .font(.caption.weight(.medium))
                            }

                            Button {
                                Task { await aiService.ensureModelReady() }
                            } label: {
                                Label("Retry Connection", systemImage: "arrow.clockwise")
                                    .font(.caption)
                            }
                        }
                    }
                    .padding(8)
                    .background(Color(NSColor.controlBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }
                .padding(8)
                .background(Color.orange.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            } else if case .notInstalled = aiService.modelStatus {
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Image(systemName: "arrow.down.circle")
                            .foregroundStyle(.blue)
                        Text("MedGemma model not yet downloaded")
                            .font(.caption)
                    }
                    Text("Click 'Run Medical Analysis' to auto-download (~2.5 GB). Requires Ollama running locally.")
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
                Text("Triage Feedback")
                    .font(.headline)
            }

            if let feedback = medicalCase.feedback {
                HStack(spacing: 8) {
                    Image(systemName: feedback.rating == .accurate ? "checkmark.circle.fill" : feedback.rating == .incorrect ? "xmark.circle.fill" : "minus.circle.fill")
                        .foregroundStyle(feedback.rating == .accurate ? Color.green : feedback.rating == .incorrect ? Color.red : Color.orange)
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
                    }
                }

                TextField("Optional notes...", text: $feedbackNotes)
                    .textFieldStyle(.roundedBorder)
                    .font(.caption)
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

    // MARK: - Follow-Up Chat

    private var followUpChatSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "bubble.left.and.bubble.right")
                    .foregroundStyle(.purple)
                Text("Ask Follow-Up Questions")
                    .font(.headline)
                Spacer()
                if isChatStreaming {
                    ProgressView()
                        .scaleEffect(0.7)
                }
            }

            if !chatMessages.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(Array(chatMessages.enumerated()), id: \.offset) { _, msg in
                        HStack(alignment: .top, spacing: 8) {
                            Image(systemName: msg.role == "user" ? "person.circle.fill" : "cross.case.circle.fill")
                                .foregroundStyle(msg.role == "user" ? Color.blue : Color.purple)
                                .font(.system(size: 16))

                            Text(msg.content)
                                .font(.caption)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .padding(8)
                        .background(msg.role == "user" ? Color.blue.opacity(0.05) : Color.purple.opacity(0.05))
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                }
            }

            HStack(spacing: 8) {
                TextField("Ask about the diagnosis, treatment options, or next steps...", text: $chatInput)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit { Task { await sendChatMessage() } }
                    .disabled(isChatStreaming)

                Button {
                    Task { await sendChatMessage() }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 24))
                        .foregroundStyle(.purple)
                }
                .buttonStyle(.plain)
                .disabled(chatInput.trimmingCharacters(in: .whitespaces).isEmpty || isChatStreaming)
                .accessibilityLabel("Send follow-up question")
            }

            Text("Responses use MedGemma on-device. Not medical advice.")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding()
        .background(Color.purple.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.purple.opacity(0.15), lineWidth: 1)
        )
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

            // Fire automation trigger
            await AutomationStore.shared.evaluate(
                context: TriggerContext(
                    trigger: .onMedicalAnalysisComplete,
                    fields: [
                        "caseId": medicalCase.id.uuidString,
                        "patientId": medicalCase.intake.patientId,
                        "triageLevel": result.triageLevel.rawValue
                    ]
                )
            )

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
                NSWorkspace.shared.open(URL(string: "tel:911")!)
            }
        } label: {
            HStack(spacing: 4) {
                Image(systemName: isCritical ? "phone.fill" : "arrow.right.circle.fill")
                    .font(.caption2)
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
                \u{2022} Data stored locally: ~/Library/Application Support/MagnetarStudio/
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

        guard let data = try? encoder.encode(export) else {
            logger.error("Failed to encode clinical export JSON")
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

    private func priorityColor(_ priority: RecommendedAction.ActionPriority) -> Color {
        switch priority {
        case .immediate: return .red
        case .high: return .orange
        case .medium: return .blue
        case .low: return .green
        }
    }
}

// MARK: - New Case Sheet

private struct NewCaseSheet: View {
    @Environment(\.dismiss) private var dismiss
    let onCreate: (PatientIntake) -> Void

    @State private var patientId = ""
    @State private var age = ""
    @State private var sex: BiologicalSex? = nil
    @State private var isPregnant = false
    @State private var chiefComplaint = ""
    @State private var onsetTime = ""
    @State private var severity: PatientIntake.Severity = .moderate
    @State private var symptomsText = ""
    @State private var medicalHistoryText = ""
    @State private var medicationsText = ""
    @State private var allergiesText = ""

    @State private var includeVitals = false
    @State private var heartRate = ""
    @State private var bloodPressure = ""
    @State private var temperature = ""
    @State private var respiratoryRate = ""
    @State private var oxygenSaturation = ""
    @State private var attachedImagePaths: [String] = []

    var body: some View {
        NavigationStack {
            Form {
                Section("Patient Information") {
                    TextField("Patient ID (optional)", text: $patientId)
                    TextField("Chief Complaint", text: $chiefComplaint, axis: .vertical)
                        .lineLimit(2...4)
                    TextField("Onset (e.g., '2 hours ago', '3 days')", text: $onsetTime)
                    Picker("Severity", selection: $severity) {
                        ForEach(PatientIntake.Severity.allCases, id: \.self) { sev in
                            Text(sev.rawValue).tag(sev)
                        }
                    }
                }

                Section("Demographics") {
                    HStack(spacing: 12) {
                        TextField("Age", text: $age)
                            .frame(width: 60)
                        Picker("Biological Sex", selection: $sex) {
                            Text("Not specified").tag(nil as BiologicalSex?)
                            ForEach(BiologicalSex.allCases, id: \.self) { s in
                                Text(s.rawValue).tag(s as BiologicalSex?)
                            }
                        }
                        .frame(width: 180)
                    }
                    if sex == .female {
                        Toggle("Currently Pregnant", isOn: $isPregnant)
                    }
                }

                Section("Symptoms") {
                    TextField("Symptoms (comma-separated)", text: $symptomsText, axis: .vertical)
                        .lineLimit(2...4)
                }

                Section("Vital Signs") {
                    Toggle("Include Vital Signs", isOn: $includeVitals)

                    if includeVitals {
                        TextField("Heart Rate (bpm)", text: $heartRate)
                        TextField("Blood Pressure (e.g., 120/80)", text: $bloodPressure)
                        TextField("Temperature (°F)", text: $temperature)
                        TextField("Respiratory Rate (per min)", text: $respiratoryRate)
                        TextField("SpO2 (%)", text: $oxygenSaturation)

                        // Inline validation warnings
                        ForEach(vitalValidationWarnings, id: \.self) { warning in
                            HStack(spacing: 4) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundStyle(.orange)
                                    .font(.caption2)
                                Text(warning)
                                    .font(.caption)
                                    .foregroundStyle(.orange)
                            }
                        }
                    }
                }

                Section("Medical History") {
                    TextField("Medical History (comma-separated)", text: $medicalHistoryText, axis: .vertical)
                        .lineLimit(2...4)
                    TextField("Current Medications (comma-separated)", text: $medicationsText, axis: .vertical)
                        .lineLimit(2...4)
                    TextField("Allergies (comma-separated)", text: $allergiesText, axis: .vertical)
                        .lineLimit(2...4)
                }

                Section("Medical Images") {
                    Button {
                        pickImages()
                    } label: {
                        Label("Attach Images", systemImage: "photo.badge.plus")
                    }
                    .accessibilityLabel("Attach medical images such as X-rays or lab results")

                    if !attachedImagePaths.isEmpty {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(attachedImagePaths, id: \.self) { path in
                                    ZStack(alignment: .topTrailing) {
                                        if let img = NSImage(contentsOfFile: path) {
                                            Image(nsImage: img)
                                                .resizable()
                                                .aspectRatio(contentMode: .fill)
                                                .frame(width: 80, height: 80)
                                                .clipShape(RoundedRectangle(cornerRadius: 6))
                                        } else {
                                            RoundedRectangle(cornerRadius: 6)
                                                .fill(Color.gray.opacity(0.2))
                                                .frame(width: 80, height: 80)
                                                .overlay {
                                                    Image(systemName: "photo")
                                                        .foregroundStyle(.tertiary)
                                                }
                                        }

                                        Button {
                                            attachedImagePaths.removeAll { $0 == path }
                                        } label: {
                                            Image(systemName: "xmark.circle.fill")
                                                .font(.system(size: 16))
                                                .foregroundStyle(.white, .red)
                                        }
                                        .buttonStyle(.plain)
                                        .offset(x: 4, y: -4)
                                        .accessibilityLabel("Remove attached image")
                                    }
                                }
                            }
                        }
                        Text("\(attachedImagePaths.count) image(s) attached — will be analyzed by on-device Vision pipeline")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .formStyle(.grouped)
            .navigationTitle("New Medical Case")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") { createIntake() }
                        .disabled(chiefComplaint.isEmpty)
                }
            }
        }
        .frame(width: 600, height: 700)
    }

    private var vitalValidationWarnings: [String] {
        guard includeVitals else { return [] }
        var warnings: [String] = []
        if let hr = Int(heartRate) {
            if hr < 20 || hr > 300 { warnings.append("Heart rate \(hr) is outside physiologic range (20-300)") }
        }
        if let spo2 = Int(oxygenSaturation) {
            if spo2 > 100 { warnings.append("SpO2 cannot exceed 100%") }
            if spo2 < 0 { warnings.append("SpO2 cannot be negative") }
        }
        if let temp = Double(temperature) {
            if temp < 80 || temp > 115 { warnings.append("Temperature \(String(format: "%.1f", temp))°F is outside expected range") }
        }
        if let rr = Int(respiratoryRate) {
            if rr < 4 || rr > 60 { warnings.append("Respiratory rate \(rr) is outside expected range (4-60)") }
        }
        return warnings
    }

    private func createIntake() {
        let symptoms = symptomsText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
        let history = medicalHistoryText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
        let meds = medicationsText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
        let allergies = allergiesText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }

        var vitals: VitalSigns?
        if includeVitals {
            vitals = VitalSigns(
                heartRate: Int(heartRate),
                bloodPressure: bloodPressure.isEmpty ? nil : bloodPressure,
                temperature: Double(temperature),
                respiratoryRate: Int(respiratoryRate),
                oxygenSaturation: Int(oxygenSaturation)
            )
        }

        let intake = PatientIntake(
            patientId: patientId,
            age: Int(age),
            sex: sex,
            isPregnant: isPregnant,
            chiefComplaint: chiefComplaint,
            symptoms: symptoms,
            onsetTime: onsetTime,
            severity: severity,
            vitalSigns: vitals,
            medicalHistory: history,
            currentMedications: meds,
            allergies: allergies,
            attachedImagePaths: attachedImagePaths
        )

        onCreate(intake)
        dismiss()
    }

    private func pickImages() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.image, .png, .jpeg, .heic, .tiff, .pdf]
        panel.message = "Select medical images (X-rays, lab results, skin photos, etc.)"

        guard panel.runModal() == .OK else { return }

        let newPaths = panel.urls.map(\.path)
        attachedImagePaths.append(contentsOf: newPaths)
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
