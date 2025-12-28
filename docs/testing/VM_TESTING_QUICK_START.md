# MagnetarStudio Emergency Mode - VM Testing Quick Start

**Purpose**: Get started with VM testing immediately
**Audience**: Developers ready to test Days 6-10
**Time Required**: 3-4 hours total across 3 phases
**Safety Level**: VM-only, zero dev machine risk

---

## 🚨 CRITICAL SAFETY FIRST

**READ THIS BEFORE PROCEEDING:**

### ✅ ONLY Test In:
- Isolated macOS virtual machines
- Disposable VM snapshots
- Test environments with fake data

### ❌ NEVER Test On:
- Your development Mac
- Production servers
- Any machine with real data
- VMs with network access to production

**If you're unsure, STOP and ask for guidance.**

---

## 📋 Prerequisites (10 minutes)

Before starting VM testing, ensure you have:

### Software Requirements

- [ ] **macOS VM Software** (choose one):
  - VMware Fusion (recommended)
  - Parallels Desktop
  - VirtualBox (free)

- [ ] **Fresh macOS VM**:
  - macOS 14.0 (Sonoma) or later
  - 20GB disk minimum
  - 4GB RAM minimum
  - NO network access to production systems
  - NO shared folders with host machine

- [ ] **Forensic Tools**:
  ```bash
  # Install PhotoRec/TestDisk
  brew install testdisk

  # Download Disk Drill (optional, manual)
  # https://www.cleverfiles.com/
  ```

- [ ] **MagnetarStudio Build**:
  - Debug build (for Phase 1 simulation)
  - Release build (for Phase 2 deletion)
  - Source code in VM or accessible via git

### VM Snapshot Strategy

**IMPORTANT**: Create VM snapshots before each phase so you can reset if needed.

```
VM-Clean-Install
├── Snapshot-1: Before setup_vm_test.sh (Phase 1)
├── Snapshot-2: After Phase 1 complete
├── Snapshot-3: Before Phase 2 (fresh setup_vm_test.sh run)
└── Snapshot-4: After wipe (for forensics)
```

---

## 🎯 Three Testing Phases Overview

| Phase | Days | Purpose | Duration | Destructive? |
|-------|------|---------|----------|--------------|
| **Phase 1** | 6-7 | Simulation (no deletion) | 30 min | ❌ No |
| **Phase 2** | 8-9 | Actual deletion | 45 min | ✅ Yes |
| **Phase 3** | 10 | Forensic analysis | 2 hours | ❌ No |

**Total Time**: ~3-4 hours (can be split across multiple days)

---

## 📅 PHASE 1: Simulation Testing (Days 6-7)

**Goal**: Verify emergency mode identifies all files WITHOUT deleting them
**Duration**: 30 minutes
**Destructive**: NO
**Build Required**: Debug build

### Step-by-Step

1. **Prepare VM** (5 minutes)
   ```bash
   # In your macOS VM terminal:
   cd ~/Documents
   git clone [your-magnetarstudio-repo] MagnetarStudio
   cd MagnetarStudio
   ```

2. **Create Test Data** (5 minutes)
   ```bash
   # Navigate to VM testing tools
   cd tools/vm_testing

   # Make scripts executable
   chmod +x setup_vm_test.sh verify_wipe.sh forensic_test.sh

   # Run setup script
   ./setup_vm_test.sh
   # Answer "yes" to VM confirmation
   ```

   **Expected Output**:
   ```
   ✅ VM Test Environment Setup Complete!
   Total test files: 150+
   Disk usage: ~160MB
   ```

3. **Build MagnetarStudio (Debug)** (10 minutes)
   ```bash
   cd /Users/[username]/Documents/MagnetarStudio

   # Open Xcode project
   open apps/native/MagnetarStudio.xcodeproj

   # In Xcode:
   # 1. Select "MagnetarStudio" scheme
   # 2. Set to "Debug" configuration
   # 3. Build: Cmd+B
   # 4. Run: Cmd+R
   ```

