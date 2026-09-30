# Spendora — Safe Deployment & Hardening Audit Report
**Deliverable for Phase 0 of Spendora Antigravity Agent Safe Deployment & Hardening Plan**  
*Date of Audit:* September 30, 2026  
*Status:* Complete (Read-Only Inspection Phase)  

---

## 1. Executive Summary & Assessment Matrix

This audit inspects the current Spendora codebase against the **Spendora Safe Deployment Instructions**. The core architecture is in excellent shape: the codebase uses modern **Flet (Flutter-backed)**, implements strict integer minor-unit (`paise`) arithmetic, and possesses an extensive suite of **169 passing automated tests**.

However, several critical deployment, security, and persistence risks must be addressed before this application can be packaged into a safe, release-ready Android APK/AAB:

| Implementation Area | Current Status | Assessment | Action Required |
| :--- | :--- | :--- | :--- |
| **1. Framework & UI** | Flet 1.0.0+ | **Modern & Complete** | Preserve completely. Do not rebuild or touch working Flet UI. |
| **2. Build Configuration** | Stale `buildozer.spec` & Kivy references in `README.md` | **Configuration Drift** | Remove stale Kivy/Buildozer instructions. Replace with official `flet build apk` / `flet build aab` workflow. |
| **3. Database Storage** | `Path(__file__).parent.parent / "data" / "spendora.db"` | **High Risk on Android** | Packaged Android bundles have read-only assets. Centralize in a platform-aware storage abstraction using app-private writable storage. |
| **4. Financial Calculations** | Pure integer `amount_paise`, deterministic engine | **Solid Foundation** | Determinism preserved. Expand edge-case tests (zero, minor units, boundary dates, leap years, negative validation). |
| **5. AI Secret Security** | `GEMINI_API_KEY` in `.env` / environment variable | **Needs Hardening** | Ensure `.env` is never packaged into the APK. Disclose cloud AI usage and support offline / custom endpoint mode. |
| **6. AI Transaction Logging** | Direct write in `_handle_transaction_logging` | **Unsafe Mutation** | Implement preview -> validation -> user confirmation (`Confirm` / `Edit` / `Cancel`) workflow before database write. |
| **7. AI Advice Authoritativeness**| Mixed phrasing in advice prompts | **Needs Calibration** | Frame AI responses as non-authoritative explanations of deterministic calculation engine facts. |
| **8. Privacy & AI Controls** | UI switches in Settings show snackbars without persistence | **Needs Wire-up** | Persist `cloud_ai_enabled` setting in `user_preferences`. Provide data minimization and clear disclosure. |
| **9. Automated Test Gate** | 169 tests passing in ~7s | **Strong** | Add regression tests for storage, AI preview/confirmation, and financial edge cases. |
| **10. Release Readiness** | Development state | **Not Ready** | Must pass all release gates before signing APK/AAB. |

---

## 2. Actual Framework & Entry Point

