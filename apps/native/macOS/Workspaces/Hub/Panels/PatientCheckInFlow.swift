//
//  PatientCheckInFlow.swift
//  MedStation
//
//  Guided patient check-in wizard: 4 intake steps → MedGemma analysis → editable results.
//  Replaces the old single-form NewCaseSheet with a step-by-step modal flow.
//
//  MedGemma Impact Challenge (Kaggle 2026).
//

import SwiftUI
import AppKit
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "PatientCheckIn")

// MARK: - Check-In Step Enum

enum CheckInStep: Int, CaseIterable {
    case chiefComplaint = 0
    case patientDetails = 1
    case medicalBackground = 2
    case review = 3
    case analyzing = 4
    case results = 5

    var title: String {
        switch self {
        case .chiefComplaint: "Chief Complaint"
        case .patientDetails: "Patient Details"
        case .medicalBackground: "Background"
        case .review: "Review"
        case .analyzing: "Analyzing"
        case .results: "Results"
        }
    }

    /// The 4 user-facing intake steps (shown in step indicator)
    static let intakeSteps: [CheckInStep] = [.chiefComplaint, .patientDetails, .medicalBackground, .review]
}

enum OnsetUnit: String, CaseIterable {
    case minutes = "Minutes"
    case hours = "Hours"
    case days = "Days"
    case weeks = "Weeks"
    case months = "Months"
    case years = "Years"
}

// MARK: - Patient Check-In Flow

struct PatientCheckInFlow: View {
    @Environment(\.dismiss) private var dismiss
    let onComplete: (MedicalCase) -> Void

    // MARK: - Navigation State

    @State private var currentStep: CheckInStep = .chiefComplaint

    // MARK: - Form State (Step 1: Chief Complaint)

    @State private var chiefComplaint = ""
    @State private var onsetValue = ""
    @State private var onsetUnit: OnsetUnit = .hours
    @State private var severity: PatientIntake.Severity?

    // MARK: - Form State (Step 2: Patient Details)

    @State private var patientId = ""
    @State private var age = ""
    @State private var sex: BiologicalSex? = nil
    @State private var isPregnant = false
    @State private var symptomsText = ""
    @State private var heartRate = ""
    @State private var bloodPressure = ""
    @State private var temperature = ""
    @State private var oxygenSaturation = ""
    @State private var weight = ""
    @State private var height = ""

    // MARK: - Form State (Step 3: Medical Background)

    @State private var medicalHistoryText = ""
    @State private var medicationsText = ""
    @State private var allergiesText = ""
    @State private var attachedImagePaths: [String] = []

    // MARK: - Analysis State

    @State private var isRunningWorkflow = false
    @State private var currentReasoningStep: ReasoningStep?
    @State private var workflowError: String?

    // MARK: - Results State

    @State private var workflowResult: MedicalWorkflowResult?
    @State private var editableTriageLevel: MedicalWorkflowResult.TriageLevel = .semiUrgent
    @State private var editableDiagnoses: [Diagnosis] = []
    @State private var editableActions: [RecommendedAction] = []

    // MARK: - Body

    var body: some View {
        VStack(spacing: 0) {
            // Step indicator (hidden during analysis/results)
            if currentStep.rawValue <= CheckInStep.review.rawValue {
                stepIndicator
                    .padding(.horizontal, 24)
                    .padding(.top, 16)
                    .padding(.bottom, 8)
            }

            Divider()

            // Content area
            ScrollView {
                Group {
                    switch currentStep {
                    case .chiefComplaint:
                        chiefComplaintStep
                    case .patientDetails:
                        patientDetailsStep
                    case .medicalBackground:
                        medicalBackgroundStep
                    case .review:
                        reviewStep
                    case .analyzing:
                        analyzingStep
                    case .results:
                        resultsStep
                    }
                }
                .padding(24)
            }

            Divider()

            // Navigation bar
            navigationBar
                .padding(.horizontal, 24)
                .padding(.vertical, 12)
        }
        .frame(width: 700, height: 620)
    }

    // MARK: - Step Indicator

