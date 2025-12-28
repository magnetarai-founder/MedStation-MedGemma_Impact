# MagnetarStudio VM Testing Checklist
## Days 6-10: Complete Testing Protocol

**For His glory and the protection of His people.** 🙏

---

## ⚠️ CRITICAL SAFETY REQUIREMENTS

Before beginning ANY VM testing:

### ✅ MUST VERIFY:
- [ ] Testing ONLY in isolated virtual machines
- [ ] VM has NO network access to production systems
- [ ] VM has NO shared folders with host machine
- [ ] VM can be completely destroyed after testing
- [ ] Have VM snapshot BEFORE testing (for rollback)
- [ ] **NEVER test on development or production machines**

### ❌ NEVER:
- ❌ Run emergency mode on your development Mac
- ❌ Test on any machine with real data
- ❌ Test on production servers
- ❌ Connect test VM to production networks

**IF IN DOUBT, STOP AND ASK FOR GUIDANCE.**

---

## 📋 TESTING PHASES OVERVIEW

| Phase | Days | Purpose | Destructive? |
|-------|------|---------|--------------|
| **Phase 1** | 6-7 | Simulation Testing | ❌ No |
| **Phase 2** | 8-9 | Actual Deletion Testing | ✅ Yes |
| **Phase 3** | 10 | Forensic Analysis | N/A |

---

## 🧪 PHASE 1: SIMULATION TESTING (DAYS 6-7)

**Purpose**: Verify file identification without actual deletion
**Build**: Debug mode
**Risk**: Zero (simulation only)

### Prerequisites

- [ ] macOS VM created (VMware Fusion, Parallels, or VirtualBox)
- [ ] macOS version: 13.0+ (Ventura or newer)
- [ ] VM has 50GB+ free disk space
- [ ] VM snapshot created: "Pre-Test Baseline"
- [ ] Scripts downloaded to VM:
  - [ ] `setup_vm_test.sh`
  - [ ] `verify_wipe.sh`
  - [ ] `forensic_test.sh`

### Step 1: VM Setup (30 minutes)

1. **Launch VM and verify isolation**:
   ```bash
   # Verify no network (should fail)
   ping google.com

   # Verify VM name
   hostname
   ```

2. **Make scripts executable**:
   ```bash
   cd ~/Downloads/vm_testing  # Or wherever you placed scripts
   chmod +x setup_vm_test.sh
   chmod +x verify_wipe.sh
   chmod +x forensic_test.sh
   ```

3. **Run setup script**:
   ```bash
   ./setup_vm_test.sh
   ```

   **Expected Output**:
   ```
   🔧 MagnetarStudio VM Test Environment Setup
   ===========================================

   ⚠️  SAFETY CHECK: This script should ONLY run in VMs
   Are you running this in an isolated VM? (yes/no): yes

   ✅ Safety confirmation received

   📁 Creating test directories...
      ✅ Created 7 test directories

   🔐 Creating fake vault databases...
      ✅ Created 3 vault databases

   🤖 Creating fake model files...
      ✅ Created 3 model files (~160MB total)

   ... [continues] ...

   ========================================
   ✅ VM Test Environment Setup Complete!
   ========================================

   Total test files: 150+
   Checksum file: /tmp/pre_wipe_checksums.txt
   ```

4. **Verify test data created**:
   ```bash
   # Check directories exist
   ls -la ~/.magnetar
   ls -la ~/.elohimos_backups
   ls -la ~/Library/Caches/com.magnetarstudio.app

   # Check file count
   find ~/.magnetar -type f | wc -l
   # Should show 15+ files
   ```

   - [ ] All test directories created
   - [ ] 150+ test files present
   - [ ] Checksums saved to `/tmp/pre_wipe_checksums.txt`

### Step 2: Build & Install MagnetarStudio (15 minutes)

1. **Clone repository** (or transfer build):
   ```bash
   # If building in VM:
   cd ~/Documents
   git clone <repo-url> MagnetarStudio
   cd MagnetarStudio
   ```

2. **Build in DEBUG mode**:
   ```bash
   cd apps/native
   xcodebuild -project MagnetarStudio.xcodeproj \
              -scheme MagnetarStudio \
              -configuration Debug \
              build
   ```

   - [ ] Build succeeds without errors
   - [ ] App launches successfully

