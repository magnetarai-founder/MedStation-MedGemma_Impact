//
//  MedicalWorkflowEngine.swift
//  MagnetarStudio
//
//  Agentic workflow engine for multi-step medical reasoning using MedGemma.
//  Executes a 5-step pipeline: Symptom Analysis → Triage → Differential Dx →
//  Risk Stratification → Recommendations. Each step feeds context to the next.
//
//  MedGemma Impact Challenge (Kaggle 2026) — Agentic Medical Workflow.
//

import AppKit
import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "MedicalWorkflowEngine")

// MARK: - Medical Workflow Engine

struct MedicalWorkflowEngine {

    // MARK: - Workflow Execution

    @MainActor
    static func executeWorkflow(
        intake: PatientIntake,
        onProgress: @escaping (ReasoningStep) -> Void
    ) async throws -> MedicalWorkflowResult {
        logger.info("Starting medical workflow for intake \(intake.id)")

        let service = MedicalAIService.shared

        if service.modelStatus != .ready && service.modelStatus != .installed {
            await service.ensureModelReady()
        }

        guard service.modelStatus == .ready || service.modelStatus == .installed else {
            throw MedicalAIError.modelNotReady
        }

        var reasoningSteps: [ReasoningStep] = []
        var stepDurations: [String: Double] = [:]
        var imageAnalysisMs: Double?
        let workflowStart = ContinuousClock.now
        var patientContext = formatPatientContext(intake)

        // Pre-step: Analyze attached medical images (on-device Vision pipeline)
        if !intake.attachedImagePaths.isEmpty {
            let imageStart = ContinuousClock.now
            let imageContext = await analyzeAttachedImages(intake.attachedImagePaths)
            let imgElapsed = imageStart.duration(to: .now)
            imageAnalysisMs = Double(imgElapsed.components.seconds) * 1000 + Double(imgElapsed.components.attoseconds) / 1_000_000_000_000_000

            if !imageContext.isEmpty {
                patientContext += "\n\nMedical Image Analysis:\n\(imageContext)"
                logger.info("Image analysis completed in \(String(format: "%.0f", imageAnalysisMs ?? 0))ms for \(intake.attachedImagePaths.count) images")
            }
        }

        // Step 1: Symptom Analysis
        let symptomAnalysis = try await executeStep(
            stepNumber: 1,
            title: "Symptom Analysis",
            prompt: """
            Analyze the patient's symptoms and identify:
            1. Primary symptoms and their characteristics
            2. Red flag symptoms requiring immediate attention
            3. Associated symptoms suggesting specific conditions
            4. Timeline and progression patterns

            Be specific and evidence-based.
            """,
            patientContext: patientContext,
            service: service
        )
        reasoningSteps.append(symptomAnalysis)
        onProgress(symptomAnalysis)

        // Step 2: Triage Assessment (context: symptoms analysis)
        let triageAssessment = try await executeStep(
            stepNumber: 2,
            title: "Triage Assessment",
            prompt: """
            Based on the symptom analysis, determine the appropriate triage level:
            - Emergency (life-threatening, call 911)
            - Urgent (seek care within 2-4 hours)
            - Semi-Urgent (see doctor within 24 hours)
            - Non-Urgent (schedule appointment this week)
            - Self-Care (monitor at home with specific instructions)

            Justify your triage decision with clinical reasoning.

            State the triage level clearly at the start of your response.
            """,
            patientContext: patientContext + "\n\nSymptom Analysis:\n\(symptomAnalysis.content)",
            service: service
        )
        reasoningSteps.append(triageAssessment)
        onProgress(triageAssessment)

        let triageLevel = extractTriageLevel(from: triageAssessment.content)

        // Step 3: Differential Diagnosis (context: triage + symptoms)
        let differentialDx = try await executeStep(
            stepNumber: 3,
            title: "Differential Diagnosis",
            prompt: """
            Generate a ranked differential diagnosis list with:
            1. Top 3-5 most likely conditions
            2. Probability estimate for each (high/medium/low likelihood)
            3. Clinical reasoning supporting each diagnosis
            4. Key distinguishing features between conditions

            Format as a numbered list. Start each entry with the condition name.
            """,
            patientContext: patientContext + "\n\nTriage: \(triageLevel.rawValue)\n\nSymptom Analysis:\n\(symptomAnalysis.content.prefix(500))",
            service: service
        )
        reasoningSteps.append(differentialDx)
        onProgress(differentialDx)

        let diagnoses = parseDifferentialDiagnoses(from: differentialDx.content)

        // Step 4: Risk Stratification (context: diagnoses + triage)
        let riskAssessment = try await executeStep(
            stepNumber: 4,
            title: "Risk Stratification",
            prompt: """
            Identify risk factors and potential complications:
            1. Patient-specific risk factors (age, comorbidities, medications)
            2. Symptoms suggesting serious complications
            3. Factors requiring immediate intervention
            4. Warning signs to monitor going forward

            Be specific about what increases risk for this patient.
            """,
            patientContext: patientContext + "\n\nDifferential: \(diagnoses.map(\.condition).joined(separator: ", "))",
            service: service
        )
        reasoningSteps.append(riskAssessment)
        onProgress(riskAssessment)

        // Step 5: Recommendations (context: everything)
        let recommendations = try await executeStep(
            stepNumber: 5,
            title: "Recommended Actions",
            prompt: """
            Provide actionable recommendations:
            1. Immediate actions needed (if any)
            2. When and where to seek medical care
            3. Diagnostic tests to request from a healthcare provider
            4. Self-care measures (if appropriate)
            5. Red flag symptoms that require immediate emergency care

            Prioritize recommendations by urgency. Format as a numbered list.
            """,
            patientContext: patientContext + "\n\nTriage: \(triageLevel.rawValue)\n\nRisk Factors:\n\(riskAssessment.content.prefix(300))",
            service: service
        )
        reasoningSteps.append(recommendations)
        onProgress(recommendations)

        let actions = parseRecommendedActions(from: recommendations.content, triageLevel: triageLevel)

        // Capture step durations from timing data
        for step in reasoningSteps {
            stepDurations[step.title] = step.durationMs
        }

        let elapsed = workflowStart.duration(to: .now)
        let totalMs = Double(elapsed.components.seconds) * 1000 + Double(elapsed.components.attoseconds) / 1_000_000_000_000_000
        let metrics = PerformanceMetrics(
            totalWorkflowMs: totalMs,
            stepDurations: stepDurations,
            modelName: "alibayram/medgemma:4b",
            modelParameterCount: "4B",
            deviceThermalState: .init(from: ProcessInfo.processInfo),
            imageAnalysisMs: imageAnalysisMs
        )

        var result = MedicalWorkflowResult(
            intakeId: intake.id,
            triageLevel: triageLevel,
            differentialDiagnoses: diagnoses,
            recommendedActions: actions,
            reasoning: reasoningSteps,
            performanceMetrics: metrics,
            disclaimer: standardDisclaimer,
            generatedAt: Date()
        )

        // Post-processing: HAI-DEF safety validation
        result.safetyAlerts = MedicalSafetyGuard.validate(result, intake: intake)

        // HAI-DEF audit logging
        MedicalAuditLogger.logWorkflowExecution(
            intake: intake,
            result: result,
            imageAnalysisPerformed: !intake.attachedImagePaths.isEmpty
        )

        logger.info("Medical workflow completed in \(String(format: "%.0f", totalMs))ms: \(triageLevel.rawValue), \(diagnoses.count) diagnoses, \(actions.count) actions")
        return result
    }