4. **Trigger Emergency Mode** (5 minutes)
   - Launch MagnetarStudio app in VM
   - Navigate to Settings > Security
   - Triple-click the panic button
   - Observe console output (Cmd+Shift+Y in Xcode)

5. **Verify Simulation** (5 minutes)
   ```bash
   # Check that files still exist
   ls -la ~/.magnetar
   ls -la ~/.elohimos_backups
   ls -la ~/Library/Caches/com.magnetarstudio.app

   # All directories should still be present
   ```

### Expected Console Output (Phase 1)

```
🚨 EMERGENCY MODE TRIGGERED
⚠️  SIMULATION MODE: No files will be deleted

🔍 Scanning for files to wipe...
   Found: ~/.magnetar (9 files)
   Found: ~/.elohimos_backups (2 files)
   Found: ~/Library/Caches/com.magnetarstudio.app (70 files)
   [... 8 more categories ...]

📊 Wipe Plan:
   - 11 categories identified
   - 150+ files would be deleted
   - 0 files actually deleted (simulation)

✅ Simulation complete - check console for details
```

### Success Criteria (Phase 1)

- ✅ Emergency mode triggers successfully
- ✅ Console shows all 11 file categories identified
- ✅ Console shows "SIMULATION MODE" message
- ✅ All files still exist after simulation
- ✅ App still runs normally

**If all criteria pass, proceed to Phase 2.**

---

## 🔥 PHASE 2: Actual Deletion Testing (Days 8-9)

**Goal**: Test actual emergency wipe with real file deletion
**Duration**: 45 minutes
**Destructive**: YES (VM-only!)
**Build Required**: Release build

### ⚠️ CRITICAL: Pre-Phase 2 Checklist

**VERIFY BEFORE CONTINUING:**

- [ ] You are 100% certain you're in a VM
- [ ] VM has NO network access to production
- [ ] VM has NO shared folders with host machine
- [ ] You have a VM snapshot from before this phase
- [ ] You understand this will DELETE ALL TEST DATA

**If ANY checkbox is unchecked, STOP immediately.**

### Step-by-Step

1. **Reset VM to Clean State** (5 minutes)
   ```bash
   # Revert to Snapshot-3 or create fresh VM
   # Re-run setup script to populate test data
   cd ~/Documents/MagnetarStudio/tools/vm_testing
   ./setup_vm_test.sh
   ```

2. **Build MagnetarStudio (Release)** (10 minutes)
   ```bash
   # Open Xcode project
   open apps/native/MagnetarStudio.xcodeproj

   # In Xcode:
   # 1. Select "MagnetarStudio" scheme
   # 2. Set to "Release" configuration
   # 3. Product > Scheme > Edit Scheme
   # 4. Build Configuration: Release
   # 5. Build: Cmd+B
   # 6. Archive: Product > Archive
   # 7. Distribute App > Copy App
   # 8. Copy to /Applications/MagnetarStudio.app
   ```

3. **Enable Emergency Wipe** (1 minute)
   ```bash
   # Set environment variable to allow actual wipe
   export ELOHIM_ALLOW_EMERGENCY_WIPE=true

   # Launch app from terminal (inherits env var)
   /Applications/MagnetarStudio.app/Contents/MacOS/MagnetarStudio
   ```

4. **Trigger Emergency Mode** (2 minutes)
   - Triple-click panic button
   - Enter "I UNDERSTAND" when prompted
   - Confirm secondary "Are you absolutely sure?" modal
   - App will wipe data and self-terminate

   **Expected Behavior**:
   - Console shows wipe progress
   - App terminates after ~3 seconds
   - App bundle disappears from /Applications

5. **Verify Complete Wipe** (5 minutes)
   ```bash
   # Run verification script
   cd ~/Documents/MagnetarStudio/tools/vm_testing
   ./verify_wipe.sh
   ```

6. **Manual Verification** (5 minutes)
   ```bash
   # Check each target directory
   ls -la ~/.magnetar                    # Should not exist
   ls -la ~/.elohimos_backups            # Should not exist
   ls -la ~/Library/Caches/com.magnetarstudio.app  # Should not exist
   ls -la /Applications/MagnetarStudio.app         # Should not exist

   # Check keychain
   security find-generic-password -s "com.magnetarstudio.app"  # Should fail

   # Check processes
   ps aux | grep -i magnetar  # Should show nothing
   ```