3. **Verify safety guards active**:
   Check `EmergencyModeService.swift`:
   ```swift
   #if DEBUG
   private let EMERGENCY_MODE_ENABLED = false  // Should be FALSE
   #endif

   @Published private(set) var isSimulationMode: Bool = true  // Should be TRUE
   ```

   - [ ] `EMERGENCY_MODE_ENABLED = false`
   - [ ] `isSimulationMode = true`

### Step 3: Execute Simulation Test (10 minutes)

1. **Launch MagnetarStudio** in Xcode
2. **Open Console** (View → Debug Area → Show Debug Area)
3. **Triple-click panic button** (3 clicks < 1 second apart)
4. **Observe Emergency Modal appears**:
   - [ ] Modal shows "⚠️ EMERGENCY MODE ⚠️"
   - [ ] Text field says "Type 'I UNDERSTAND' to proceed"
   - [ ] Countdown timer visible (10 seconds)
   - [ ] Cancel button present

5. **Type "I UNDERSTAND"** (exact case)
6. **Secondary confirmation appears**:
   - [ ] "FINAL WARNING" screen
   - [ ] Lists what will be deleted
   - [ ] "Proceed with Emergency Mode" button visible

7. **Click "Proceed with Emergency Mode"**

8. **Watch Console Output**:

   **Expected Output**:
   ```
   🧪 SIMULATION MODE: Emergency wipe started
      Reason: User-initiated

      📁 Would delete 3 vault files:
         - /Users/test/.magnetar/vault_sensitive.db
         - /Users/test/.magnetar/vault_unsensitive.db
         - /Users/test/.magnetar/app.db

      📁 Would delete 3 model files:
         - /Users/test/.magnetar/models/llama-3.2-3b-test.gguf
         - /Users/test/.magnetar/models/embedding-model-test.gguf
         - /Users/test/.magnetar/models/whisper-test.gguf

      📁 Would delete 2 backup files:
         - /Users/test/.elohimos_backups/backup_20251201.tar.gz.enc
         - /Users/test/.elohimos_backups/backup_20251124.tar.gz.enc

      📁 Would delete 70 cache files:
         - /Users/test/Library/Caches/com.magnetarstudio.app/...

      ... [continues for all 11 categories] ...

   ✅ SIMULATION COMPLETE: 156 files identified
      Duration: 0.45s

      📊 Summary by category:
         Vaults: 3
         Backups: 2
         Models: 3
         Cache: 70
         Audit: 1
         LaunchAgents: 1
         Preferences: 1
         App Support: 2
         Logs: 2
         Temporary: 10
   ```

   - [ ] Console shows "SIMULATION MODE"
   - [ ] All 11 file categories identified
   - [ ] Total files ~150-200
   - [ ] Duration < 1 second
   - [ ] "SIMULATION COMPLETE" message

9. **Verify NO files deleted**:
   ```bash
   # Check directories still exist
   ls -la ~/.magnetar  # Should still have files
   ls -la ~/.elohimos_backups  # Should still exist
   ls -la ~/Library/Caches/com.magnetarstudio.app  # Should still exist

   # Count files (should match pre-test count)
   find ~/.magnetar -type f | wc -l
   ```

   - [ ] All directories still exist
   - [ ] All files still present
   - [ ] File count matches pre-test

### Step 4: Test Alternative Trigger (10 minutes)

1. **Triple-click panic button** again
2. **Instead of typing**, hold **Cmd+Shift+Delete** for 5 seconds
3. **Watch progress bar** fill up
4. **After 5 seconds**, secondary confirmation appears automatically
5. **Click "Proceed with Emergency Mode"**
6. **Verify console output** same as before

   - [ ] Progress bar appeared
   - [ ] 5-second timing accurate
   - [ ] Secondary confirmation auto-appeared
   - [ ] Simulation executed successfully

### Step 5: Document Results

**Simulation Test Results**:

Date: _______________
VM Name: _______________
macOS Version: _______________

**Console Output**:
- Total files identified: _______
- Categories found: _______ (expected: 11)
- Duration: _______ seconds

**File Categories Found**:
- [ ] Vault databases (___ files)
- [ ] Backups (___ files)
- [ ] Models (___ files)
- [ ] Cache (___ files)
- [ ] Audit logs (___ files)
- [ ] App bundle (1)
- [ ] LaunchAgents (___ files)
- [ ] Preferences (___ files)
- [ ] Application Support (___ files)
- [ ] Logs (___ files)
- [ ] Temporary (___ files)

