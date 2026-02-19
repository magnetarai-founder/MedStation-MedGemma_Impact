//
//  MedicalWorkflowEngine.swift
//  MedStation
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

private let logger = Logger(subsystem: "com.medstation.app", category: "MedicalWorkflowEngine")

// MARK: - Medical Workflow Engine

struct MedicalWorkflowEngine {

    // MARK: - Workflow Execution

    @MainActor
    static func executeWorkflow(
        intake: PatientIntake,
        disclaimerConfirmed: Bool = true,
        onProgress: @escaping (ReasoningStep) -> Void
    ) async throws -> MedicalWorkflowResult {
        logger.info("Starting medical workflow for intake \(intake.id)")

        let service = MedicalAIService.shared

        if service.modelStatus != .ready {
            await service.ensureModelReady()
        }

        guard service.modelStatus == .ready else {
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

        // Track parsed outputs as we go — later steps depend on earlier ones
        var triageLevel: MedicalWorkflowResult.TriageLevel = .undetermined
        var diagnoses: [Diagnosis] = []
        var actions: [RecommendedAction] = []
        var incompleteReason: String?

        // Helper: build partial result from whatever we have so far
        func buildResult(partial: Bool) -> MedicalWorkflowResult {
            for step in reasoningSteps { stepDurations[step.title] = step.durationMs }
            let elapsed = workflowStart.duration(to: .now)
            let totalMs = Double(elapsed.components.seconds) * 1000 + Double(elapsed.components.attoseconds) / 1_000_000_000_000_000
            let metrics = PerformanceMetrics(
                totalWorkflowMs: totalMs,
                stepDurations: stepDurations,
                modelName: "google/medgemma-1.5-4b-it",
                modelParameterCount: "4B",
                deviceThermalState: .init(from: ProcessInfo.processInfo),
                imageAnalysisMs: imageAnalysisMs
            )
            return MedicalWorkflowResult(
                intakeId: intake.id,
                triageLevel: triageLevel,
                differentialDiagnoses: diagnoses,
                recommendedActions: actions,
                reasoning: reasoningSteps,
                performanceMetrics: metrics,
                disclaimer: standardDisclaimer,
                generatedAt: Date(),
                isPartial: partial,
                incompleteReason: incompleteReason
            )
        }

        // Step 1: Symptom Analysis — must succeed (no useful data without it)
        let symptomAnalysis = try await executeStep(
            stepNumber: 1,
            title: "Symptom Analysis",
            prompt: """
            Analyze the patient's symptoms. For each point, give 1-2 sentences max:
            1. Primary symptoms and characteristics
            2. Red flag symptoms requiring immediate attention
            3. Associated symptoms suggesting specific conditions
            4. Timeline and progression

            Be concise and evidence-based. Use bullet points.
            """,
            patientContext: patientContext,
            service: service
        )
        reasoningSteps.append(symptomAnalysis)
        onProgress(symptomAnalysis)

        // Steps 2-5: each wrapped for graceful degradation
        do {
            let triageAssessment = try await executeStep(
                stepNumber: 2,
                title: "Triage Assessment",
                prompt: """
                Your FIRST line must be exactly one of these (copy it verbatim):
                TRIAGE: Emergency
                TRIAGE: Urgent
                TRIAGE: Semi-Urgent
                TRIAGE: Non-Urgent
                TRIAGE: Self-Care

                Then justify in 2-3 sentences. Only classify as Emergency if immediately life-threatening RIGHT NOW.
                """,
                patientContext: patientContext + "\n\nSymptom Analysis:\n\(symptomAnalysis.content)",
                service: service
            )
            reasoningSteps.append(triageAssessment)
            onProgress(triageAssessment)
            triageLevel = extractTriageLevel(from: triageAssessment.content)
        } catch {
            logger.error("Triage step failed, returning partial results: \(error)")
            incompleteReason = "Triage assessment failed: \(error.localizedDescription)"
        }

        if incompleteReason == nil {
            do {
                let differentialDx = try await executeStep(
                    stepNumber: 3,
                    title: "Differential Diagnosis",
                    prompt: """
                    List top 3 most likely diagnoses. For each, one line:
                    [Number]. [Condition] (high/medium/low likelihood) — [1 sentence reasoning]

                    Be concise. No more than 3 conditions.
                    """,
                    patientContext: patientContext + "\n\nTriage: \(triageLevel.rawValue)\n\nSymptom Analysis:\n\(symptomAnalysis.content.prefix(500))",
                    service: service
                )
                reasoningSteps.append(differentialDx)
                onProgress(differentialDx)
                diagnoses = parseDifferentialDiagnoses(from: differentialDx.content)
            } catch {
                logger.error("Differential diagnosis step failed: \(error)")
                incompleteReason = "Differential diagnosis failed: \(error.localizedDescription)"
            }
        }

        if incompleteReason == nil {
            do {
                let riskAssessment = try await executeStep(
                    stepNumber: 4,
                    title: "Risk Stratification",
                    prompt: """
                    List key risk factors as bullet points (1 sentence each):
                    - Patient-specific risk factors
                    - Warning signs requiring immediate care
                    - Complications to monitor

                    Be concise. Max 5 bullet points.
                    """,
                    patientContext: patientContext + "\n\nDifferential: \(diagnoses.map(\.condition).joined(separator: ", "))",
                    service: service
                )
                reasoningSteps.append(riskAssessment)
                onProgress(riskAssessment)
            } catch {
                logger.error("Risk stratification step failed: \(error)")
                incompleteReason = "Risk stratification failed: \(error.localizedDescription)"
            }
        }

        if incompleteReason == nil {
            do {
                let riskContent = reasoningSteps.last(where: { $0.title == "Risk Stratification" })?.content ?? ""
                let recommendations = try await executeStep(
                    stepNumber: 5,
                    title: "Recommended Actions",
                    prompt: """
                    List 3-5 actionable recommendations, numbered by priority:
                    1. Most urgent action first
                    2. When/where to seek care
                    3. Key diagnostic tests
                    4. Red flags requiring emergency care

                    One sentence per recommendation.
                    """,
                    patientContext: patientContext + "\n\nTriage: \(triageLevel.rawValue)\n\nRisk Factors:\n\(riskContent.prefix(300))",
                    service: service
                )
                reasoningSteps.append(recommendations)
                onProgress(recommendations)
                actions = parseRecommendedActions(from: recommendations.content, triageLevel: triageLevel)
            } catch {
                logger.error("Recommendations step failed: \(error)")
                incompleteReason = "Recommendations failed: \(error.localizedDescription)"
            }
        }

        let isPartial = incompleteReason != nil
        var result = buildResult(partial: isPartial)

        // Post-processing: HAI-DEF safety validation
        result.safetyAlerts = MedicalSafetyGuard.validate(result, intake: intake)

        // HAI-DEF audit logging
        MedicalAuditLogger.logWorkflowExecution(
            intake: intake,
            result: result,
            imageAnalysisPerformed: !intake.attachedImagePaths.isEmpty,
            disclaimerConfirmed: disclaimerConfirmed
        )

        let totalMs = result.performanceMetrics?.totalWorkflowMs ?? 0
        if isPartial {
            logger.warning("Workflow completed PARTIALLY (\(reasoningSteps.count)/5 steps) in \(String(format: "%.0f", totalMs))ms: \(incompleteReason ?? "")")
        } else {
            logger.info("Medical workflow completed in \(String(format: "%.0f", totalMs))ms: \(triageLevel.rawValue), \(diagnoses.count) diagnoses, \(actions.count) actions")
        }
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

        if let age = intake.age {
            var ageNote = "\nAge: \(age) years"
            if age < 2 {
                ageNote += " (Neonate/Infant — use pediatric-specific differentials and dosing)"
            } else if age < 18 {
                ageNote += " (Pediatric — consider age-appropriate differentials, vital sign ranges differ)"
            } else if age > 65 {
                ageNote += " (Geriatric — consider polypharmacy, atypical presentations, frailty)"
            }
            context += ageNote
        }

        if let sex = intake.sex {
            context += "\nBiological Sex: \(sex.rawValue)"
        }

        if intake.isPregnant {
            context += "\n⚠️ PREGNANT — Consider pregnancy complications (eclampsia, ectopic, abruption), medication contraindications, and trimester-specific risks"
        }

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
            if let wt = vitals.weight { context += "\n  Weight: \(String(format: "%.0f", wt)) lbs" }
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

    static func extractTriageLevel(from text: String) -> MedicalWorkflowResult.TriageLevel {
        // Parse structured "TRIAGE: <level>" from the first few lines
        let lines = text.components(separatedBy: .newlines).prefix(3)
        for line in lines {
            let lower = line.lowercased().trimmingCharacters(in: .whitespaces)

            // Match "TRIAGE: <level>" format
            if lower.contains("triage:") || lower.contains("triage level:") {
                if lower.contains("self-care") || lower.contains("self care") { return .selfCare }
                if lower.contains("non-urgent") || lower.contains("nonurgent") { return .nonUrgent }
                if lower.contains("semi-urgent") || lower.contains("semiurgent") { return .semiUrgent }
                if lower.contains("emergency") { return .emergency }
                if lower.contains("urgent") { return .urgent }
            }

            // Fallback: check if first line starts with a level name directly
            if lower.hasPrefix("emergency") { return .emergency }
            if lower.hasPrefix("urgent") { return .urgent }
            if lower.hasPrefix("semi-urgent") { return .semiUrgent }
            if lower.hasPrefix("non-urgent") { return .nonUrgent }
            if lower.hasPrefix("self-care") || lower.hasPrefix("self care") { return .selfCare }
        }

        // Don't silently assume any level — surface uncertainty to the clinician
        logger.warning("Could not parse triage level from MedGemma output. Flagging as undetermined. Raw: \(text.prefix(200))")
        return .undetermined
    }

    static func parseDifferentialDiagnoses(from text: String) -> [Diagnosis] {
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

    static func parseRecommendedActions(
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