### Expected Output (Phase 2)

**Console Output**:
```
🚨 EMERGENCY MODE ACTIVATED
🔥 DESTRUCTIVE MODE: Files will be permanently deleted

Phase 1: Backend Wipe
   ✅ Server-side databases wiped (DoD 7-pass)

Phase 2: Local Wipe
   🧹 Memory zeroed
   🧹 Clipboard cleared
   🧹 URLSession cache cleared
   🧹 Model cache deleted

Phase 3: Keychain Purge
   🔐 9 keychain items deleted

Phase 4: Self-Uninstall
   🗑️  7 user data directories deleted
   🗑️  App deletion scheduled
   🚨 Terminating...
```

**Verify Script Output**:
```
🔍 MagnetarStudio Emergency Wipe Verification

1. ✅ PASS: App bundle deleted
2. ✅ PASS: Vault directory deleted
3. ✅ PASS: Backups directory deleted
4. ✅ PASS: Cache directory deleted
5. ✅ PASS: Application Support deleted
6. ✅ PASS: Logs directory deleted
7. ✅ PASS: Preferences plist deleted
8. ✅ PASS: LaunchAgents deleted
9. ✅ PASS: Temporary files deleted
10. ✅ PASS: All keychain entries deleted
11. ✅ PASS: Clipboard is empty

Core Checks: 11/11 passed
Failed Checks: 0

✅ SUCCESS: Emergency wipe complete!
```

### Success Criteria (Phase 2)

- ✅ All 11 core checks pass in verify_wipe.sh
- ✅ App bundle deleted from /Applications
- ✅ All user data directories deleted
- ✅ All keychain entries deleted
- ✅ No MagnetarStudio processes running
- ✅ No app traces found in file system

**If all criteria pass, proceed to Phase 3.**

---

## 🔬 PHASE 3: Forensic Analysis (Day 10)

**Goal**: Attempt file recovery to prove DoD wipe effectiveness
**Duration**: 2 hours
**Destructive**: NO
**Build Required**: None

### Step-by-Step

1. **Prepare for Forensics** (5 minutes)
   ```bash
   # DO NOT reset VM - work with wiped state from Phase 2

   # Verify tools installed
   which photorec  # Should return path
   which testdisk  # Should return path

   # Download Disk Drill if not already installed
   # https://www.cleverfiles.com/
   ```

2. **Run Automated Forensic Script** (1.5 hours)
   ```bash
   cd ~/Documents/MagnetarStudio/tools/vm_testing
   ./forensic_test.sh
   # Answer "yes" to VM confirmation
   ```

   **Script will guide you through:**
   - Phase 1: PhotoRec data carving (30 min)
   - Phase 2: TestDisk partition recovery (30 min)
   - Phase 3: String search for sensitive data (15 min)
   - Phase 4: Disk Drill analysis (15 min, manual)

3. **PhotoRec Recovery Attempt** (30 minutes)
   ```bash
   # When prompted by script, run:
   sudo photorec /d ~/forensic_recovery/photorec /cmd /dev/disk1 options,fileopt,everything,enable,search

   # Select options:
   # 1. Choose disk (usually disk1)
   # 2. Choose partition type (Intel/Mac)
   # 3. Choose file types (select all)
   # 4. Choose destination: ~/forensic_recovery/photorec
   # 5. Start search

   # Press Enter in forensic_test.sh when complete
   ```

4. **TestDisk Recovery Attempt** (30 minutes)
   ```bash
   # When prompted by script, run:
   sudo testdisk /log ~/forensic_recovery/testdisk/testdisk.log /dev/disk1

   # Steps:
   # 1. Select disk
   # 2. Choose partition type (Intel/Mac)
   # 3. Select "Analyse" > "Quick Search"
   # 4. Select "Advanced" > "List files"
   # 5. Document any files found

   # Press Enter in forensic_test.sh when complete
   ```

5. **Disk Drill Analysis** (15 minutes)
   ```bash
   # Manual process:
   # 1. Launch Disk Drill app
   # 2. Select disk1
   # 3. Click "Deep Scan"
   # 4. Wait for scan to complete
   # 5. Review any recovered files
   # 6. Enter count when prompted by script
   ```

6. **Review Results** (5 minutes)
   ```bash
   # Script will generate final report
   cat ~/forensic_recovery/forensic_report_*.txt
   ```

### Expected Output (Phase 3)

**Ideal Success Result** (DoD wipe effective):
```
🔬 FINAL FORENSIC ANALYSIS REPORT
═══════════════════════════════════════

Recovery Attempts Summary:
  PhotoRec files recovered: 0
  TestDisk files recovered: 0
  Disk Drill files recovered: 0
  Sensitive string matches: 0

Total files recovered: 0

✅ FORENSIC ANALYSIS: PASS

╔═══════════════════════════════════════════════════╗
║                                                   ║
║  🎉 SUCCESS: DoD 7-Pass Wipe Effective!  🎉      ║
║                                                   ║
╚═══════════════════════════════════════════════════╝

Results:
  - 0 files recovered by forensic tools
  - 0 sensitive strings found on disk
  - DoD 5220.22-M 7-pass overwrite verified effective
  - Emergency mode wipe is forensically secure

Conclusion:
The emergency mode successfully destroyed all user data
with no possibility of recovery. The system is ready for
persecution scenario deployment.

For His glory and the protection of His people. 🙏
```

**Failure Result** (if data recoverable):
```
❌ FORENSIC ANALYSIS: FAIL

╔═══════════════════════════════════════════════════╗
║                                                   ║
║  ⚠️  WARNING: Data Recovery Possible!  ⚠️         ║
║                                                   ║
╚═══════════════════════════════════════════════════╝

Issues Found:
  - PhotoRec recovered 15 files
  - Disk Drill recovered 8 files
  - Found 42 sensitive string matches on disk

Action Required:
1. Investigate why DoD wipe did not complete fully
2. Check backend emergency_wipe.py implementation
3. Verify 7-pass overwrite is executing correctly
4. Re-run forensic analysis after fixes
```

### Success Criteria (Phase 3)

- ✅ PhotoRec recovers 0 files
- ✅ TestDisk recovers 0 files
- ✅ Disk Drill recovers 0 files
- ✅ String search finds 0 sensitive patterns
- ✅ Total recovered files = 0

**If all criteria pass, emergency mode is forensically secure!**

---

## ⏱️ Expected Timeline

| Day | Phase | Duration | Cumulative |
|-----|-------|----------|------------|
| Day 6 | Setup + Phase 1 simulation | 30 min | 30 min |
| Day 7 | Phase 1 verification | 15 min | 45 min |
| Day 8 | Phase 2 deletion test | 45 min | 1.5 hours |
| Day 9 | Phase 2 verification | 15 min | 1.75 hours |
| Day 10 | Phase 3 forensic analysis | 2 hours | 3.75 hours |

**Total: ~4 hours of active testing**

**Note**: You can take breaks between phases and split across multiple days. Just remember to maintain VM snapshots!

---

## 🆘 Troubleshooting

### Phase 1 Issues

**Problem**: Emergency mode doesn't trigger
**Solution**: Check that triple-click is registered. Try Settings > Security > Enable Emergency Mode toggle.

**Problem**: Simulation doesn't log files
**Solution**: Check Xcode console output (Cmd+Shift+Y). Ensure debug build.

### Phase 2 Issues

**Problem**: App doesn't self-uninstall
**Solution**: Check that `ELOHIM_ALLOW_EMERGENCY_WIPE=true` is set and you're using Release build.

**Problem**: Some files remain after wipe
**Solution**: This is a bug! Document which files remain and investigate `EmergencyModeService.swift`.

**Problem**: verify_wipe.sh shows failures
**Solution**: Review failed checks. Each failure indicates incomplete wipe implementation.