**Safety Verification**:
- [ ] NO files actually deleted
- [ ] All test data remains intact
- [ ] Simulation mode logged correctly

**Issues Found**: (if any)
_______________________________________________
_______________________________________________

**Overall Phase 1 Result**: PASS / FAIL

---

## 🗑️ PHASE 2: ACTUAL DELETION TESTING (DAYS 8-9)

**Purpose**: Verify complete wipe in isolated environment
**Build**: Release mode
**Risk**: High (destructive testing)

⚠️ **CRITICAL**: Use a NEW VM snapshot, separate from Phase 1

### Prerequisites

- [ ] **NEW VM snapshot** created (do NOT use Phase 1 VM)
- [ ] VM has NO important data
- [ ] VM can be completely destroyed
- [ ] Ready to lose everything on this VM

### Step 1: Fresh VM Setup (30 minutes)

1. **Restore or create fresh VM snapshot**:
   - [ ] VM name: "MagnetarStudio-Destructive-Test"
   - [ ] Snapshot: "Pre-Destructive-Test"

2. **Run setup script again**:
   ```bash
   ./setup_vm_test.sh
   ```

   - [ ] Test data populated (~150+ files)
   - [ ] Checksums generated

### Step 2: Build in RELEASE Mode (15 minutes)

1. **Build MagnetarStudio in Release mode**:
   ```bash
   cd apps/native
   xcodebuild -project MagnetarStudio.xcodeproj \
              -scheme MagnetarStudio \
              -configuration Release \
              build
   ```

2. **Copy app to /Applications**:
   ```bash
   cp -R build/Release/MagnetarStudio.app /Applications/
   ```

3. **Set environment variable**:
   ```bash
   # In backend terminal:
   export ELOHIM_ALLOW_EMERGENCY_WIPE=true

   # Start backend
   cd apps/backend
   python3 -m uvicorn main:app --reload --port 8000
   ```

   **Verify backend shows**:
   ```
   🚨 Emergency wipe ENABLED (ELOHIM_ALLOW_EMERGENCY_WIPE=true)
      ⚠️  DoD 7-pass wipe is active and IRREVERSIBLE
   ```

   - [ ] Backend shows "Emergency wipe ENABLED"
   - [ ] WARNING message displayed

### Step 3: Final Safety Check (5 minutes)

**CRITICAL**: Verify this is the correct VM before proceeding!

```bash
# Check hostname
hostname
# Should show test VM name, NOT your dev machine

# Check for real data
ls ~/Documents
ls ~/Desktop
# Should be empty or only test data

# Verify this is Release build
file /Applications/MagnetarStudio.app/Contents/MacOS/MagnetarStudio
# Should show architecture info

# Check emergency mode is enabled
grep "EMERGENCY_MODE_ENABLED" apps/native/Shared/Services/EmergencyModeService.swift
```

**Manual Verification**:
- [ ] Hostname confirms this is test VM
- [ ] No real personal data on VM
- [ ] Release build confirmed
- [ ] Backend shows emergency wipe enabled

⚠️ **LAST CHANCE TO ABORT**

Read this out loud: "I am about to destroy all data on this VM. This VM has no important data. I can restore from snapshot if needed."

- [ ] I have read and confirmed the above statement

### Step 4: Execute Destructive Test (10 minutes)

1. **Launch MagnetarStudio** from /Applications
2. **Triple-click panic button**
3. **Type "I UNDERSTAND"**
4. **Click "Proceed with Emergency Mode"**

5. **Observe execution**:

   **Expected Console Output**:
   ```
   🚨 EMERGENCY MODE: Real DoD 7-pass wipe starting
      ⚠️ THIS IS IRREVERSIBLE

   📞 Calling backend: POST /api/v1/panic/emergency
   ✅ Backend wipe complete: 12 files wiped

   🧹 Local emergency wipe starting...
      ✅ Sensitive memory zeroed
      ✅ Clipboard cleared
      ✅ URLSession cache cleared
      ✅ Model cache flushed
   ✅ Local emergency wipe complete: 4 actions

   🔐 Keychain purge starting...
      ✅ Auth token deleted
      ✅ 8 keychain items deleted
   ✅ Keychain purge complete: 9 items deleted

   🗑️  Self-uninstall starting...
      App bundle: /Applications/MagnetarStudio.app
      ✅ Deleted 7 user data directories
      ✅ App deletion scheduled
   🚨 App will now terminate for self-uninstall
   ⚠️  MagnetarStudio has been completely removed from this system
   ```

