"""
Spendora — Application-wide settings and constants.

All configuration is centralised here. Sensitive values (API keys etc.)
are loaded from environment variables via python-dotenv and are never
hard-coded.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
DATABASE_PATH: Path = DATA_DIR / "spendora.db"
ASSETS_DIR: Path = BASE_DIR / "assets"

# Ensure the data directory exists at import time (safe to call repeatedly).
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv(BASE_DIR / ".env")

DEBUG: bool = os.getenv("SPENDORA_DEBUG", "false").lower() == "true"
LOG_LEVEL: str = os.getenv("SPENDORA_LOG_LEVEL", "WARNING")

# AI API keys — loaded from environment, NEVER hard-coded.
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"

# ---------------------------------------------------------------------------
# Money / Currency
# ---------------------------------------------------------------------------

# Minor units per major unit for each supported currency.
# INR uses paise (100 paise = 1 rupee).
# Architecture supports additional currencies: add entries here.
CURRENCY_MINOR_UNITS: dict[str, int] = {
    "INR": 100,
    "USD": 100,
    "EUR": 100,
    "GBP": 100,
}

DEFAULT_CURRENCY: str = "INR"

CURRENCY_SYMBOLS: dict[str, str] = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}

# ---------------------------------------------------------------------------
# Profession Catalogue
# ---------------------------------------------------------------------------

PROFESSIONS: list[str] = [
    "Student",
    "Software Engineer",
    "Developer",
    "Doctor",
    "Teacher",
    "Business Owner",
    "Freelancer",
    "Government Employee",
    "Private Employee",
    "Other",
]

# ---------------------------------------------------------------------------
# Default Category Suggestions per Profession
# ---------------------------------------------------------------------------
# Each entry is a dict with name, icon, color, and optional subcategories.
# These are *suggestions* — the user always has full control.

PROFESSION_CATEGORY_SUGGESTIONS: dict[str, list[dict]] = {
    "Student": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Canteen", "Groceries", "Food Delivery"]},
        {"name": "Transport", "icon": "train", "color": "#4ECDC4",
         "subcategories": ["Bus", "Metro", "Cab"]},
        {"name": "Education", "icon": "book-open-variant", "color": "#45B7D1",
         "subcategories": ["Books", "Stationery", "Courses", "Fees"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Movies", "Games", "Subscriptions"]},
        {"name": "Shopping", "icon": "shopping", "color": "#BB8FCE",
         "subcategories": ["Clothes", "Electronics", "Accessories"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Medicine", "Doctor", "Gym"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Mobile Recharge", "Internet"]},
    ],
    "Software Engineer": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Restaurant", "Groceries", "Food Delivery"]},
        {"name": "Rent", "icon": "home", "color": "#5DADE2",
         "subcategories": ["Rent", "Maintenance"]},
        {"name": "Transport", "icon": "car", "color": "#4ECDC4",
         "subcategories": ["Fuel", "Bus", "Cab", "Metro"]},
        {"name": "Technology", "icon": "laptop", "color": "#45B7D1",
         "subcategories": ["Software", "Cloud Services", "Gadgets", "Accessories"]},
        {"name": "Internet", "icon": "wifi", "color": "#1ABC9C",
         "subcategories": ["Broadband", "Mobile Data"]},
        {"name": "Education", "icon": "book-open-variant", "color": "#45B7D1",
         "subcategories": ["Courses", "Books", "Certifications"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Subscriptions", "Movies", "Games"]},
        {"name": "Shopping", "icon": "shopping", "color": "#BB8FCE",
         "subcategories": ["Clothes", "Electronics", "Accessories"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Medicine", "Doctor", "Gym", "Insurance"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Gas", "Mobile"]},
        {"name": "Savings", "icon": "piggy-bank", "color": "#A9DFBF",
         "subcategories": ["Emergency Fund", "Investments"]},
    ],
    "Developer": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Restaurant", "Groceries", "Food Delivery"]},
        {"name": "Rent", "icon": "home", "color": "#5DADE2",
         "subcategories": ["Rent", "Maintenance"]},
        {"name": "Transport", "icon": "car", "color": "#4ECDC4",
         "subcategories": ["Fuel", "Bus", "Cab"]},
        {"name": "Technology", "icon": "laptop", "color": "#45B7D1",
         "subcategories": ["Software", "Cloud Services", "Gadgets", "Domain/Hosting"]},
        {"name": "Internet", "icon": "wifi", "color": "#1ABC9C",
         "subcategories": ["Broadband", "Mobile Data"]},
        {"name": "Education", "icon": "book-open-variant", "color": "#45B7D1",
         "subcategories": ["Courses", "Books", "Certifications"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Subscriptions", "Movies", "Games"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Medicine", "Doctor", "Gym"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Mobile"]},
    ],
    "Doctor": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Restaurant", "Groceries", "Food Delivery"]},
        {"name": "Rent", "icon": "home", "color": "#5DADE2",
         "subcategories": ["Rent", "Maintenance"]},
        {"name": "Transport", "icon": "car", "color": "#4ECDC4",
         "subcategories": ["Fuel", "Cab", "Parking"]},
        {"name": "Professional", "icon": "stethoscope", "color": "#5DADE2",
         "subcategories": ["Medical Equipment", "Journals", "Conferences"]},
        {"name": "Education", "icon": "book-open-variant", "color": "#45B7D1",
         "subcategories": ["CME", "Books", "Courses"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Insurance", "Personal Health"]},
        {"name": "Shopping", "icon": "shopping", "color": "#BB8FCE",
         "subcategories": ["Clothes", "Accessories"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Mobile", "Internet"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Subscriptions", "Dining Out", "Travel"]},
    ],
    "Teacher": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Canteen", "Groceries", "Restaurant"]},
        {"name": "Transport", "icon": "bus", "color": "#4ECDC4",
         "subcategories": ["Bus", "Auto", "Fuel"]},
        {"name": "Education", "icon": "book-open-variant", "color": "#45B7D1",
         "subcategories": ["Books", "Stationery", "Courses"]},
        {"name": "Shopping", "icon": "shopping", "color": "#BB8FCE",
         "subcategories": ["Clothes", "Household"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Medicine", "Doctor"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Mobile", "Internet"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Movies", "Subscriptions"]},
    ],
    "Business Owner": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Restaurant", "Groceries", "Food Delivery"]},
        {"name": "Business", "icon": "briefcase", "color": "#2ECC71",
         "subcategories": ["Operations", "Marketing", "Staff", "Rent", "Supplies"]},
        {"name": "Transport", "icon": "car", "color": "#4ECDC4",
         "subcategories": ["Fuel", "Cab", "Flights"]},
        {"name": "Technology", "icon": "laptop", "color": "#45B7D1",
         "subcategories": ["Software", "Hardware", "Cloud", "Website"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Insurance", "Gym", "Doctor"]},
        {"name": "Shopping", "icon": "shopping", "color": "#BB8FCE",
         "subcategories": ["Clothes", "Office Supplies"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Internet", "Mobile"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Dining Out", "Travel", "Events"]},
    ],
    "Freelancer": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Restaurant", "Groceries", "Food Delivery"]},
        {"name": "Workspace", "icon": "desk", "color": "#5DADE2",
         "subcategories": ["Co-working", "Home Office", "Equipment"]},
        {"name": "Technology", "icon": "laptop", "color": "#45B7D1",
         "subcategories": ["Software", "Cloud Services", "Domain/Hosting", "Tools"]},
        {"name": "Internet", "icon": "wifi", "color": "#1ABC9C",
         "subcategories": ["Broadband", "Mobile Data"]},
        {"name": "Transport", "icon": "car", "color": "#4ECDC4",
         "subcategories": ["Fuel", "Cab", "Metro"]},
        {"name": "Education", "icon": "book-open-variant", "color": "#45B7D1",
         "subcategories": ["Courses", "Books", "Certifications"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Insurance", "Gym", "Doctor"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Subscriptions", "Movies", "Games"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Mobile"]},
    ],
    "Government Employee": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Canteen", "Groceries", "Restaurant"]},
        {"name": "Transport", "icon": "bus", "color": "#4ECDC4",
         "subcategories": ["Bus", "Auto", "Fuel", "Train"]},
        {"name": "Shopping", "icon": "shopping", "color": "#BB8FCE",
         "subcategories": ["Clothes", "Household"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Medicine", "Doctor", "Insurance"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Gas", "Mobile", "Internet"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Movies", "Travel", "Subscriptions"]},
        {"name": "Education", "icon": "book-open-variant", "color": "#45B7D1",
         "subcategories": ["Children Education", "Books", "Courses"]},
        {"name": "Savings", "icon": "piggy-bank", "color": "#A9DFBF",
         "subcategories": ["LIC", "PF", "PPF", "FD"]},
    ],
    "Private Employee": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Restaurant", "Groceries", "Food Delivery"]},
        {"name": "Rent", "icon": "home", "color": "#5DADE2",
         "subcategories": ["Rent", "Maintenance"]},
        {"name": "Transport", "icon": "car", "color": "#4ECDC4",
         "subcategories": ["Fuel", "Bus", "Cab", "Metro"]},
        {"name": "Shopping", "icon": "shopping", "color": "#BB8FCE",
         "subcategories": ["Clothes", "Electronics", "Accessories"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Insurance", "Gym", "Medicine", "Doctor"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Gas", "Mobile", "Internet"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Subscriptions", "Movies", "Dining Out"]},
        {"name": "Education", "icon": "book-open-variant", "color": "#45B7D1",
         "subcategories": ["Courses", "Books"]},
        {"name": "Savings", "icon": "piggy-bank", "color": "#A9DFBF",
         "subcategories": ["Emergency Fund", "Investments", "SIP"]},
    ],
    "Other": [
        {"name": "Food", "icon": "food", "color": "#FF6B6B",
         "subcategories": ["Restaurant", "Groceries", "Food Delivery"]},
        {"name": "Transport", "icon": "car", "color": "#4ECDC4",
         "subcategories": ["Fuel", "Bus", "Cab"]},
        {"name": "Shopping", "icon": "shopping", "color": "#BB8FCE",
         "subcategories": ["Clothes", "Household", "Electronics"]},
        {"name": "Health", "icon": "heart-pulse", "color": "#82E0AA",
         "subcategories": ["Medicine", "Doctor"]},
        {"name": "Utilities", "icon": "lightning-bolt", "color": "#F0B27A",
         "subcategories": ["Electricity", "Water", "Mobile", "Internet"]},
        {"name": "Entertainment", "icon": "television-play", "color": "#F7DC6F",
         "subcategories": ["Movies", "Subscriptions"]},
    ],
}

# ---------------------------------------------------------------------------
# UI / Theme
# ---------------------------------------------------------------------------

THEME_PRIMARY_COLOR: str = "#9058FF"
THEME_ACCENT_COLOR: str = "#4ECDC4"
THEME_STYLE: str = "Dark"  # "Light" or "Dark"

APP_NAME: str = "Spendora"
APP_VERSION: str = "0.1.0"

APP_BG_DARK: tuple = (8 / 255, 15 / 255, 25 / 255, 1)
APP_BG_PANEL: tuple = (18 / 255, 28 / 255, 42 / 255, 1)
APP_BG_CARD: tuple = (27 / 255, 38 / 255, 54 / 255, 1)
APP_LINE: tuple = (110 / 255, 128 / 255, 160 / 255, 0.38)
APP_TEXT: tuple = (240 / 255, 244 / 255, 255 / 255, 1)
APP_MUTED_TEXT: tuple = (160 / 255, 176 / 255, 196 / 255, 1)
APP_ACCENT: tuple = (144 / 255, 88 / 255, 255 / 255, 1)
APP_ACCENT_2: tuple = (79 / 255, 175 / 255, 255 / 255, 1)
APP_SUCCESS: tuple = (75 / 255, 202 / 255, 156 / 255, 1)
APP_DANGER: tuple = (239 / 255, 92 / 255, 92 / 255, 1)
APP_ORANGE: tuple = (248 / 255, 135 / 255, 89 / 255, 1)