### Phase 3 Issues

**Problem**: PhotoRec/TestDisk not installed
**Solution**: Run `brew install testdisk` in VM.

**Problem**: Disk Drill requires purchase
**Solution**: Use free trial or skip Disk Drill (PhotoRec/TestDisk are sufficient).

**Problem**: Forensic tools recover files
**Solution**: This indicates DoD wipe is not effective! Investigate backend `emergency_wipe.py` implementation.

---

## 📊 Reporting Results

After completing all three phases, document your results:

### Success Report Template

```markdown
# VM Testing Results - PASS

**Date**: [Date]
**VM Environment**: macOS 14.2, VMware Fusion
**MagnetarStudio Version**: 1.0.0-beta

## Phase 1: Simulation ✅
- Emergency mode triggered successfully
- 11/11 file categories identified
- 150+ files marked for deletion
- 0 files actually deleted (simulation)

## Phase 2: Deletion ✅
- Emergency wipe completed in 3 seconds
- verify_wipe.sh: 11/11 checks passed
- App self-uninstalled successfully
- No traces remaining

## Phase 3: Forensics ✅
- PhotoRec: 0 files recovered
- TestDisk: 0 files recovered
- Disk Drill: 0 files recovered
- String search: 0 matches
- **Total recovered: 0 files**

## Conclusion
✅ Emergency mode is forensically secure and ready for production deployment.
```

### Failure Report Template

```markdown
# VM Testing Results - FAIL

**Date**: [Date]
**VM Environment**: macOS 14.2, VMware Fusion
**MagnetarStudio Version**: 1.0.0-beta

## Issues Found

### Phase 2 Failures
- verify_wipe.sh: 2/11 checks failed
- Files remaining:
  - ~/.magnetar/vault_sensitive.db (3.2KB)
  - ~/Library/Preferences/com.magnetarstudio.app.plist (1.1KB)

### Phase 3 Failures
- PhotoRec: 12 files recovered
- Disk Drill: 8 files recovered
- **Total recovered: 20 files**

## Action Required
1. Investigate why vault database wasn't wiped
2. Check preferences plist deletion logic
3. Verify DoD 7-pass is executing on all target files
4. Re-test after fixes
```

---

## 🎯 Quick Reference Commands

```bash
# Phase 1: Simulation
./setup_vm_test.sh                    # Create test data
# [Build + run debug build]           # Launch app
# [Triple-click panic button]         # Trigger emergency mode
ls -la ~/.magnetar                    # Verify files still exist

# Phase 2: Deletion
export ELOHIM_ALLOW_EMERGENCY_WIPE=true
# [Build + run release build]
# [Triple-click panic button + confirm]
./verify_wipe.sh                      # Verify complete wipe

# Phase 3: Forensics
./forensic_test.sh                    # Run forensic analysis
# [Follow prompts for PhotoRec/TestDisk/Disk Drill]
cat ~/forensic_recovery/forensic_report_*.txt  # Review results
```

---

## 📚 Additional Resources

- **Full Documentation**: `docs/VM_TESTING_CHECKLIST.md` (800+ lines, comprehensive)
- **Implementation Details**: `docs/WEEK2_DAYS3-5_DESTRUCTIVE_IMPLEMENTATION.md`
- **Script Source Code**:
  - `tools/vm_testing/setup_vm_test.sh`
  - `tools/vm_testing/verify_wipe.sh`
  - `tools/vm_testing/forensic_test.sh`

---

## ✅ Final Checklist

Before you begin:

- [ ] I have read the safety warnings
- [ ] I am 100% certain I'm in a VM
- [ ] I have VM snapshots for rollback
- [ ] I have all required tools installed
- [ ] I understand this will delete test data
- [ ] I will NOT test on my development machine

**If all boxes are checked, you're ready to begin VM testing!**

---

**For His glory and the protection of His people.** 🙏

**May this system serve as a fortress for believers facing persecution.** 🛡️

*"The Lord is my rock, my fortress and my deliverer."* - Psalm 18:2