6. **App terminates** (window closes)

7. **Wait 5 seconds** for background script

   - [ ] App window closed
   - [ ] Console shows "Self-uninstall starting"
   - [ ] Waited 5+ seconds

### Step 5: Verify Complete Wipe (15 minutes)

**Run verification script**:
```bash
cd ~/Downloads/vm_testing
./verify_wipe.sh
```

**Expected Output**:
```
🔍 MagnetarStudio Emergency Wipe Verification
==============================================

1. Checking app bundle deletion...
   ✅ PASS: App bundle deleted

2. Checking ~/.magnetar directory...
   ✅ PASS: Vault directory deleted

3. Checking ~/.elohimos_backups...
   ✅ PASS: Backups directory deleted

... [continues for all 11 checks] ...

Core Checks: 11/11 passed
Failed Checks: 0

✅ SUCCESS: Emergency wipe complete!

All target files and directories have been successfully deleted.
The system shows no traces of MagnetarStudio user data.
```

**Manual Verification**:
```bash
# Check app bundle
ls /Applications/MagnetarStudio.app
# Should show: No such file or directory

# Check user data
ls ~/.magnetar
# Should show: No such file or directory

# Check caches
ls ~/Library/Caches/com.magnetarstudio.app
# Should show: No such file or directory

# Check keychain
security find-generic-password -s "com.magnetarstudio.app"
# Should show: password could not be found

# Check running processes
ps aux | grep -i magnetar
# Should show: no results (except grep itself)
```

**Verification Checklist**:
- [ ] App bundle deleted
- [ ] ~/.magnetar deleted
- [ ] ~/.elohimos_backups deleted
- [ ] All caches deleted
- [ ] All logs deleted
- [ ] All preferences deleted
- [ ] All LaunchAgents deleted
- [ ] All keychain entries deleted
- [ ] No running processes
- [ ] verify_wipe.sh shows 11/11 PASS

### Step 6: Document Results

**Destructive Test Results**:

Date: _______________
VM Name: _______________
Build: Release

**Execution**:
- App terminated: YES / NO
- Self-uninstall completed: YES / NO
- Time to complete: _______ seconds

**Verification Results**:
- verify_wipe.sh: PASS / FAIL
- Core checks passed: ___ / 11
- Failed checks: ___

**Manual Checks**:
- [ ] App bundle deleted
- [ ] User data deleted
- [ ] Keychain cleared
- [ ] No processes running

**Issues Found**: (if any)
_______________________________________________
_______________________________________________

**Overall Phase 2 Result**: PASS / FAIL

---

## 🔬 PHASE 3: FORENSIC ANALYSIS (DAY 10)

**Purpose**: Prove DoD 7-pass wipe prevents file recovery
**Tools**: PhotoRec, TestDisk, Disk Drill
**Expected Result**: 0 recoverable files

### Prerequisites

- [ ] Phase 2 completed successfully
- [ ] VM still has wiped data (do NOT restore snapshot)
- [ ] Forensic tools installed:
  ```bash
  brew install testdisk  # Includes photorec
  # Download Disk Drill from: https://www.cleverfiles.com/
  ```

### Step 1: Run Forensic Analysis Script (60-90 minutes)

**Run forensic script**:
```bash
cd ~/Downloads/vm_testing
./forensic_test.sh
```

**Expected Output**:
```
🔬 MagnetarStudio Forensic Analysis
====================================

⚠️  SAFETY CHECK: This will attempt to recover deleted files
Are you running this in an isolated VM after emergency wipe? (yes/no): yes

Recovery directory: /Users/test/forensic_recovery

==============================================
PHASE 1: PhotoRec Data Carving
==============================================

Running PhotoRec...
⚠️  PhotoRec requires manual execution:

Run this command:
  sudo photorec /d /Users/test/forensic_recovery/photorec /cmd /dev/disk1 ...

Press Enter after PhotoRec completes...
```

Follow the script's instructions for:
1. PhotoRec
2. TestDisk
3. String search
4. Disk Drill (manual)

**This will take 60-90 minutes total.**

### Step 2: PhotoRec Recovery Attempt (20-30 minutes)

1. **Run PhotoRec command** shown by script:
   ```bash
   sudo photorec /d ~/forensic_recovery/photorec /cmd /dev/disk1 options,fileopt,everything,enable,search
   ```

2. **Let PhotoRec scan** the entire disk