    // MARK: - Step Execution

    private static func executeStep(
        stepNumber: Int,
        title: String,
        prompt: String,
        patientContext: String,
        service: MedicalAIService
    ) async throws -> ReasoningStep {
        logger.debug("Executing step \(stepNumber): \(title)")

        let stepStart = ContinuousClock.now
        let response = try await service.generateWorkflowStep(
            stepPrompt: prompt,
            patientContext: patientContext
        )
        let stepElapsed = stepStart.duration(to: .now)
        let stepMs = Double(stepElapsed.components.seconds) * 1000 + Double(stepElapsed.components.attoseconds) / 1_000_000_000_000_000

        logger.info("Step \(stepNumber) (\(title)) completed in \(String(format: "%.0f", stepMs))ms")

        return ReasoningStep(
            step: stepNumber,
            title: title,
            content: response,
            durationMs: stepMs,
            timestamp: Date()
        )
    }

    // MARK: - Context Formatting

    private static func formatPatientContext(_ intake: PatientIntake) -> String {
        var context = """
        Patient ID: \(intake.patientId.isEmpty ? "Anonymous" : intake.patientId)
        Chief Complaint: \(intake.chiefComplaint)
        Onset: \(intake.onsetTime)
        Severity: \(intake.severity.rawValue)
        """

        if !intake.symptoms.isEmpty {
            context += "\nSymptoms: \(intake.symptoms.joined(separator: ", "))"
        }

        if let vitals = intake.vitalSigns {
            context += "\nVital Signs:"
            if let hr = vitals.heartRate { context += "\n  HR: \(hr) bpm" }
            if let bp = vitals.bloodPressure { context += "\n  BP: \(bp)" }
            if let temp = vitals.temperature { context += "\n  Temp: \(String(format: "%.1f", temp))°F" }
            if let rr = vitals.respiratoryRate { context += "\n  RR: \(rr)/min" }
            if let spo2 = vitals.oxygenSaturation { context += "\n  SpO2: \(spo2)%" }
        }

        if !intake.medicalHistory.isEmpty {
            context += "\nMedical History: \(intake.medicalHistory.joined(separator: ", "))"
        }

        if !intake.currentMedications.isEmpty {
            context += "\nMedications: \(intake.currentMedications.joined(separator: ", "))"
        }

        if !intake.allergies.isEmpty {
            context += "\nAllergies: \(intake.allergies.joined(separator: ", "))"
        }

        return context
    }

