# Spendora — AI Personal Expense Tracker

[![Tests](https://img.shields.io/badge/tests-139%20passed-brightgreen)](#automated-testing)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-KivyMD%202.0%20(MD3)-purple)](https://kivymd.readthedocs.io/)
[![AI](https://img.shields.io/badge/AI-Google%20Gemini%203.8%20Flash-orange)](https://ai.google.dev/)
[![Platform](https://img.shields.io/badge/platform-Android%20%7C%20Desktop-teal)](#packaging-for-android)

**Spendora** is a privacy-first, production-quality mobile expense tracking application designed for Android and desktop. It combines strict deterministic financial calculations with Google Gemini AI for smart category prediction and data-grounded conversational financial coaching.

---

## Core Architectural Invariants

1. **Deterministic Financial Arithmetic**:
   - Every financial calculation is executed in pure Python using integer paise minor units ($1\text{ INR} = 100\text{ paise}$).
   - Floating-point calculations are strictly forbidden in transaction ledgers to eliminate rounding errors.
   - Arithmetic is **never** delegated to an LLM.
2. **Grounded AI Assistant (Zero Hallucination Guarantee)**:
   - The AI assistant is strictly read-only.
   - All financial figures reported by the AI are computed deterministically by the calculation engine and injected as immutable Ground Truth into system prompts.
   - If an API key or network connection is unavailable, Spendora gracefully falls back to local deterministic responses.
3. **Category & Data Ownership**:
   - All categories and subcategories are user-owned.
   - AI category recommendations are presented explicitly for review (accept, reject, or edit) and never overwrite user-defined categories.
4. **Privacy & Security**:
   - Financial figures and transaction notes are never leaked in debug/info logs.
   - API keys are loaded securely from environment variables (`.env`).
   - SQLite database runs locally with Write-Ahead Logging (WAL) and foreign key constraints enabled.

---

## Project Structure

```
spendora/
├── main.py                             # Root application entry point & router
├── buildozer.spec                      # Production Android build specification
├── requirements.txt                    # Pinned dependencies
├── .env.example                        # Environment variables template
├── assets/
│   ├── icon.png                        # App icon (512x512)
│   └── presplash.png                   # Splash screen (1080x1920)
├── config/
│   ├── __init__.py
│   └── settings.py                     # App constants, currencies, theming, professions
├── database/
│   ├── __init__.py
│   ├── database.py                     # Engine, WAL mode, session factory
│   ├── models.py                       # SQLAlchemy ORM models (User, Category, Transaction, etc.)
│   └── repositories/
│       ├── __init__.py
│       ├── user_repository.py
│       ├── category_repository.py
│       └── transaction_repository.py   # Aggregated analytical & balance queries
├── services/
│   ├── __init__.py
│   ├── profile_service.py              # User onboarding & profile management
│   ├── category_service.py             # Category & subcategory CRUD & lifecycle
│   ├── transaction_service.py          # Transaction validation & management
│   ├── calculation_service.py          # Deterministic financial calculation engine
│   ├── analytics_service.py            # Arbitrary date-range analysis & comparisons
│   └── ai_service.py                   # Gemini category prediction & grounded assistant
├── components/
│   ├── __init__.py
│   ├── transaction_card.py             # MD3 signed transaction card
│   ├── distribution_bar.py             # Hardware-accelerated visual percentage gauge
│   ├── category_breakdown_item.py      # Category row with share percentage & gauge
│   ├── category_management_card.py     # Interactive category management card
│   ├── color_picker_row.py             # Color swatch selection palette
│   └── chat_bubble.py                  # Conversational message bubble widget
├── screens/
│   ├── __init__.py
│   ├── onboarding/
│   │   ├── welcome_screen.py           # Onboarding Step 1 (Profile & Profession)
│   │   └── category_setup_screen.py    # Onboarding Step 2 (AI/Curated Categories)
│   ├── dashboard/
│   │   └── dashboard_screen.py         # Real-time balance, burn rate & recent transactions
│   ├── transactions/
│   │   ├── transactions_screen.py      # Searchable, filterable transaction list
│   │   └── add_edit_transaction_screen.py # Full-screen transaction creator & editor
│   ├── analytics/
│   │   └── analytics_screen.py         # Date-range performance, distributions & insights
│   ├── personalization/
│   │   └── personalization_screen.py   # Custom categories, subcategories & profile settings
│   └── assistant/
│       └── assistant_screen.py         # Grounded AI financial assistant
├── utils/
│   ├── __init__.py
│   ├── validators.py                   # Input validation & paise conversion
│   ├── formatting.py                   # Currency (Indian numbering) & date formatting
│   └── date_utils.py                   # Timezone-safe calendar range helpers
└── tests/                              # Comprehensive test suite (139 passing tests)
```

---

## Features Walkthrough

### 1. Dashboard
- **Live Financial Position**: Real-time Net Balance, Monthly Income, Total Expenses, and Gain/Loss badge.
- **Burn Status**: Daily average spending rate with trajectory indicators.
- **Recent Transactions Feed**: Quick access to recent activity with tap-to-edit.
- **Quick Action (+ Add)**: One-tap launcher for logging income or expenses.

### 2. Transactions Manager
- **Full-Screen Creator & Editor**: Type toggle (Expense/Income), decimal amount input, category and dynamic subcategory dropdowns, calendar date navigators, and deletion confirmation.
- **Live Search**: Instant search filtering across transaction descriptions and notes.
- **Type Filtering**: One-tap toggles for All, Expenses, and Income.

### 3. Financial Analytics & Date-Range Engine
- **Arbitrary Date Ranges**: Evaluate financial performance between **any two user-selected dates**.
- **Preset Toggles**: `This Month`, `Last Month`, `30 Days`, `This Year`, and `Custom Range`.
- **Period-over-Period Comparisons**: Automatically compares any selected window with the preceding equivalent timeframe (e.g. `Expenses ↓ 14.5% vs previous period`).
- **Spending Distribution**: Ranked category breakdown with custom colored distribution gauges and percentage shares.
- **Spending Insights**: Identifies peak spending days, largest single purchases, and average transaction sizes.

### 4. Personalization & Settings
- **Category Customization**: Create custom categories with custom icons and color swatches.
- **Subcategory Hierarchy**: Add, rename, or soft-delete subcategories under any parent category.
- **Soft-Delete Safety**: Soft-deletes categories to preserve historical transaction linkages.
- **Profile & Financial Baselines**: Edit user name, monthly income target, and fixed expenses.
- **Multi-Currency Support**: Switch between **INR (₹)**, **USD ($)**, **EUR (€)**, and **GBP (£)** with instant app-wide formatting updates.

### 5. Grounded AI Financial Assistant
- **Google Gemini 3.8 Flash**: Conversational AI assistant analyzing your actual financial records.
- **Strict Anti-Hallucination**: Answers natural-language questions (*"How much did I spend this month?"*, *"Am I spending more than I earn?"*) strictly based on verified calculation engine data.
- **Read-Only Operation**: Guaranteed never to alter, delete, or fabricate records.
- **Offline Mode**: Operates seamlessly with deterministic local heuristic responses when no API key or network connection is available.

---

## Getting Started (Local Development)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/spendora.git
cd spendora

# Install required Python packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional for AI features)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your Google Gemini API key to `.env`:
```ini
GEMINI_API_KEY=your_actual_gemini_api_key
```
*(Note: Spendora runs fully offline without an API key using curated suggestions and local deterministic responses).*

### 3. Run Automated Tests
```bash
pytest tests/ -v
```
All 139 tests will run and pass across models, validators, calculations, repositories, services, and integration pipelines.

### 4. Launch the App
```bash
python main.py
```

---

## Packaging for Android (Buildozer)

Spendora is pre-configured for Android deployment using Buildozer and `python-for-android`.

### Prerequisites (Linux / WSL2 recommended for Buildozer)
Install system build dependencies:
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
pip install --upgrade buildozer cython virtualenv
```

### Build Debug APK
Run Buildozer in the project root:
```bash
buildozer android debug
```
The compiled APK will be generated in `bin/` (e.g., `bin/spendora-1.0.0-arm64-v8a-debug.apk`).

### Deploy Directly to Connected Android Device
Enable **USB Debugging** on your Android device and run:
```bash
buildozer android deploy run
```

---

## License
MIT License. Crafted with precision for privacy-conscious personal finance.