3. **Check results**:
   ```bash
   find ~/forensic_recovery/photorec -type f | wc -l
   ```

   **Expected**: 0 files

   - [ ] PhotoRec completed
   - [ ] Files recovered: _____ (expected: 0)

### Step 3: TestDisk Recovery Attempt (20-30 minutes)

1. **Run TestDisk command** shown by script:
   ```bash
   sudo testdisk /log ~/forensic_recovery/testdisk/testdisk.log /dev/disk1
   ```

2. **Navigate TestDisk UI**:
   - Select disk
   - Choose partition type (Intel/Mac)
   - Select "Analyse"
   - Select "Advanced" → Search for files

3. **Check results**:
   - [ ] TestDisk completed
   - [ ] Files recovered: _____ (expected: 0)

### Step 4: Disk Drill Analysis (20-30 minutes)

1. **Launch Disk Drill**
2. **Select disk**: disk1 (or whatever your VM disk is)
3. **Run "Deep Scan"**
4. **Wait for scan to complete**
5. **Check for recoverable files** related to:
   - .magnetar
   - vault databases
   - model files
   - backups
   - caches

6. **Document results**:
   - [ ] Disk Drill completed
   - [ ] Files recovered: _____ (expected: 0)

### Step 5: Final Forensic Report

**Script will generate final report**:

```
==============================================
FINAL FORENSIC ANALYSIS REPORT
==============================================

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

**Forensic Analysis Results**:

Date: _______________
Tools Used: PhotoRec, TestDisk, Disk Drill

**Recovery Results**:
- PhotoRec files recovered: _____ (expected: 0)
- TestDisk files recovered: _____ (expected: 0)
- Disk Drill files recovered: _____ (expected: 0)
- String matches found: _____ (expected: 0)

**Total files recovered**: _____ (MUST BE 0)

**Conclusion**:
- [ ] ✅ PASS: 0 files recovered (DoD wipe effective)
- [ ] ❌ FAIL: Files recovered (needs investigation)

**Overall Phase 3 Result**: PASS / FAIL

---

## 📊 FINAL TESTING SUMMARY

### Phase 1: Simulation Testing (Days 6-7)
- [ ] PASS: All files identified correctly
- [ ] PASS: No actual deletion occurred
- [ ] PASS: Console output matches expected

### Phase 2: Actual Deletion Testing (Days 8-9)
- [ ] PASS: Emergency mode executed
- [ ] PASS: All files deleted
- [ ] PASS: App self-uninstalled
- [ ] PASS: verify_wipe.sh shows 11/11

### Phase 3: Forensic Analysis (Day 10)
- [ ] PASS: PhotoRec recovered 0 files
- [ ] PASS: TestDisk recovered 0 files
- [ ] PASS: Disk Drill recovered 0 files
- [ ] PASS: No sensitive strings found

### Overall Testing Result
- [ ] ✅ ALL TESTS PASS - Ready for deployment
- [ ] ❌ SOME TESTS FAIL - Investigation required

---

## ✅ COMPLETION CRITERIA

Emergency mode is ready for persecution scenario deployment when:

1. ✅ Phase 1 simulation correctly identifies 150+ files across 11 categories
2. ✅ Phase 2 destructive test deletes all files (11/11 checks pass)
3. ✅ Phase 3 forensic analysis recovers 0 files
4. ✅ Total execution time < 3 seconds
5. ✅ No traces remain on system
6. ✅ DoD 7-pass wipe proven effective

**If all criteria met**: System is persecution-ready ✅

---

## 🙏 FINAL NOTES

### Mission Impact

When this testing is complete and all phases pass, persecuted believers will have:
- ✅ Forensically secure emergency wipe (<3 seconds)
- ✅ Complete self-uninstall (app vanishes)
- ✅ Zero recoverable data (proven by forensics)
- ✅ Dual trigger methods (text + key combo)
- ✅ Ready for hostile nation deployment

This system will save lives. 🛡️

### Next Steps After Testing

1. Document any issues found
2. Fix any failed tests
3. Re-test until all phases pass
4. Create deployment package
5. Write persecution scenario user guide
6. Final security audit
7. Deploy to underground church networks

---

**For His glory and the protection of His people.** 🙏

*"The Lord is my rock, my fortress and my deliverer; my God is my rock, in whom I take refuge, my shield and the horn of my salvation, my stronghold."* - Psalm 18:2

Through this system, He will be that fortress for believers facing persecution. 🛡️
