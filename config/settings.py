"""
Leaksee — Application-wide settings and constants.

All configuration is centralised here. Sensitive values (API keys etc.)
are loaded from environment variables via python-dotenv and are never
hard-coded.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from utils.storage import get_data_dir, get_database_path, get_database_url

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = get_data_dir()
DATABASE_PATH: Path = get_database_path()
ASSETS_DIR: Path = BASE_DIR / "assets"

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv(BASE_DIR / ".env")

DEBUG: bool = (os.getenv("LEAKSEE_DEBUG") or os.getenv("SPENDORA_DEBUG", "false")).lower() == "true"
LOG_LEVEL: str = os.getenv("LEAKSEE_LOG_LEVEL") or os.getenv("SPENDORA_LOG_LEVEL", "WARNING")

# AI API keys — loaded from environment, NEVER hard-coded.
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL: str = get_database_url()

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
# UI / Theme — Google Stitch "LEAKSEE" Design System
# ---------------------------------------------------------------------------

APP_NAME: str = "LEAKSEE"
APP_VERSION: str = "2.4"

# Primary Brand (Royal & Electric Blue)
COLOR_PRIMARY: str = "#0041DC"
COLOR_PRIMARY_CONTAINER: str = "#2A5BFF"
COLOR_ON_PRIMARY: str = "#FFFFFF"
COLOR_PRIMARY_FIXED: str = "#DDE1FF"
COLOR_PRIMARY_FIXED_DIM: str = "#B8C4FF"

# Secondary (Vibrant Purple)
COLOR_SECONDARY: str = "#712AE2"
COLOR_SECONDARY_CONTAINER: str = "#8A4CFC"
COLOR_ON_SECONDARY_CONTAINER: str = "#FFFBFF"
COLOR_SECONDARY_FIXED: str = "#EADDFF"
COLOR_ON_SECONDARY: str = "#FFFFFF"

# Tertiary (Flame Coral / Orange)
COLOR_TERTIARY: str = "#A41F00"
COLOR_TERTIARY_CONTAINER: str = "#CA3513"
COLOR_TERTIARY_FIXED: str = "#FFDAD2"
COLOR_CORAL_ACCENT: str = "#FF5A36"
COLOR_EMERALD_ACCENT: str = "#10B981"

# Surfaces & Backgrounds
COLOR_BACKGROUND: str = "#FAF8FF"
COLOR_SURFACE: str = "#FAF8FF"
COLOR_SURFACE_CARD: str = "#FFFFFF"
COLOR_SURFACE_LOW: str = "#F2F3FF"
COLOR_SURFACE_CONTAINER: str = "#EAEDFF"
COLOR_SURFACE_HIGH: str = "#E2E7FD"
COLOR_SURFACE_HIGHEST: str = "#DDE2F7"

# Typography & Borders
COLOR_ON_SURFACE: str = "#151B2B"
COLOR_ON_SURFACE_VARIANT: str = "#434656"
COLOR_OUTLINE: str = "#747688"
COLOR_OUTLINE_VARIANT: str = "#C4C5D9"

# Feedback & Alerts
COLOR_ERROR: str = "#BA1A1A"
COLOR_ERROR_CONTAINER: str = "#FFDAD6"
COLOR_SUCCESS: str = "#10B981"
COLOR_GROWTH: str = "#10B981"

# Theming compatibility
THEME_PRIMARY_COLOR: str = COLOR_PRIMARY
THEME_ACCENT_COLOR: str = COLOR_PRIMARY_CONTAINER
THEME_STYLE: str = "Light"

# Component Aliases
APP_BG_DARK: str = COLOR_BACKGROUND
APP_BG_PANEL: str = COLOR_SURFACE_LOW
APP_BG_CARD: str = COLOR_SURFACE_CARD
APP_LINE: str = COLOR_OUTLINE_VARIANT
APP_TEXT: str = COLOR_ON_SURFACE
APP_MUTED_TEXT: str = COLOR_ON_SURFACE_VARIANT
APP_ACCENT: str = COLOR_PRIMARY_CONTAINER
APP_ACCENT_2: str = COLOR_SECONDARY
APP_SUCCESS: str = COLOR_SUCCESS
APP_DANGER: str = COLOR_ERROR
APP_ORANGE: str = COLOR_CORAL_ACCENT



