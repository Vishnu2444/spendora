# Spendora — AI Personal Expense Tracker

Spendora is a privacy-first, production-quality personal expense tracker built with Python and KivyMD, targeting Android packaging via Buildozer.

## Core Architectural Invariants

1. **Deterministic Financial Arithmetic**: All financial calculations are executed in pure Python using integer paise (1 INR = 100 paise). Arithmetic is **never** delegated to an LLM.
2. **Category Ownership**: All categories and subcategories are user-owned. AI suggestions are explicitly presented for user approval (accept/reject/edit) and never overwrite user-created data silently.
3. **Layered Modular Architecture**:
   - **UI Layer**: KivyMD 2.0 (Material Design 3)
   - **Service Layer**: Pure Python business logic and validation
   - **Repository Layer**: Data access isolation
   - **Database Layer**: SQLite with SQLAlchemy ORM (WAL mode, foreign key enforcement)
   - **AI Layer (Phase 5+)**: Intent classification and explanatory assistance; strictly separated from data storage and arithmetic.

## Project Structure

```
spendora/
├── main.py                     # KivyMD application entry point & router
├── config/
│   ├── __init__.py
│   └── settings.py             # App constants, profession categories, theming
├── database/
│   ├── __init__.py
│   ├── database.py             # Engine, WAL mode, session factory
│   ├── models.py               # ORM models (User, Category, Subcategory, Transaction, UserPreference)
│   └── repositories/
│       ├── __init__.py
│       ├── user_repository.py
│       ├── category_repository.py
│       └── transaction_repository.py
├── services/
│   ├── __init__.py
│   ├── profile_service.py      # Profile management & input validation
│   └── category_service.py     # Category/subcategory CRUD & suggestion acceptance
├── screens/
│   ├── __init__.py
│   ├── onboarding/
│   │   ├── __init__.py
│   │   ├── welcome_screen.py        # Name & profession selection
│   │   └── category_setup_screen.py # Suggested category review & accept/reject
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── dashboard_screen.py      # Primary overview & quick actions
│   ├── transactions/
│   │   ├── __init__.py
│   │   └── transactions_screen.py   # Transaction history & management
│   ├── analytics/
│   │   ├── __init__.py
│   │   └── analytics_screen.py      # Spending analytics & charts
│   ├── personalization/
│   │   ├── __init__.py
│   │   └── personalization_screen.py# Category label management
│   └── assistant/
│       ├── __init__.py
│       └── assistant_screen.py      # AI financial assistant
├── utils/
│   ├── __init__.py
│   ├── validators.py           # Pure-Python input validation
│   ├── formatting.py           # Indian currency & date display formatting
│   └── date_utils.py           # Timezone-safe calendar range helpers
├── tests/
│   ├── __init__.py
│   ├── test_calculations.py    # Financial arithmetic & date range tests
│   ├── test_models.py          # SQLAlchemy ORM schema & constraint tests
│   ├── test_validators.py      # Input validation & paise conversion tests
│   ├── test_services.py        # Profile & Category service tests
│   └── test_onboarding_flow.py # End-to-end onboarding pipeline test
├── requirements.txt
├── .gitignore
└── .env.example
```

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Tests
```bash
pytest tests/ -v
```

### 3. Launch the Application
```bash
python main.py
```

## Implementation Phases
- **Phase 1 (Completed)**: Core architecture, SQLite database layer, ORM models, input validators, repositories, services, KivyMD 2.0 navigation bar, and onboarding screens.
- **Phase 2 (Next)**: Full Transaction CRUD system (Income/Expense), category selection, amount validation, and ledger calculations.
- **Phase 3**: Dedicated Personalization management for custom category and subcategory hierarchies.
- **Phase 4**: Financial Analytics, date-range filters, and charting.
- **Phase 5**: Smart categorization rule engine + AI category recommendations.
- **Phase 6**: Privacy-first AI Financial Assistant with validated queries and deterministic explanations.
- **Phase 7**: Historical trend prediction and recurring payment forecasting.
- **Phase 8**: Security hardening, packaging, and Android APK generation via Buildozer.