    private var stepIndicator: some View {
        HStack(spacing: 0) {
            ForEach(CheckInStep.intakeSteps, id: \.rawValue) { step in
                HStack(spacing: 6) {
                    Circle()
                        .fill(stepColor(step))
                        .frame(width: 10, height: 10)

                    Text(step.title)
                        .font(.caption.weight(currentStep == step ? .semibold : .regular))
                        .foregroundStyle(currentStep == step ? .primary : .secondary)
                }
                .onTapGesture {
                    // Allow jumping to completed steps
                    if step.rawValue < currentStep.rawValue {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            currentStep = step
                        }
                    }
                }

                if step != .review {
                    Image(systemName: "chevron.right")
                        .font(.caption2)
                        .foregroundStyle(.quaternary)
                        .padding(.horizontal, 8)
                }
            }
        }
    }

    private func stepColor(_ step: CheckInStep) -> Color {
        if step == currentStep {
            return .accentColor
        } else if step.rawValue < currentStep.rawValue {
            return .green
        } else {
            return Color(NSColor.separatorColor)
        }
    }

    // MARK: - Navigation Bar

    private var navigationBar: some View {
        HStack {
            if currentStep == .results {
                Button("Discard") { dismiss() }
                    .keyboardShortcut(.cancelAction)
            } else if currentStep != .analyzing {
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)
            }

            Spacer()

            if currentStep.rawValue > 0 && currentStep.rawValue <= CheckInStep.review.rawValue {
                Button("Back") {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        currentStep = CheckInStep(rawValue: currentStep.rawValue - 1) ?? .chiefComplaint
                    }
                }
            }

            if currentStep == .review {
                Button {
                    runAnalysis()
                } label: {
                    Label("Run MedGemma Analysis", systemImage: "brain")
                }
                .buttonStyle(.borderedProminent)
                .disabled(chiefComplaint.isEmpty)
            } else if currentStep == .results {
                Button {
                    saveCase()
                } label: {
                    Label("Save Case", systemImage: "checkmark.circle.fill")
                }
                .buttonStyle(.borderedProminent)
            } else if currentStep != .analyzing {
                Button("Next") {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        currentStep = CheckInStep(rawValue: currentStep.rawValue + 1) ?? .review
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(!isCurrentStepValid)
                .keyboardShortcut(.defaultAction)
            }
        }
    }

    // MARK: - Step 1: Chief Complaint

    private var chiefComplaintStep: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 4) {
                Text("What brings the patient in today?")
                    .font(.title2.weight(.semibold))
                Text("Describe the primary reason for the visit")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            VStack(alignment: .leading, spacing: 12) {
                Text("Chief Complaint")
                    .font(.headline)
                TextEditor(text: $chiefComplaint)
                    .font(.body)
                    .frame(minHeight: 100)
                    .scrollContentBackground(.hidden)
                    .padding(8)
                    .background(Color(NSColor.controlBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color(NSColor.separatorColor), lineWidth: 1)
                    )
            }

            HStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Onset")
                        .font(.headline)
                    HStack(spacing: 8) {
                        TextField("#", text: $onsetValue)
                            .textFieldStyle(.roundedBorder)
                            .frame(width: 60)
                        Picker("Unit", selection: $onsetUnit) {
                            ForEach(OnsetUnit.allCases, id: \.self) { unit in
                                Text(unit.rawValue).tag(unit)
                            }
                        }
                        .labelsHidden()
                        .frame(width: 100)
                        Text("ago")
                            .foregroundStyle(.secondary)
                    }
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Severity *")
                        .font(.headline)
                    Picker("Severity", selection: $severity) {
                        Text("Select").tag(nil as PatientIntake.Severity?)
                        ForEach(PatientIntake.Severity.allCases, id: \.self) { sev in
                            Text(sev.rawValue).tag(sev as PatientIntake.Severity?)
                        }
                    }
                    .labelsHidden()
                }
            }
        }
    }

    // MARK: - Step 2: Patient Details

    private var patientDetailsStep: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Patient Details")
                    .font(.title2.weight(.semibold))
                Text("Demographics, symptoms, and vital signs")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // Demographics row
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Age *")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                    TextField("Years", text: $age)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 70)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Sex at Birth *")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                    Picker("Sex", selection: $sex) {
                        Text("Select").tag(nil as BiologicalSex?)
                        ForEach(BiologicalSex.allCases, id: \.self) { s in
                            Text(s.rawValue).tag(s as BiologicalSex?)
                        }
                    }
                    .labelsHidden()
                }

                if sex == .female {
                    Toggle("Pregnant", isOn: $isPregnant)
                        .padding(.top, 16)
                }
            }

            // Symptoms
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 4) {
                    Text("Symptoms *")
                        .font(.headline)
                    if !symptomsText.isEmpty && symptomsText.count < 10 {
                        Text("(minimum 10 characters)")
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }
                }
                TextField("Comma-separated (e.g., chest pain, shortness of breath, nausea)", text: $symptomsText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(2...4)
            }

            // Vital Signs (standard 6)
            VStack(alignment: .leading, spacing: 10) {
                Text("Vital Signs")
                    .font(.headline)

                HStack(spacing: 12) {
                    vitalField("Weight (lbs)", text: $weight, width: nil)
                    vitalField("Height (in)", text: $height, width: nil)
                    vitalField("BP (e.g. 120/80)", text: $bloodPressure, width: nil)
                }

                HStack(spacing: 12) {
                    vitalField("Heart Rate (BPM)", text: $heartRate, width: nil)
                    vitalField("Temperature (°F)", text: $temperature, width: nil)
                    vitalField("Pulse Ox (%)", text: $oxygenSaturation, width: nil)
                }

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
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private func vitalField(_ label: String, text: Binding<String>, width: CGFloat?) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
            TextField("", text: text)
                .textFieldStyle(.roundedBorder)
                .frame(maxWidth: width ?? .infinity)
        }
    }

    // MARK: - Step 3: Medical Background

    private var medicalBackgroundStep: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Medical Background")
                    .font(.title2.weight(.semibold))
                Text("History, medications, allergies, and imaging")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Medical History")
                    .font(.headline)
                TextField("Comma-separated (e.g., hypertension, diabetes, asthma)", text: $medicalHistoryText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(2...4)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Current Medications")
                    .font(.headline)
                TextField("Comma-separated (e.g., lisinopril 10mg, metformin 500mg)", text: $medicationsText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(2...4)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Allergies")
                    .font(.headline)
                TextField("Comma-separated (e.g., penicillin, sulfa drugs)", text: $allergiesText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(2...4)
            }

            // Medical Images — UI hidden for competition submission; vision pipeline code retained
            // VStack { ... image picker UI ... }
        }
    }

    // MARK: - Step 4: Review

    private var reviewStep: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Review & Confirm")
                    .font(.title2.weight(.semibold))
                Text("Verify the information before running MedGemma analysis")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // Summary cards
            reviewCard("Chief Complaint", step: .chiefComplaint) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(chiefComplaint)
                        .font(.body)
                    HStack {
                        if !onsetValue.isEmpty {
                            Label("\(onsetValue) \(onsetUnit.rawValue) ago", systemImage: "clock")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        if let severity {
                            Label(severity.rawValue, systemImage: "gauge.with.dots.needle.33percent")
                                .font(.caption)
                                .foregroundStyle(severityColor)
                        }
                    }
                }
            }

            reviewCard("Patient Details", step: .patientDetails) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 12) {
                        if !age.isEmpty { Text("Age: \(age)").font(.caption) }
                        if let sex { Text("Sex at Birth: \(sex.rawValue)").font(.caption) }
                        if isPregnant { Text("Pregnant").font(.caption).foregroundStyle(.pink) }
                    }
                    if !symptomsText.isEmpty {
                        Text("Symptoms: \(symptomsText)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    if hasAnyVitals {
                        Text("Vitals recorded")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            reviewCard("Medical Background", step: .medicalBackground) {
                VStack(alignment: .leading, spacing: 4) {
                    if !medicalHistoryText.isEmpty {
                        Text("History: \(medicalHistoryText)")
                            .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                    }
                    if !medicationsText.isEmpty {
                        Text("Meds: \(medicationsText)")
                            .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                    }
                    if !allergiesText.isEmpty {
                        Text("Allergies: \(allergiesText)")
                            .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                    }
                    if medicalHistoryText.isEmpty && medicationsText.isEmpty && allergiesText.isEmpty {
                        Text("None provided")
                            .font(.caption).foregroundStyle(.tertiary)
                    }
                }
            }

            // Disclaimer
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "info.circle.fill")
                    .foregroundStyle(.blue)
                Text("MedGemma analysis is for educational purposes only. Not a substitute for professional medical advice.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()
            .background(Color.blue.opacity(0.05))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private func reviewCard<Content: View>(_ title: String, step: CheckInStep, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Button("Edit") {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        currentStep = step
                    }
                }
                .font(.caption)
                .buttonStyle(.plain)
                .foregroundStyle(Color.accentColor)
            }
            content()
        }
        .padding(12)
        .background(Color(NSColor.controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var severityColor: Color {
        switch severity {
        case .mild: .green
        case .moderate: .yellow
        case .severe: .orange
        case .critical: .red
        case nil: .secondary
        }
    }

    // MARK: - Step 5: Analyzing

    private var analyzingStep: some View {
        VStack(spacing: 24) {
            Spacer()

            ProgressView()
                .scaleEffect(1.5)
                .padding(.bottom, 8)

            Text("Running MedGemma Analysis")
                .font(.title2.weight(.semibold))

            if let step = currentReasoningStep {
                VStack(spacing: 8) {
                    Text("Step \(step.step) of 5: \(step.title)")
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(.secondary)

                    Text(String(step.content.prefix(200)))
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                        .lineLimit(3)
                        .frame(maxWidth: 400)
                }
            } else {
                Text("Preparing patient data...")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if let error = workflowError {
                VStack(spacing: 8) {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.center)

                    Button("Retry") { runAnalysis() }
                        .buttonStyle(.bordered)
                }
            }

            Spacer()
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Step 6: Results (Editable)

    private var resultsStep: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Header
            HStack {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .font(.title2)
                Text("Analysis Complete")
                    .font(.title2.weight(.semibold))
                Spacer()
                if let metrics = workflowResult?.performanceMetrics {
                    Text(String(format: "%.1fs", metrics.totalWorkflowMs / 1000))
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                }
            }

            // Safety Alerts
            if let result = workflowResult, !result.safetyAlerts.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Safety Alerts")
                        .font(.headline)
                    ForEach(result.safetyAlerts) { alert in
                        HStack(spacing: 6) {
                            Image(systemName: alert.severity == .critical ? "exclamationmark.octagon.fill" : "exclamationmark.triangle.fill")
                                .foregroundStyle(alert.severity == .critical ? .red : .orange)
                                .font(.caption)
                            Text(alert.message)
                                .font(.caption)
                        }
                    }
                }
                .padding()
                .background(Color.red.opacity(0.05))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            // Editable Triage
            VStack(alignment: .leading, spacing: 8) {
                Text("Triage Assessment")
                    .font(.headline)
                Picker("Triage Level", selection: $editableTriageLevel) {
                    ForEach(MedicalWorkflowResult.TriageLevel.allCases, id: \.self) { level in
                        Text(level.rawValue).tag(level)
                    }
                }
                .labelsHidden()
                .padding(8)
                .background(triageBackground(editableTriageLevel))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            // Editable Diagnoses
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Differential Diagnosis")
                        .font(.headline)
                    Spacer()
                    Button {
                        editableDiagnoses.append(Diagnosis(condition: "", probability: 0.5, rationale: ""))
                    } label: {
                        Label("Add", systemImage: "plus.circle")
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(Color.accentColor)
                }

                ForEach($editableDiagnoses) { $dx in
                    HStack(spacing: 8) {
                        TextField("Condition", text: $dx.condition)
                            .textFieldStyle(.roundedBorder)
                        TextField("Rationale", text: $dx.rationale)
                            .textFieldStyle(.roundedBorder)
                            .foregroundStyle(.secondary)
                        Button {
                            editableDiagnoses.removeAll { $0.id == dx.id }
                        } label: {
                            Image(systemName: "trash")
                                .foregroundStyle(.red.opacity(0.6))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            // Editable Actions
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Recommended Actions")
                        .font(.headline)
                    Spacer()
                    Button {
                        editableActions.append(RecommendedAction(action: "", priority: .medium))
                    } label: {
                        Label("Add", systemImage: "plus.circle")
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(Color.accentColor)
                }

                ForEach($editableActions) { $action in
                    HStack(spacing: 8) {
                        Picker("", selection: $action.priority) {
                            ForEach(RecommendedAction.ActionPriority.allCases, id: \.self) { p in
                                Text(p.rawValue).tag(p)
                            }
                        }
                        .labelsHidden()
                        .frame(width: 100)

                        TextField("Action", text: $action.action)
                            .textFieldStyle(.roundedBorder)

                        Button {
                            editableActions.removeAll { $0.id == action.id }
                        } label: {
                            Image(systemName: "trash")
                                .foregroundStyle(.red.opacity(0.6))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            // Reasoning steps (collapsed)
            if let result = workflowResult {
                DisclosureGroup("Clinical Reasoning (\(result.reasoning.count) steps)") {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(result.reasoning) { step in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text("Step \(step.step): \(step.title)")
                                        .font(.caption.weight(.semibold))
                                    Spacer()
                                    Text(String(format: "%.1fs", step.durationMs / 1000))
                                        .font(.caption2.monospaced())
                                        .foregroundStyle(.blue)
                                }
                                Text(step.content)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(8)
                            .background(Color(NSColor.controlBackgroundColor))
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                        }
                    }
                    .padding(.top, 4)
                }
                .font(.subheadline.weight(.medium))
            }
        }
    }

    private func triageBackground(_ level: MedicalWorkflowResult.TriageLevel) -> Color {
        switch level {
        case .emergency: Color.red.opacity(0.15)
        case .urgent: Color.orange.opacity(0.15)
        case .semiUrgent: Color.yellow.opacity(0.15)
        case .nonUrgent: Color.blue.opacity(0.1)
        case .selfCare: Color.green.opacity(0.1)
        case .undetermined: Color.gray.opacity(0.15)
        }
    }

    // MARK: - Actions

    private func runAnalysis() {
        let intake = buildIntake()

        withAnimation(.easeInOut(duration: 0.2)) {
            currentStep = .analyzing
        }
        isRunningWorkflow = true
        workflowError = nil
        currentReasoningStep = nil

        Task { @MainActor in
            do {
                let result = try await MedicalWorkflowEngine.executeWorkflow(
                    intake: intake,
                    disclaimerConfirmed: true,
                    onProgress: { step in
                        Task { @MainActor in
                            currentReasoningStep = step
                        }
                    }
                )

                workflowResult = result
                editableTriageLevel = result.triageLevel
                editableDiagnoses = result.differentialDiagnoses
                editableActions = result.recommendedActions
                isRunningWorkflow = false

                if result.isPartial {
                    workflowError = "Partial results: \(result.incompleteReason ?? "Some steps could not complete.")"
                }

                withAnimation(.easeInOut(duration: 0.3)) {
                    currentStep = .results
                }

            } catch {
                isRunningWorkflow = false
                workflowError = error.localizedDescription
                logger.error("Workflow failed: \(error)")
            }
        }
    }

    private func saveCase() {
        let intake = buildIntake()

        // Apply edits to result
        var finalResult = workflowResult
        finalResult?.triageLevel = editableTriageLevel
        finalResult?.differentialDiagnoses = editableDiagnoses
        finalResult?.recommendedActions = editableActions

        let medicalCase = MedicalCase(
            intake: intake,
            result: finalResult,
            status: finalResult != nil ? .completed : .pending
        )

        logger.info("Saving case with triage: \(editableTriageLevel.rawValue), \(editableDiagnoses.count) diagnoses, \(editableActions.count) actions")
        onComplete(medicalCase)
        dismiss()
    }

    private func buildIntake() -> PatientIntake {
        let symptoms = symptomsText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
        let history = medicalHistoryText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
        let meds = medicationsText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
        let allergies = allergiesText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }

        var tempF: Double?
        if let raw = Double(temperature) {
            tempF = raw <= 50 ? (raw * 9.0 / 5.0 + 32) : raw
        }
        let vitals: VitalSigns? = hasAnyVitals ? VitalSigns(
            heartRate: Int(heartRate),
            bloodPressure: bloodPressure.isEmpty ? nil : bloodPressure,
            temperature: tempF,
            oxygenSaturation: Int(oxygenSaturation),
            weight: Double(weight),
            height: Double(height)
        ) : nil

        return PatientIntake(
            patientId: patientId,
            age: Int(age),
            sex: sex,
            isPregnant: isPregnant,
            chiefComplaint: chiefComplaint,
            symptoms: symptoms,
            onsetTime: onsetValue.isEmpty ? "" : "\(onsetValue) \(onsetUnit.rawValue.lowercased()) ago",
            severity: severity ?? .moderate,
            vitalSigns: vitals,
            medicalHistory: history,
            currentMedications: meds,
            allergies: allergies,
            attachedImagePaths: attachedImagePaths
        )
    }

    // MARK: - Step Validation

    private var isCurrentStepValid: Bool {
        switch currentStep {
        case .chiefComplaint:
            return !chiefComplaint.trimmingCharacters(in: .whitespaces).isEmpty
                && !onsetValue.isEmpty
                && severity != nil
        case .patientDetails:
            return !age.isEmpty
                && Int(age) != nil
                && sex != nil
                && symptomsText.count >= 10
        case .medicalBackground, .review:
            return true
        case .analyzing, .results:
            return true
        }
    }

    // MARK: - Vital Validation

    private var hasAnyVitals: Bool {
        !heartRate.isEmpty || !bloodPressure.isEmpty || !temperature.isEmpty ||
        !oxygenSaturation.isEmpty || !weight.isEmpty || !height.isEmpty
    }

    private var vitalValidationWarnings: [String] {
        var warnings: [String] = []
        if let hr = Int(heartRate) {
            if hr < 20 || hr > 300 { warnings.append("Heart rate \(hr) outside physiologic range (20-300)") }
        }
        if let spo2 = Int(oxygenSaturation) {
            if spo2 > 100 { warnings.append("SpO2 cannot exceed 100%") }
            if spo2 < 0 { warnings.append("SpO2 cannot be negative") }
        }
        if let temp = Double(temperature) {
            if temp <= 50 {
                warnings.append("Looks like Celsius — will auto-convert to \(String(format: "%.1f°F", temp * 9.0 / 5.0 + 32))")
            } else if temp < 80 || temp > 115 {
                warnings.append("Temperature \(String(format: "%.1f", temp))°F outside expected range")
            }
        }
        if !bloodPressure.isEmpty {
            let parts = bloodPressure.components(separatedBy: "/")
            if parts.count != 2 || Int(parts[0].trimmingCharacters(in: .whitespaces)) == nil || Int(parts[1].trimmingCharacters(in: .whitespaces)) == nil {
                warnings.append("BP should be systolic/diastolic (e.g. 120/80)")
            } else if let sys = Int(parts[0].trimmingCharacters(in: .whitespaces)),
                      let dia = Int(parts[1].trimmingCharacters(in: .whitespaces)) {
                if sys < 60 || sys > 260 { warnings.append("Systolic BP \(sys) outside range (60-260)") }
                if dia < 30 || dia > 160 { warnings.append("Diastolic BP \(dia) outside range (30-160)") }
                if dia >= sys { warnings.append("Diastolic should be lower than systolic") }
            }
        }
        return warnings
    }

    // MARK: - Image Picker

    private func pickImages() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.image, .png, .jpeg, .heic, .tiff, .pdf]
        panel.message = "Select medical images (X-rays, lab results, skin photos)"

        guard panel.runModal() == .OK else { return }
        attachedImagePaths.append(contentsOf: panel.urls.map(\.path))
    }
}