    // MARK: - Image Analysis

    private static func analyzeAttachedImages(_ imagePaths: [String]) async -> String {
        var contextParts: [String] = []

        for path in imagePaths {
            guard let nsImage = NSImage(contentsOfFile: path) else {
                logger.warning("Could not load image at path: \(path)")
                continue
            }

            do {
                let result = try await ImageAnalysisService.shared.analyze(nsImage)
                let aiContext = result.generateAIContext()

                if !aiContext.isEmpty {
                    let filename = (path as NSString).lastPathComponent
                    contextParts.append("[\(filename)]:\n\(aiContext)")
                }

                let layerInfo = result.layerTimings.map { "\($0.key): \(String(format: "%.0f", $0.value * 1000))ms" }.joined(separator: ", ")
                logger.info("Analyzed \((path as NSString).lastPathComponent): \(result.layersExecuted.count) layers (\(layerInfo))")
            } catch {
                logger.error("Image analysis failed for \(path): \(error.localizedDescription)")
            }
        }

        return contextParts.joined(separator: "\n\n")
    }

    // MARK: - Output Parsing

    private static func extractTriageLevel(from text: String) -> MedicalWorkflowResult.TriageLevel {
        let lower = text.lowercased()

        if lower.contains("emergency") || lower.contains("911") || lower.contains("life-threatening") {
            return .emergency
        } else if lower.contains("semi-urgent") || lower.contains("within 24") {
            return .semiUrgent
        } else if lower.contains("urgent") && !lower.contains("non-urgent") {
            return .urgent
        } else if lower.contains("non-urgent") || lower.contains("schedule appointment") {
            return .nonUrgent
        } else if lower.contains("self-care") || lower.contains("monitor at home") {
            return .selfCare
        }

        return .semiUrgent
    }

    private static func parseDifferentialDiagnoses(from text: String) -> [Diagnosis] {
        var diagnoses: [Diagnosis] = []
        let lines = text.components(separatedBy: .newlines)
        var currentCondition = ""
        var currentRationale = ""
        var currentProbability = 0.6

        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespaces)

            // Match numbered/bulleted list items (e.g. "1. Acute Appendicitis", "- Viral Gastroenteritis")
            let isListItem = trimmed.first?.isNumber == true || trimmed.hasPrefix("-") || trimmed.hasPrefix("*")

