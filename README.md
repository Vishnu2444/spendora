@"
# 💰 Spendora

> AI-assisted personal expense tracker built with Python and Flet.

**Created and maintained by VISHNU A**

[![Tests](https://img.shields.io/badge/tests-211%20passed-brightgreen)](#testing)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flet-purple)](https://flet.dev/)
[![Platform](https://img.shields.io/badge/platform-Android%20%7C%20Desktop-teal)](#android)

Spendora is a personal finance application focused on expense tracking, financial
analytics, privacy, and AI-assisted organization.

---

## 👨‍💻 Creator

**VISHNU A**

BE Computer Science & Engineering | 2026

GitHub: https://github.com/vishnu2444

Spendora is independently developed and maintained by VISHNU A.

---

## ✨ Features

### 📊 Dashboard

- Current financial position
- Income and expense summaries
- Gain/loss information
- Recent transaction history
- Quick transaction entry

### 💳 Transaction Management

- Income and expense tracking
- Custom categories and subcategories
- Transaction editing and deletion
- Search and filtering
- Date-based transaction handling

### 📈 Financial Analytics

- Custom date-range analysis
- Monthly and yearly views
- Gain/loss calculations
- Spending distribution
- Category-level analysis
- Period comparisons
- Spending insights

### 🎨 Personalization

- User profile
- Profession-based personalization
- Custom categories
- Custom subcategories
- Category colors and icons
- Financial baseline settings
- Multi-currency formatting

### 🤖 AI Assistance

Spendora can optionally use Google Gemini for AI-assisted functionality such as:

- Transaction category suggestions
- Financial questions
- Context-aware financial assistance
- Expense-related insights

AI suggestions are presented for user review rather than silently modifying
financial records.

---

## 🏗️ Architecture

Spendora is built around a Python application architecture with Flet for the
user interface.

```text
Spendora
│
├── main.py
│
├── config/
│   ├── settings.py
│   └── theme_manager.py
│
├── database/
│   ├── database.py
│   ├── models.py
│   └── repositories/
│
├── services/
│   ├── transaction_service.py
│   ├── calculation_service.py
│   ├── analytics_service.py
│   ├── category_service.py
│   ├── profile_service.py
│   └── ai_service.py
│
├── components/
│
├── screens/
│   ├── onboarding/
│   ├── dashboard/
│   ├── transactions/
│   ├── analytics/
│   ├── personalization/
│   └── assistant/
│
├── utils/
│
├── tests/
│
├── assets/
│
├── docs/
│
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt