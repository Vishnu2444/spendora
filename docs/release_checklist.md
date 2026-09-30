# Spendora — Release & Safe Deployment Checklist

This document details the complete end-to-end verification gate, build workflow, signing procedures, and security checks required before releasing Spendora to Android production.

---

## 1. Automated Verification Gate

Before initiating any build or release packaging, execute the automated verification suite:

```bash
# 1. Bytecode compilation & syntax check (zero syntax errors)
python -m compileall -q .

# 2. Complete test suite with 100% pass requirement
python -m pytest -q
```

### Passing Criteria:
* `198+ passed`, 0 failed, 0 errors.
* Integer minor units (paise) math preserved across all calculations.
* No `buildozer.spec` or references to Buildozer remaining in the repo.
* No test dependencies (`pytest`, `pytest-cov`) packaged in production `requirements.txt`.

---

## 2. Security & Data Privacy Verification

* [x] **No Hardcoded Secrets**: Ensure `.env`, `spendora.db`, and API keys are strictly excluded from git tracking and app asset bundles.
* [x] **Platform-Aware Storage**: Verify that `utils.storage.get_data_dir()` correctly resolves to Android's internal app sandbox (`/data/user/0/org.spendora.spendora/files`) or OS user data dir on desktop.
* [x] **Database Integrity**: Ensure SQLite executes `PRAGMA integrity_check` before connecting to existing databases to prevent silent overwrite of corrupt user records.
* [x] **Safe AI Flow**: Confirm that natural language transactions generate a structured candidate preview (`TRANSACTION_PENDING_CONFIRMATION`) and never write to SQLite without explicit user confirmation.
* [x] **Cloud AI Opt-In**: Confirm that `cloud_ai_enabled` defaults to opt-in control in user preferences and never sends data to external Gemini servers when toggled off.

---

## 3. Official Flet Android Build Workflow

Spendora is built on **Flet 1.0.0** (Flutter-backed UI runtime). Do NOT use Buildozer.

### Step 3.1: Install Flet CLI
```bash
pip install "flet[all]>=1.0.0"
```

### Step 3.2: Build Debug APK (for Testing on Device / Emulator)
```bash
flet build apk --project Spendora --org org.spendora.spendora
```
The output APK is generated at:
`build/apk/app-release.apk` (or `build/apk/app-debug.apk`)

### Step 3.3: Build Production Android App Bundle (AAB for Google Play)
```bash
flet build aab --project Spendora --org org.spendora.spendora
```
The output AAB is generated at:
`build/aab/app-release.aab`

---

## 4. Production Release Signing & Alignment

For distribution on Google Play or direct enterprise sideloading:

### Step 4.1: Generate Keystore (if not already created)
```bash
keytool -genkey -v -keystore spendora-release.keystore -alias spendora -keyalg RSA -keysize 2048 -validity 10000
```

### Step 4.2: Build with Release Keystore via Flet
```bash
flet build apk \
  --project Spendora \
  --org org.spendora.spendora \
  --keystore-path /path/to/spendora-release.keystore \
  --keystore-password "$KEYSTORE_PASS" \
  --key-alias spendora \
  --key-password "$KEY_PASS"
```

Or sign an existing APK using `apksigner`:
```bash
# 1. Align the APK
zipalign -v -p 4 build/apk/app-release-unsigned.apk spendora-aligned.apk

# 2. Sign with release key
apksigner sign --ks spendora-release.keystore --ks-key-alias spendora --out spendora-release-signed.apk spendora-aligned.apk

# 3. Verify signature
apksigner verify spendora-release-signed.apk
```

---

## 5. Post-Deployment Device Smoke Tests

Install the signed build onto an Android physical device or virtual device (AVD):

```bash
adb install -r spendora-release-signed.apk
```

Execute the following smoke test checklist on the physical device:

1. **Cold Launch & Storage Initialization**:
   - App launches smoothly to Onboarding/Dashboard.
   - Database creates cleanly in `/data/user/0/org.spendora.spendora/files/spendora.db`.
   - Re-opening the app retains previously created categories and transactions without reset.

2. **Ledger Transaction Logging**:
   - Add an Expense (e.g. ₹450) and an Income (e.g. ₹5,000).
   - Verify transaction appears immediately in Ledger with correct balance formatting (`₹450.00`).
   - Force kill app (`adb shell am force-stop org.spendora.spendora`) and relaunch: verify all records persist.

3. **AI Concierge Assistant**:
   - Navigate to Concierge tab.
   - Test natural language entry: `"Spent 250 on coffee yesterday"`.
   - Verify Candidate Preview card displays with `[ Confirm & Log ]`, `[ Edit in Form ]`, and `[ Cancel ]`.
   - Click `Confirm & Log`: verify transaction commits to database and updates monthly surplus.
   - Navigate to Settings -> Toggle `Cloud AI (Google Gemini)` off: verify assistant continues answering queries using local deterministic intelligence.

4. **Edge Cases**:
   - Test entry of zero or negative amounts in transaction form: verify validation prevents corrupted entries.
   - Verify 50-30-20 budget calculation displays accurately.