* **Framework:** **Flet** (`flet>=1.0.0`), utilizing Flutter as its underlying native rendering engine.
* **Entry Point:** [`main.py`](file:///c:/Users/vishn/Desktop/spendora/main.py)
* **Application Shell:** Single-page application with navigation rail/bar switching between 6 primary view components:
  1. `WelcomeView` & `CategorySetupView` ([`screens/onboarding/`](file:///c:/Users/vishn/Desktop/spendora/screens/onboarding))
  2. `DashboardView` ([`screens/dashboard/dashboard_screen.py`](file:///c:/Users/vishn/Desktop/spendora/screens/dashboard/dashboard_screen.py))
  3. `TransactionsView` & `AddEditTransactionView` ([`screens/transactions/`](file:///c:/Users/vishn/Desktop/spendora/screens/transactions))
  4. `AnalyticsView` ([`screens/analytics/analytics_screen.py`](file:///c:/Users/vishn/Desktop/spendora/screens/analytics/analytics_screen.py))
  5. `AssistantView` ([`screens/assistant/assistant_screen.py`](file:///c:/Users/vishn/Desktop/spendora/screens/assistant/assistant_screen.py))
  6. `PersonalizationView` ([`screens/personalization/personalization_screen.py`](file:///c:/Users/vishn/Desktop/spendora/screens/personalization/personalization_screen.py))
* **Theme System:** Centralized `ThemeManager` in [`config/theme_manager.py`](file:///c:/Users/vishn/Desktop/spendora/config/theme_manager.py) supporting reactive Light, Dark, and System modes.

---

## 3. Dependencies Audit

### `requirements.txt`
```
flet>=1.0.0
flet-charts>=0.1.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
google-genai>=2.0.0
pytest>=8.0.0
pytest-cov>=5.0.0
```

### Dependency Findings & Clean-up Required:
1. **Packaging Separation:** `pytest` and `pytest-cov` are currently bundled in `requirements.txt`. For production Android packaging, development dependencies should be separated into a `requirements-dev.txt` so test runners are not packaged into the mobile distribution.
2. **Kivy / Buildozer Artifact:** `buildozer.spec` references:
   ```ini
   requirements = python3,kivy==2.3.1,kivymd==2.0.0,pillow==10.4.0,sqlalchemy==2.0.52,pydantic==2.13.5,python-dotenv==1.2.3,google-genai==2.21.0
   ```
   This is dead configuration from an abandoned prototype and must be removed or marked deprecated to prevent build confusion.

---

## 4. Database Location, Initialization & Transaction Handling

### Current Implementation:
* **Settings Definition** ([`config/settings.py`](file:///c:/Users/vishn/Desktop/spendora/config/settings.py#L21-L28)):
  ```python
  BASE_DIR: Path = Path(__file__).resolve().parent.parent
  DATA_DIR: Path = BASE_DIR / "data"
  DATABASE_PATH: Path = DATA_DIR / "spendora.db"
  DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"
  ```
* **Engine Configuration** ([`database/database.py`](file:///c:/Users/vishn/Desktop/spendora/database/database.py#L35-L60)):
  * Uses SQLite with `check_same_thread=False`.
  * Event listener automatically executes `PRAGMA foreign_keys=ON` and `PRAGMA journal_mode=WAL`.
* **Session Management**:
  * Clean context manager `get_session()` handling commit, rollback on error, and automatic close.

### Vulnerabilities & Risks for Android:
1. **Read-Only App Assets Risk:** On Android, `BASE_DIR / "data"` resolves to the APK's read-only extraction directory or application root where write operations fail with `sqlite3.OperationalError: unable to open database file` or `PermissionError`.
2. **Target Fix:** Create a centralized storage abstraction `utils/storage.py` or extend `config/settings.py` to resolve:
   * Android/Flet: `os.environ.get("FLET_APP_STORAGE_DATA")` or platform-standard app-private directory (`/data/user/0/<app_id>/files` or `user_data_dir("Spendora", "Spendora")`).
   * Desktop / Dev: Fallback to `BASE_DIR / "data" / "spendora.db"`.
   * Ensure directory exists before connecting.
   * If a corrupt database cannot be opened, surface a recoverable error rather than silently overwriting user data.

---

## 5. Financial Data Integrity & Flow

### Flow Architecture:
1. **Input Parsing:** User input strings are strictly validated in [`utils/validators.py`](file:///c:/Users/vishn/Desktop/spendora/utils/validators.py) using regex and converted to integer paise (`amount_to_paise("250.50") -> 25050`).
2. **Storage:** Stored in the `transactions` table as non-negative integer `amount_paise`.
3. **Deterministic Arithmetic:** All totals, net balances, burn rates, savings projections, and category percentages are calculated in pure Python in [`services/calculation_service.py`](file:///c:/Users/vishn/Desktop/spendora/services/calculation_service.py) and [`services/analytics_service.py`](file:///c:/Users/vishn/Desktop/spendora/services/analytics_service.py).
4. **Display:** Formatted deterministically via [`utils/formatting.py`](file:///c:/Users/vishn/Desktop/spendora/utils/formatting.py) (`format_currency`).

### Evaluation:
* **Compliant Invariant:** Money calculations are **100% deterministic**. The AI is never used to sum, subtract, or derive balances.
* **Needed Edge-Case Tests:**
  * Zero amount handling (`₹0.00`).
  * Micro unit transactions (`₹0.01` -> 1 paisa).
  * High-value bounds (e.g. ₹99,99,99,999.99).
  * Boundary dates: February 29 (leap year), month boundaries (e.g. Dec 31 -> Jan 1), future dates.
  * Empty database / zero-transaction state across analytics and calculator tabs.

---

## 6. AI Entry Points, Prompt Data Flow & Privacy

### AI Features in [`services/ai_service.py`](file:///c:/Users/vishn/Desktop/spendora/services/ai_service.py):
1. **`predict_categories()`**: Suggests categories during onboarding based on profession. Falls back to curated offline dictionary when unconfigured or offline.
2. **`chat()`**: Grounded conversational financial assistant (Personal Financial ChatGPT).

### Privacy & Data Flow Analysis:
* **Context Gathering:** `_gather_financial_context(user_id)` builds ground truth:
  * Current monthly income, expenses, and net surplus.
  * Category breakdown with integer paise totals and percentages.
  * Last 10 transactions (description, date, amount, category).
* **Risks & Required Hardening:**
  1. **Data Minimization:** Only include transaction descriptions when specifically analyzing transactions. Avoid sending full transaction lists if the user is asking general questions (e.g. "What is the 50-30-20 rule?").
  2. **Opt-in & Control:** Add a persistent setting `cloud_ai_enabled` in `UserPreference`. When disabled, the AI operates in **100% offline heuristic mode** and never contacts Google Gemini.
  3. **No Prompt Logging:** Ensure prompt text and full model responses are never logged to production logs (`logger.info`/`logger.debug`).
  4. **Clear Disclosure:** Add an informational note in the settings UI explaining what data is stored locally and what is transmitted when cloud AI is active.

---

## 7. AI Transaction Logging & Confirmation Workflow

### Current Unsafe Behavior:
* In `services/ai_service.py` (`_handle_transaction_logging`):
  When a user types `"Spent ₹250 on lunch"`, the AI service resolves the category and **immediately writes to the database**:
  ```python
  txn = self._transaction_service.create_transaction(...)
  ```
  The chat screen then shows `"Transaction recorded directly to your ledger!"`.

### Compliance Violation:
* Rule: **AI must not silently mutate financial data.** All AI-generated transactions, edits, or categorizations must use a preview and confirmation workflow:
  ```
  [Candidate Transaction Preview]
  • Amount: ₹250.00
  • Type: Expense
  • Category: Food & Dining
  • Date: 30 Sep 2026
  
  [ Confirm & Log ]   [ Edit ]   [ Cancel ]
  ```
* **Database write must occur only after explicit user confirmation.**
* Ambiguous parsing must prompt the user for clarification rather than making assumptions.

---

## 8. Android Build Path & Packaging

### Current State:
* `README.md` instructs using `buildozer android debug`.
* `buildozer.spec` exists in the repository root.
* The application code is built on **Flet**, which uses its own build toolchain (`flet build apk` / `flet build aab`). Running Buildozer on this codebase will fail or package an unusable Kivy wrapper.

### Required Actions:
1. Update `README.md` to document the Flet Android build workflow:
   ```bash
   flet build apk --project Spendora --org org.spendora
   flet build aab --project Spendora --org org.spendora
   ```
2. Deprecate or remove `buildozer.spec` so developers and CI systems do not execute Kivy build pipelines.
3. Configure `flet.toml` or equivalent project configuration specifying app name, package name, version, and permissions (`INTERNET`).

---

## 9. Test Suite & Coverage Status

### Current Test Suite:
* **15 test files** in `tests/`:
  * `test_models.py`
  * `test_validators.py`
  * `test_calculations.py`
  * `test_calculation_service.py`
  * `test_analytics_service.py`
  * `test_transaction_service.py`
  * `test_ai_service.py`
  * `test_services.py`
  * `test_onboarding_flow.py`
  * `test_transactions_flow.py`
  * `test_personalization.py`
  * `test_theme_and_ui.py`
* **Test Results:** 169 passed in 6.97s.
* **Code Integrity:** Zero syntax errors; `python -m compileall -q .` completed cleanly.

### Needed Regression & Hardening Tests:
1. `tests/test_storage.py`: Test app-private storage resolution and directory verification.
2. `tests/test_financial_edge_cases.py`: Boundary values, leap year dates, negative amount validation, zero-state analytics.
3. `tests/test_ai_confirmation.py`: Verify preview generation, user confirmation gate, cancellation, and rejection of ambiguous input.

---

## 10. Prioritized Implementation Plan

| Phase | Description | Key Files Involved |
| :--- | :--- | :--- |
| **Phase 1** | **Correct Android Build Path & Clean Configuration** | `README.md`, `requirements.txt`, `buildozer.spec` |
| **Phase 2** | **Android-Safe Persistent Storage** | `config/settings.py`, `database/database.py`, `utils/storage.py` |
| **Phase 3** | **Financial Data Integrity & Edge-Case Tests** | `utils/validators.py`, `tests/test_financial_edge_cases.py` |
| **Phase 4** | **AI Security, Privacy & Opt-In Controls** | `config/settings.py`, `services/ai_service.py`, `screens/personalization/personalization_screen.py` |
| **Phase 5** | **Safe AI Transaction Preview & Confirmation Flow** | `services/ai_service.py`, `screens/assistant/assistant_screen.py`, `components/chat_bubble.py` |
| **Phase 6** | **Non-Authoritative AI Advice Refinement** | `services/ai_service.py` |
| **Phase 7** | **Documentation & Version Synchronization** | `README.md`, `config/settings.py`, `docs/release_checklist.md` |
| **Phase 8** | **Automated Test Gate & Regression Verification** | `pytest -q`, `python -m compileall -q .` |
