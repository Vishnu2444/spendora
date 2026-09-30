# Spendora — Final Deployment Hardening & Pre-Release Audit

**Document:** `docs/final_deployment_audit.md`  
**Date:** 2026-09-30  
**Target Environment:** Android Mobile (Flet 1.0 Runtime) & Desktop  
**Status:** Pre-Hardening Verification

---

## 1. Executive Summary

This audit assesses the current state of Spendora against all 15 operational phases specified in the Final Deployment Hardening & Bug-Fix Specification. The codebase has a robust foundation with Flet 1.0 UI, SQLite integer paise math, and candidate transaction confirmation. However, critical deployment blockers remain around **Cloud AI default privacy (currently defaulting to enabled instead of disabled)**, **AI prompt data minimization (sending full financial context for all queries)**, and **build artifact exclusions in `pyproject.toml`**.

---

## 2. Requirement Classification Matrix

Each item is classified according to the required standard:
* `[PASS]`: Already correctly implemented and verified.
* `[PARTIAL]`: Implemented but requires improvement or hardening.
* `[FAIL]`: Missing, incorrect, or unsafe.
* `[UNKNOWN]`: Cannot verify yet.

| Area / Phase | Requirement | Current Status | Classification | Gap / Action Required |
| :--- | :--- | :--- | :---: | :--- |
| **Phase 0 & 1** | Application Entry & Bootstrapping | `main.py` boots Flet 1.0 with responsive viewport and `init_db()` | `[PASS]` | Verified working. |
| **Phase 1** | Test Suite Verification | Pytest automated test execution across components and services | `[PASS]` | Real test suite passes, recording detailed counts in `docs/test_results.md`. |
| **Phase 2** | Cloud AI Default Preference | Privacy-first default: fresh installs MUST default `cloud_ai_enabled = false` | `[FAIL]` | `ai_service.py` and `personalization_screen.py` currently default to `"true"`. Must be changed to `"false"`. |
| **Phase 3** | AI Data Minimization | Minimum necessary data principle: do not send full financial context for generic queries | `[FAIL]` | `_build_gemini_system_instruction` currently sends user's full income, expenses, category breakdown, and last 6 transactions unconditionally. |
| **Phase 4** | AI Transaction Safety | Candidate Preview -> User Confirmation (`[Confirm]`, `[Edit]`, `[Cancel]`) -> Database Write | `[PARTIAL]` | Implemented in `ai_service.py` & `assistant_screen.py`. Needs edge-case regression tests (malformed input, duplicate confirm, missing category). |
| **Phase 5** | Financial Calculation Safety | 100% deterministic integer minor units (paise) math; zero LLM math dependency | `[PASS]` | `CalculationService` strictly computes from SQLite using integer paise. Boundary tests verified. |
| **Phase 6** | Database & Storage Abstraction | Platform-aware persistent storage in Android app sandbox (`/data/user/0/...`) | `[PASS]` | `utils/storage.py` and `database/database.py` verify directory writability and `PRAGMA integrity_check`. |
| **Phase 7** | Secrets & Environment Security | No hardcoded API keys in source code, assets, git tracking, or packages | `[PARTIAL]` | Zero hardcoded keys in git. Need explicit documentation for production backend proxy architecture. |
| **Phase 8** | Production Logging | Production logs do not expose sensitive financial figures or complete AI prompts | `[PARTIAL]` | Audit all `logging` statements in services to ensure raw transaction prompts/payloads are sanitized. |
| **Phase 9** | Development Data Cleanup | Exclude local test database (`data/`), CSV exports, tests, and caches from release APK | `[PARTIAL]` | Gitignored, but `pyproject.toml` lacks explicit `exclude` configuration for `tool.flet.app`. |
| **Phase 10** | Documentation Consistency | All documentation aligned with Flet 1.0 (no Kivy/Buildozer remnants) | `[PASS]` | `README.md` and `docs/` reflect Flet toolchain. |
| **Phase 11 & 12**| Android Build & Device Readiness | Reproducible `flet build apk` workflow targeting `org.spendora.spendora` | `[PARTIAL]` | Configured in `pyproject.toml`. Requires verification of generated APK bundle. |
| **Phase 13** | Offline Safety | App functions gracefully in Airplane Mode without network or Gemini crashes | `[PARTIAL]` | Local database and deterministic services operate offline; need explicit offline regression tests. |
| **Phase 14 & 15**| Release Artifact & Report | Release APK/AAB builds with verified status report | `[UNKNOWN]` | To be generated in final phases. |