            if isListItem && trimmed.count > 3 {
                // Save previous
                if !currentCondition.isEmpty {
                    diagnoses.append(Diagnosis(
                        condition: currentCondition,
                        probability: currentProbability,
                        rationale: currentRationale.trimmingCharacters(in: .whitespaces)
                    ))
                }

                // Extract condition name (strip list prefix)
                var conditionText = trimmed
                if let dotIndex = conditionText.firstIndex(of: ".") {
                    conditionText = String(conditionText[conditionText.index(after: dotIndex)...])
                        .trimmingCharacters(in: .whitespaces)
                } else if conditionText.hasPrefix("-") || conditionText.hasPrefix("*") {
                    conditionText = String(conditionText.dropFirst())
                        .trimmingCharacters(in: .whitespaces)
                }

                // Extract probability from keywords
                let lowerLine = trimmed.lowercased()
                if lowerLine.contains("high") || lowerLine.contains("most likely") || lowerLine.contains("likely") {
                    currentProbability = 0.8
                } else if lowerLine.contains("moderate") || lowerLine.contains("possible") || lowerLine.contains("medium") {
                    currentProbability = 0.5
                } else if lowerLine.contains("low") || lowerLine.contains("unlikely") || lowerLine.contains("less likely") {
                    currentProbability = 0.2
                } else {
                    currentProbability = 0.6
                }

                // Take just the condition name (before any dash/colon explanation)
                if let separatorIndex = conditionText.firstIndex(where: { $0 == ":" || $0 == "—" || $0 == "–" }) {
                    currentCondition = String(conditionText[..<separatorIndex])
                        .trimmingCharacters(in: .whitespaces)
                    currentRationale = String(conditionText[conditionText.index(after: separatorIndex)...])
                        .trimmingCharacters(in: .whitespaces)
                } else {
                    currentCondition = conditionText
                    currentRationale = ""
                }
            } else if !trimmed.isEmpty && !currentCondition.isEmpty {
                currentRationale += (currentRationale.isEmpty ? "" : " ") + trimmed
            }
        }

        // Save last
        if !currentCondition.isEmpty {
            diagnoses.append(Diagnosis(
                condition: currentCondition,
                probability: currentProbability,
                rationale: currentRationale.trimmingCharacters(in: .whitespaces)
            ))
        }

        return Array(diagnoses.prefix(5))
    }

    private static func parseRecommendedActions(
        from text: String,
        triageLevel: MedicalWorkflowResult.TriageLevel
    ) -> [RecommendedAction] {
        var actions: [RecommendedAction] = []
        let lines = text.components(separatedBy: .newlines)

        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            let isListItem = trimmed.first?.isNumber == true || trimmed.hasPrefix("-") || trimmed.hasPrefix("*")

            guard isListItem && trimmed.count > 3 else { continue }

            // Strip list prefix
            var actionText = trimmed
            if let dotIndex = actionText.firstIndex(of: ".") {
                actionText = String(actionText[actionText.index(after: dotIndex)...])
                    .trimmingCharacters(in: .whitespaces)
            } else if actionText.hasPrefix("-") || actionText.hasPrefix("*") {
                actionText = String(actionText.dropFirst())
                    .trimmingCharacters(in: .whitespaces)
            }

            guard !actionText.isEmpty else { continue }

            // Determine priority
            var priority: RecommendedAction.ActionPriority = .medium
            let lowerAction = actionText.lowercased()

            if triageLevel == .emergency {
                priority = .immediate
            } else if lowerAction.contains("immediate") || lowerAction.contains("emergency") || lowerAction.contains("call 911") {
                priority = .immediate
            } else if lowerAction.contains("urgent") || lowerAction.contains("soon") || lowerAction.contains("today") {
                priority = .high
            } else if lowerAction.contains("monitor") || lowerAction.contains("watch") || lowerAction.contains("follow up") {
                priority = .low
            }

            actions.append(RecommendedAction(action: actionText, priority: priority))
        }

        return actions
    }

    // MARK: - Constants

    static let standardDisclaimer = """
    MEDICAL DISCLAIMER: This analysis is generated by an AI system (MedGemma) for educational \
    and informational purposes only. It is NOT a substitute for professional medical advice, \
    diagnosis, or treatment. Always seek the advice of your physician or other qualified health \
    provider with any questions you may have regarding a medical condition. Never disregard \
    professional medical advice or delay seeking it because of information from this system. \
    If you think you may have a medical emergency, call your doctor or 911 immediately.
    """
}
