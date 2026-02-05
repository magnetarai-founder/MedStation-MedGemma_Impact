//
//  SchedulerService.swift
//  MagnetarStudio
//
//  Simple scheduler for time-based automation triggers.
//  Checks scheduled rules periodically and fires them when due.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "Scheduler")

@MainActor @Observable
final class SchedulerService {
    static let shared = SchedulerService()

    private var checkTimer: Timer?
    private var lastChecked: Date = Date()
    var isRunning = false

    private init() {}

    // MARK: - Start / Stop

    func start() {
        guard !isRunning else { return }
        isRunning = true

        checkTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.checkScheduledRules()
            }
        }
        logger.info("Scheduler started (checking every 60s)")
    }

    func stop() {
        checkTimer?.invalidate()
        checkTimer = nil
        isRunning = false
        logger.info("Scheduler stopped")
    }

    // MARK: - Check

    private func checkScheduledRules() {
        guard FeatureFlags.shared.automations else { return }

        let now = Date()
        let scheduledRules = AutomationStore.shared.enabledRules.filter {
            if case .onSchedule = $0.trigger { return true }
            return false
        }

        for rule in scheduledRules {
            if case .onSchedule(let cron) = rule.trigger {
                if shouldRun(cron: cron, since: lastChecked, now: now) {
                    let context = TriggerContext(trigger: .onSchedule(cron: cron))
                    Task {
                        await AutomationStore.shared.evaluate(context: context)
                    }
                    logger.info("Scheduled rule fired: \(rule.name)")
                }
            }
        }

        lastChecked = now
    }

    // MARK: - Simple Cron Parsing

    /// Simplified cron: supports "every Xm", "every Xh", "daily HH:MM", "hourly".
    private func shouldRun(cron: String, since: Date, now: Date) -> Bool {
        let lower = cron.lowercased().trimmingCharacters(in: .whitespaces)

        // "every 5m" — every N minutes
        if lower.hasPrefix("every ") && lower.hasSuffix("m") {
            let numStr = lower.dropFirst(6).dropLast(1)
            guard let minutes = Int(numStr), minutes > 0 else { return false }
            return now.timeIntervalSince(since) >= Double(minutes * 60)
        }

        // "every 2h" — every N hours
        if lower.hasPrefix("every ") && lower.hasSuffix("h") {
            let numStr = lower.dropFirst(6).dropLast(1)
            guard let hours = Int(numStr), hours > 0 else { return false }
            return now.timeIntervalSince(since) >= Double(hours * 3600)
        }

        // "hourly" — every hour
        if lower == "hourly" {
            let cal = Calendar.current
            let sinceHour = cal.component(.hour, from: since)
            let nowHour = cal.component(.hour, from: now)
            return nowHour != sinceHour
        }

        // "daily HH:MM" — once per day at specific time
        if lower.hasPrefix("daily ") {
            let timePart = String(lower.dropFirst(6))
            let parts = timePart.split(separator: ":")
            guard parts.count == 2,
                  let hour = Int(parts[0]),
                  let minute = Int(parts[1]) else { return false }

            let cal = Calendar.current
            let nowHour = cal.component(.hour, from: now)
            let nowMinute = cal.component(.minute, from: now)

            // Check if we're in the target minute and haven't run yet this period
            return nowHour == hour && nowMinute == minute &&
                   now.timeIntervalSince(since) >= 60
        }

        return false
    }
}