---

## 3. Detailed Component Findings

### 3.1 Cloud AI Preference Default (Phase 2 Blocker)
* **Finding:** In [`services/ai_service.py`](file:///c:/Users/vishn/Desktop/spendora/services/ai_service.py#L130), `get_preference(user_id, "cloud_ai_enabled", "true")` defaults to `"true"`.
* **Finding:** In [`screens/personalization/personalization_screen.py`](file:///c:/Users/vishn/Desktop/spendora/screens/personalization/personalization_screen.py#L659), `cloud_ai_pref` defaults to `"true"`.
* **Correction Required:** All defaults must be changed to `"false"`. A new user must have Cloud AI disabled by default. The local heuristic financial assistant must handle all queries unless the user explicitly toggles Cloud AI on in Settings.

### 3.2 AI Data Minimization (Phase 3 Blocker)
* **Finding:** In [`services/ai_service.py`](file:///c:/Users/vishn/Desktop/spendora/services/ai_service.py#L664), `_build_gemini_system_instruction(context)` appends:
  * Baseline monthly income and fixed commitments
  * Current month income, expenses, and net balance
  * 50-30-20 budget audit
  * Full category breakdown
  * Recent 6 transactions with descriptions, amounts, and dates
* **Correction Required:** Implement a query intent classifier / context filter that determines the minimum necessary data scope:
  * `GENERIC_FINANCIAL_KNOWLEDGE` (e.g., *"What is the 50/30/20 rule?"*): Send **ZERO** user financial records or transactions.
  * `CATEGORY_SPECIFIC` (e.g., *"How much did I spend on dining?"*): Send only the aggregate total for that specific category.
  * `AFFORDABILITY_OR_BUDGET` (e.g., *"Can I afford X?"*): Send only net surplus and safe daily spend; exclude itemized recent transactions.
  * `RECENT_TRANSACTIONS_INQUIRY` (e.g., *"What did I buy recently?"*): Send only recent transactions.

### 3.3 Build Exclusions in `pyproject.toml` (Phase 9 Blocker)
* **Finding:** In [`pyproject.toml`](file:///c:/Users/vishn/Desktop/spendora/pyproject.toml#L28), `[tool.flet.app]` specifies `path = "."` without an `exclude` list.
* **Correction Required:** Add:
  ```toml
  [tool.flet.app]
  path = "."
  exclude = [
      "data",
      "tests",
      "docs",
      "*.csv",
      "*.db",
      ".env*",
      "requirements-dev.txt",
      "stitch_ai_personal_expense_tracker",
      "web_ui",
  ]
  ```

---

## 4. Remediation Plan

The following ordered sequence will be executed strictly:
1. **Phase 1:** Run pytest, record real baseline results in `docs/test_results.md`.
2. **Phase 2:** Switch Cloud AI default to `false`, preserve existing explicit preferences, update tests.
3. **Phase 3:** Implement Minimum Necessary Data filter for Cloud AI context, add test suite for query scoping.
4. **Phase 4:** Harden transaction candidate confirmation with edge case tests (missing category, ambiguous inputs).
5. **Phase 5 & 6:** Verify financial calculations and storage integrity.
6. **Phase 7 & 8:** Verify secret sanitization and production log filtering.
7. **Phase 9:** Configure `exclude` in `pyproject.toml`.
8. **Phase 10:** Synchronize documentation.
9. **Phase 11 - 14:** Build APK/AAB and verify artifact.
10. **Phase 15:** Generate `docs/final_release_report.md`.
