# Spendora — Test Execution Results (Post-Hardening Suite)

**Document:** `docs/test_results.md`  
**Execution Timestamp:** 2026-09-30T07:32:39Z  
**Command:** `python -m pytest -q`  
**Platform:** Windows 11 (win32), Python 3.12.7, pytest 9.1.1  
**Result Status:** `SUCCESS` (0 Failures, 0 Errors, 0 Skipped)

---

## 1. Summary Metrics

| Metric | Measured Value |
| :--- | :---: |
| **Total Tests Discovered** | **211** |
| **Passed** | **211** |
| **Failed** | **0** |
| **Skipped** | **0** |
| **Errors** | **0** |
| **Warnings** | **0** |
| **Execution Time** | **9.33 seconds** |
| **Pass Rate** | **100.0%** |

---

## 2. Test Suite Breakdown (Exact Counts)

| Test File | Tests Passed | Focus Area |
| :--- | :---: | :--- |
| `tests/test_ai_confirmation.py` | 12 | Candidate preview/confirmation, cancellation safety, duplicate confirmation protection, missing category fallback, malformed candidate rejection, deletion refusal |
| `tests/test_ai_data_minimization.py` | 8 | Strict Minimum Necessary Data Principle, query scope classification, sensitive field exclusion, zero financial leakage for generic queries |
| `tests/test_ai_service.py` | 14 | Grounded AI advice, local heuristic fallback, affordability checks, privacy default (`cloud_ai_enabled=false`) |
| `tests/test_analytics_service.py` | 7 | Analytics summaries, spending breakdown by category, monthly trends |
| `tests/test_calculation_service.py` | 7 | Gain/loss deterministic calculations, period summaries |
| `tests/test_calculations.py` | 32 | Mathematical precision, zero/large values, paise conversions, period bounds |
| `tests/test_financial_edge_cases.py` | 17 | 1 paisa (₹0.01), ₹999.99, large values, leap year, category deletion safety, uncategorized transactions |
| `tests/test_models.py` | 16 | SQLAlchemy ORM model integrity, relationships, and constraints |
| `tests/test_onboarding_flow.py` | 1 | End-to-end user onboarding pipeline |
| `tests/test_personalization.py` | 5 | Category management, color/icon updates, subcategories, soft-deletion |
| `tests/test_services.py` | 11 | ProfileService and CategoryService suggestions and validation |
| `tests/test_storage.py` | 5 | Platform-aware persistent storage (`utils.storage`), Android path probe, DB initialization |
| `tests/test_theme_and_ui.py` | 20 | Stitch UI color tokens, responsive shells, theme switching, dialog safety |
| `tests/test_transaction_service.py` | 14 | Transaction CRUD operations, input constraints, ownership, filtering |
| `tests/test_transactions_flow.py` | 1 | Complete end-to-end integration: profile creation, txns, balance calculations |
| `tests/test_validators.py` | 41 | Input validators, amount string checks, regex sanitization, paise conversions |
| **Total** | **211** | **Full Project Verification** |

---

## 3. Key Hardening Validations

1. **Privacy-First Default (`cloud_ai_enabled = false`)**: Verified fresh installs do not call Cloud AI unless explicitly toggled on by user.
2. **AI Data Minimization**: Verified that generic budgeting questions ("What is the 50/30/20 rule?") send zero transactions, zero accounts, and zero monthly totals to Gemini.
3. **Candidate Transaction Flow**: Verified that all AI transaction intents produce preview candidates requiring explicit user confirmation before writing to the database; cancel produces zero mutations; duplicates are rejected.
4. **Deterministic Arithmetic**: 100% of balances, gain/loss, and totals are computed deterministically in Python/SQL integer paise math.
