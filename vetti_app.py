import io
import json
import re
import sqlite3
import uuid
from base64 import b64encode
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Vetti | Autonomous Audit-to-Recovery Agent", layout="wide")

DB_PATH = Path(__file__).with_name("vetti_audit_history.db")
LOGO_PATH = Path(__file__).with_name("vetti_logo.svg")

ELECTRIC_COBALT = "#3B82F6"
COBALT_SOFT = "#60A5FA"
SLATE = "#0F172A"
SLATE_CARD = "rgba(23, 32, 51, 0.68)"
SLATE_ALT = "#172033"
SLATE_MUTED = "#94A3B8"
SUCCESS = "#22C55E"
ALERT = "#F97316"
DANGER = "#EF4444"
WHITE = "#F8FAFC"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_runs (
                audit_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                vendor_email TEXT NOT NULL,
                invoice_filename TEXT NOT NULL,
                items_scanned INTEGER NOT NULL,
                items_flagged INTEGER NOT NULL,
                total_overcharge REAL NOT NULL,
                tolerance_pct REAL NOT NULL,
                payment_hold_status TEXT NOT NULL,
                gmail_status TEXT NOT NULL,
                recovery_status TEXT NOT NULL,
                historical_vendor_trust_score REAL NOT NULL,
                notes TEXT NOT NULL
            )
            """
        )


def inject_global_styles() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(59,130,246,0.16), transparent 28%),
                radial-gradient(circle at top right, rgba(96,165,250,0.10), transparent 22%),
                linear-gradient(180deg, #081120 0%, {SLATE} 36%, #0c1628 100%);
            color: {WHITE};
        }}
        [data-testid="stAppViewContainer"] > .main {{
            max-width: 1240px;
            margin: 0 auto;
            padding-left: 1rem;
            padding-right: 1rem;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(15,23,42,0.98) 0%, rgba(9,14,27,0.98) 100%);
            border-right: 1px solid rgba(148,163,184,0.16);
        }}
        h1, h2, h3 {{
            color: {WHITE} !important;
            letter-spacing: -0.02em;
        }}
        p, label, .stMarkdown, .stCaption {{
            color: #D7E3F3;
        }}
        .hero-shell {{
            border-radius: 24px;
            padding: 2.4rem 2.2rem;
            background:
                linear-gradient(135deg, rgba(59,130,246,0.26) 0%, rgba(29,78,216,0.14) 32%, rgba(15,23,42,0.92) 100%);
            border: 1px solid rgba(148,163,184,0.18);
            box-shadow: 0 24px 70px rgba(2, 6, 23, 0.42);
            overflow: hidden;
            position: relative;
        }}
        .hero-grid {{
            display: grid;
            grid-template-columns: minmax(0, 1.5fr) minmax(220px, 0.9fr);
            gap: 1.5rem;
            align-items: center;
            margin-top: 1rem;
        }}
        .hero-shell::after {{
            content: "";
            position: absolute;
            inset: auto -10% -55% 52%;
            height: 320px;
            background: radial-gradient(circle, rgba(96,165,250,0.36) 0%, rgba(96,165,250,0.0) 72%);
            pointer-events: none;
        }}
        .hero-kicker {{
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(96,165,250,0.12);
            border: 1px solid rgba(96,165,250,0.24);
            color: #BFDBFE;
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        .hero-title {{
            font-size: clamp(2.6rem, 5vw, 4.8rem);
            line-height: 0.95;
            margin: 1rem 0 0.8rem 0;
            font-weight: 800;
        }}
        .hero-subheadline {{
            font-size: 1.3rem;
            color: #DBEAFE;
            margin-bottom: 0.9rem;
            font-weight: 700;
        }}
        .hero-copy {{
            max-width: 42rem;
            font-size: 1rem;
            color: #CBD5E1;
        }}
        .hero-proof {{
            display: grid;
            grid-template-columns: repeat(3, minmax(170px, 1fr));
            gap: 0.85rem;
            margin-top: 1.25rem;
            max-width: 100%;
        }}
        .hero-proof-card {{
            padding: 0.95rem 1rem;
            border-radius: 14px;
            background: rgba(15,23,42,0.42);
            border: 1px solid rgba(148,163,184,0.12);
            min-width: 0;
        }}
        .hero-proof-value {{
            color: {WHITE};
            font-size: 1.05rem;
            line-height: 1.15;
            font-weight: 800;
            word-break: keep-all;
            overflow-wrap: normal;
            hyphens: none;
        }}
        .hero-proof-label {{
            color: #BFDBFE;
            font-size: 0.92rem;
            line-height: 1.55;
            margin-top: 0.45rem;
            word-break: normal;
            overflow-wrap: break-word;
        }}
        .hero-logo-panel {{
            width: min(100%, 260px);
            aspect-ratio: 1 / 1;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
            padding: 1.1rem;
            border-radius: 24px;
            background: linear-gradient(180deg, rgba(15,23,42,0.58), rgba(15,23,42,0.2));
            border: 1px solid rgba(148,163,184,0.14);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        }}
        .hero-logo-img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }}
        .feature-card, .glass-card {{
            background: {SLATE_CARD};
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border: 1px solid rgba(148,163,184,0.16);
            border-radius: 12px;
            box-shadow: 0 18px 40px rgba(2, 6, 23, 0.28);
            padding: 1.15rem 1.15rem 1rem 1.15rem;
        }}
        .feature-icon {{
            font-size: 2rem;
            margin-bottom: 0.55rem;
            display: inline-block;
        }}
        .feature-title {{
            font-weight: 700;
            color: {WHITE};
            margin-bottom: 0.35rem;
        }}
        .feature-copy {{
            color: #CBD5E1;
            font-size: 0.96rem;
            line-height: 1.45;
        }}
        .glass-card-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: {WHITE};
            margin-bottom: 0.8rem;
        }}
        .icon-row {{
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin: 0.55rem 0;
            color: #D7E3F3;
        }}
        .icon-row svg {{
            width: 18px;
            height: 18px;
            stroke: {COBALT_SOFT};
            flex: 0 0 auto;
        }}
        .metric-band {{
            margin-top: 1rem;
            border-radius: 16px;
            border: 1px solid rgba(148,163,184,0.14);
            background: linear-gradient(135deg, rgba(23,32,51,0.92) 0%, rgba(15,23,42,0.82) 100%);
            padding: 0.2rem 0.3rem;
        }}
        .top-summary-card {{
            background: linear-gradient(180deg, rgba(23,32,51,0.92), rgba(15,23,42,0.86));
            border: 1px solid rgba(148,163,184,0.12);
            padding: 1.1rem 1.15rem;
            border-radius: 16px;
            box-shadow: 0 12px 28px rgba(2, 6, 23, 0.22);
            height: 100%;
        }}
        .top-summary-label {{
            color: #BFDBFE;
            font-size: 0.84rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        .top-summary-value {{
            color: {WHITE};
            font-size: 2.75rem;
            font-weight: 800;
            line-height: 1.1;
            margin-top: 0.45rem;
        }}
        .top-summary-copy {{
            color: #CBD5E1;
            font-size: 0.95rem;
            line-height: 1.55;
            margin-top: 0.55rem;
        }}
        div[data-testid="metric-container"] {{
            background: linear-gradient(180deg, rgba(23,32,51,0.9), rgba(15,23,42,0.88));
            border: 1px solid rgba(148,163,184,0.12);
            padding: 1rem 1rem 0.9rem 1rem;
            border-radius: 14px;
            box-shadow: 0 12px 28px rgba(2, 6, 23, 0.22);
        }}
        div[data-testid="metric-container"] label,
        div[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
            color: #BFDBFE !important;
            font-weight: 600;
        }}
        div[data-testid="stButton"] > button {{
            border-radius: 12px;
            border: 1px solid rgba(96,165,250,0.28);
            background: linear-gradient(135deg, {ELECTRIC_COBALT} 0%, #2563EB 100%);
            color: white;
            font-weight: 700;
            box-shadow: 0 14px 28px rgba(37,99,235,0.25);
        }}
        div[data-testid="stButton"] > button:hover {{
            border-color: rgba(191,219,254,0.65);
            background: linear-gradient(135deg, #4D97FF 0%, #2B6EF3 100%);
        }}
        .dashboard-section-title {{
            margin-top: 1.6rem;
            margin-bottom: 0.8rem;
            font-size: 1.25rem;
            font-weight: 700;
            color: {WHITE};
        }}
        .dashboard-topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin: 0.8rem 0 1.2rem 0;
            padding: 0.9rem 1rem;
            border-radius: 16px;
            background: linear-gradient(180deg, rgba(23,32,51,0.92), rgba(15,23,42,0.86));
            border: 1px solid rgba(148,163,184,0.12);
            box-shadow: 0 12px 28px rgba(2, 6, 23, 0.22);
        }}
        .demo-banner {{
            margin: 0.75rem 0 1rem 0;
            padding: 0.95rem 1rem;
            border-radius: 14px;
            background: linear-gradient(135deg, rgba(249,115,22,0.22), rgba(234,88,12,0.14));
            border: 1px solid rgba(251,146,60,0.35);
            color: #FFEDD5;
            font-weight: 600;
        }}
        .workflow-card {{
            padding: 1rem 1.05rem;
            border-radius: 14px;
            background: linear-gradient(180deg, rgba(23,32,51,0.92), rgba(15,23,42,0.84));
            border: 1px solid rgba(148,163,184,0.12);
            box-shadow: 0 12px 28px rgba(2, 6, 23, 0.22);
            height: 100%;
        }}
        .workflow-step {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            border-radius: 999px;
            background: rgba(59,130,246,0.14);
            color: #BFDBFE;
            font-weight: 800;
            margin-bottom: 0.6rem;
        }}
        .workflow-title {{
            color: {WHITE};
            font-weight: 700;
            margin-bottom: 0.35rem;
        }}
        .workflow-copy {{
            color: #CBD5E1;
            font-size: 0.95rem;
            line-height: 1.45;
        }}
        .status-pill {{
            display: inline-flex;
            align-items: center;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
            margin-top: 0.35rem;
        }}
        .status-safe {{
            color: #DCFCE7;
            background: rgba(34,197,94,0.15);
            border: 1px solid rgba(34,197,94,0.3);
        }}
        .status-risk {{
            color: #FECACA;
            background: rgba(239,68,68,0.15);
            border: 1px solid rgba(239,68,68,0.3);
        }}
        @media (max-width: 900px) {{
            .hero-grid {{
                grid-template-columns: 1fr;
            }}
            .hero-logo-panel {{
                justify-self: start;
                width: 180px;
            }}
            .hero-proof {{
                grid-template-columns: 1fr;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def make_mock_contract_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Item ID": "A100", "Item Description": "Latex Gloves Case Pack", "Product Category": "PPE", "Unit Price": 18.40},
            {"Item ID": "B205", "Item Description": "Surgical Masks Bulk Box", "Product Category": "PPE", "Unit Price": 14.25},
            {"Item ID": "C310", "Item Description": "Hand Sanitizer Refill", "Product Category": "Sanitation", "Unit Price": 28.75},
            {"Item ID": "D415", "Item Description": "Disinfecting Wipes Carton", "Product Category": "Sanitation", "Unit Price": 22.10},
            {"Item ID": "E520", "Item Description": "Thermometer Covers Pack", "Product Category": "Diagnostics", "Unit Price": 9.80},
            {"Item ID": "F625", "Item Description": "Sterile Drapes Surgical Set", "Product Category": "Surgical", "Unit Price": 41.60},
        ]
    )


def make_mock_invoice_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Invoice Line": 1, "Item ID": "A100", "Item Description": "Latex Gloves Case Pack", "Product Category": "PPE", "Quantity": 145, "Unit Price": 21.90},
            {"Invoice Line": 2, "Item ID": "B205", "Item Description": "Surgical Masks Bulk Box", "Product Category": "PPE", "Quantity": 210, "Unit Price": 17.85},
            {"Invoice Line": 3, "Item ID": "C310", "Item Description": "Hand Sanitizer Refill", "Product Category": "Sanitation", "Quantity": 96, "Unit Price": 33.40},
            {"Invoice Line": 4, "Item ID": "D415", "Item Description": "Disinfecting Wipes Carton", "Product Category": "Sanitation", "Quantity": 118, "Unit Price": 26.95},
            {"Invoice Line": 5, "Item ID": "E520", "Item Description": "Thermometer Covers Pack", "Product Category": "Diagnostics", "Quantity": 160, "Unit Price": 10.95},
            {"Invoice Line": 6, "Item ID": "F625", "Item Description": "Sterile Drapes Surgical Set", "Product Category": "Surgical", "Quantity": 74, "Unit Price": 49.80},
        ]
    )


def load_contract_csv_or_mock(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return make_mock_contract_data()
    return normalize_contract_data(pd.read_csv(uploaded_file))


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [str(col).strip() for col in normalized.columns]
    return normalized


def apply_column_aliases(df: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    normalized = normalize_columns(df)
    normalized_lookup = {str(col).strip().lower(): col for col in normalized.columns}
    rename_map = {}

    for canonical_name, candidate_names in aliases.items():
        if canonical_name in normalized.columns:
            continue
        for candidate in candidate_names:
            original_name = normalized_lookup.get(candidate.lower())
            if original_name:
                rename_map[original_name] = canonical_name
                break

    if rename_map:
        normalized = normalized.rename(columns=rename_map)
    return normalized


def normalize_contract_data(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "Item ID": ["item id", "itemid", "sku", "product id", "product code", "contract item id"],
        "Item Description": ["item description", "description", "product description", "item name"],
        "Product Category": ["product category", "category", "item category"],
        "Unit Price": ["unit price", "price", "contract price", "approved unit price"],
    }
    return apply_column_aliases(df, aliases)


def normalize_invoice_data(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "Invoice Line": ["invoice line", "line", "line number", "line no", "invoice line number"],
        "Item ID": ["item id", "itemid", "sku", "product id", "product code"],
        "Item Description": ["item description", "description", "product description", "item name"],
        "Product Category": ["product category", "category", "item category"],
        "Quantity": ["quantity", "qty", "ordered qty", "billed qty"],
        "Unit Price": ["unit price", "price", "invoice price", "billed unit price"],
    }
    normalized = apply_column_aliases(df, aliases)
    if "Invoice Line" not in normalized.columns:
        normalized["Invoice Line"] = range(1, len(normalized) + 1)
    return normalized


def read_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""


def read_image_text(file_bytes: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)
    except Exception:
        return ""


def parse_invoice_line_items(raw_text: str) -> pd.DataFrame:
    rows = []
    pattern = re.compile(
        r"(?P<item_id>[A-Z]\d{3,4})\s+"
        r"(?P<description>[A-Za-z][A-Za-z\s\-]+?)\s+"
        r"(?P<quantity>\d+)\s+"
        r"\$?(?P<unit_price>\d+(?:\.\d{1,2})?)"
    )
    category_map = {
        "Gloves": "PPE",
        "Masks": "PPE",
        "Sanitizer": "Sanitation",
        "Wipes": "Sanitation",
        "Covers": "Diagnostics",
        "Drapes": "Surgical",
    }

    for index, line in enumerate(raw_text.splitlines(), start=1):
        cleaned_line = " ".join(line.strip().split())
        match = pattern.search(cleaned_line)
        if not match:
            continue

        description = match.group("description").strip()
        category = "General"
        for keyword, mapped_category in category_map.items():
            if keyword.lower() in description.lower():
                category = mapped_category
                break

        rows.append(
            {
                "Invoice Line": index,
                "Item ID": match.group("item_id"),
                "Item Description": description,
                "Product Category": category,
                "Quantity": int(match.group("quantity")),
                "Unit Price": float(match.group("unit_price")),
            }
        )

    return pd.DataFrame(rows)


def extract_invoice_from_document(uploaded_invoice):
    if uploaded_invoice is None:
        return make_mock_invoice_data(), {
            "source_mode": "Demo Mode",
            "ocr_status": "No invoice uploaded. Mock OCR invoice generated.",
            "raw_text_preview": "Mock invoice dataset loaded to demonstrate the autonomous workflow.",
            "agent_status": "Recovery agent standing by with demo data.",
        }

    file_bytes = uploaded_invoice.getvalue()
    extension = Path(uploaded_invoice.name).suffix.lower()
    extracted_text = ""
    source_mode = "Structured OCR"

    if extension == ".csv":
        parsed_df = normalize_invoice_data(pd.read_csv(io.BytesIO(file_bytes)))
        return parsed_df, {
            "source_mode": "CSV Upload",
            "ocr_status": f"Structured invoice CSV loaded from {uploaded_invoice.name}.",
            "raw_text_preview": "CSV invoice loaded directly. OCR was not required for this upload.",
            "agent_status": "Recovery agent primed for variance detection and dispute orchestration.",
        }

    if extension == ".pdf":
        extracted_text = read_pdf_text(file_bytes)
    elif extension in {".png", ".jpg", ".jpeg"}:
        extracted_text = read_image_text(file_bytes)
    else:
        source_mode = "Unsupported file type"

    parsed_df = parse_invoice_line_items(extracted_text)

    if parsed_df.empty:
        parsed_df = make_mock_invoice_data()
        ocr_status = "OCR parser could not confidently extract line items. Demo invoice data loaded as fallback."
        source_mode = "Fallback Parser"
    else:
        parsed_df = normalize_invoice_data(parsed_df)
        ocr_status = f"OCR extracted {len(parsed_df)} invoice line item(s) from {uploaded_invoice.name}."

    return parsed_df, {
        "source_mode": source_mode,
        "ocr_status": ocr_status,
        "raw_text_preview": extracted_text[:1200] if extracted_text else "No extractable text returned by available local OCR/PDF parsers.",
        "agent_status": "Recovery agent primed for variance detection and dispute orchestration.",
    }


def audit_engine(contract_df: pd.DataFrame, invoice_df: pd.DataFrame, variance_tolerance_pct: float, vendor_name: str):
    contract = normalize_contract_data(contract_df)
    invoice = normalize_invoice_data(invoice_df)

    required_contract = {"Item ID", "Unit Price"}
    required_invoice = {"Item ID", "Unit Price"}

    missing_contract = required_contract - set(contract.columns)
    missing_invoice = required_invoice - set(invoice.columns)

    if missing_contract:
        raise ValueError(f"Master Contract Pricing is missing required columns: {', '.join(sorted(missing_contract))}")
    if missing_invoice:
        raise ValueError(f"Parsed invoice is missing required columns: {', '.join(sorted(missing_invoice))}")

    contract = contract.rename(columns={"Unit Price": "Contract Unit Price"})
    invoice = invoice.rename(columns={"Unit Price": "Invoice Unit Price"})

    if "Quantity" not in invoice.columns:
        invoice["Quantity"] = 1
    if "Item Description" not in invoice.columns:
        invoice["Item Description"] = "Unknown Item"
    if "Product Category" not in invoice.columns:
        invoice["Product Category"] = "General"
    if "Invoice Line" not in invoice.columns:
        invoice["Invoice Line"] = range(1, len(invoice) + 1)

    merged = invoice.merge(
        contract[[col for col in ["Item ID", "Contract Unit Price", "Product Category"] if col in contract.columns]],
        on="Item ID",
        how="left",
        suffixes=("", "_contract"),
    )

    if "Product Category_contract" in merged.columns:
        merged["Product Category"] = merged["Product Category"].fillna(merged["Product Category_contract"])
        merged = merged.drop(columns=["Product Category_contract"])

    merged["Vendor"] = vendor_name
    merged["Invoice Unit Price"] = pd.to_numeric(merged["Invoice Unit Price"], errors="coerce")
    merged["Contract Unit Price"] = pd.to_numeric(merged["Contract Unit Price"], errors="coerce")
    merged["Quantity"] = pd.to_numeric(merged["Quantity"], errors="coerce").fillna(1)
    merged["Price Difference"] = merged["Invoice Unit Price"] - merged["Contract Unit Price"]
    merged["Variance %"] = (
        (merged["Price Difference"] / merged["Contract Unit Price"])
        .where(merged["Contract Unit Price"] > 0)
        .fillna(0)
        * 100
    )
    merged["Overcharge Amount"] = merged["Price Difference"].clip(lower=0) * merged["Quantity"]
    merged["Flagged"] = merged["Variance %"] > variance_tolerance_pct
    merged["Contract Match Found"] = merged["Contract Unit Price"].notna()

    flagged = merged[merged["Flagged"]].copy()
    total_overcharge = float(flagged["Overcharge Amount"].sum()) if not flagged.empty else 0.0
    return merged, flagged, total_overcharge


def calculate_vendor_trust_score(vendor_name: str, current_overcharge: float, current_flagged_items: int) -> float:
    with get_connection() as conn:
        historical = pd.read_sql_query(
            "SELECT total_overcharge, items_flagged FROM audit_runs WHERE vendor_name = ?",
            conn,
            params=(vendor_name,),
        )

    historical_overcharge = float(historical["total_overcharge"].sum()) if not historical.empty else 0.0
    historical_flags = int(historical["items_flagged"].sum()) if not historical.empty else 0
    penalty = ((historical_overcharge + current_overcharge) / 25.0) + ((historical_flags + current_flagged_items) * 4)
    return max(0.0, round(100.0 - penalty, 1))


def build_dispute_email(vendor_name: str, vendor_email: str, flagged_items: int, total_overcharge: float) -> str:
    return f"""Subject: Request for Credit Memo - Pricing Variance Review

To: {vendor_email}

Dear {vendor_name} Billing Team,

Our automated audit agent completed a contract-to-invoice review and identified {flagged_items} billed line item(s) priced above the contracted rate.

The exact total overcharge identified is ${total_overcharge:,.2f}. Please issue a credit memo for this amount and confirm once the adjustment has been processed.

If helpful, we can provide the supporting discrepancy report showing the affected line items, contract pricing, invoice pricing, and variance calculations.

Thank you for your prompt review and resolution.

Best regards,
Vetti Financial Recovery Agent
"""


def deploy_recovery_workflow(vendor_name: str, vendor_email: str, flagged_df: pd.DataFrame, total_overcharge: float, tolerance_pct: float, trust_score: float):
    flagged_items = int(len(flagged_df))
    if flagged_items == 0:
        return {
            "gmail_status": "Not deployed. No disputed overcharges found.",
            "payment_hold_status": "No payment hold required.",
            "recovery_status": "Resolved automatically: no action needed.",
            "notes": "Audit closed without recovery actions.",
        }

    notes = {
        "flagged_item_ids": flagged_df["Item ID"].astype(str).tolist(),
        "dispute_amount": round(total_overcharge, 2),
        "tolerance_pct": tolerance_pct,
        "trust_score_at_deploy": trust_score,
        "gmail_agent_mode": "demo",
        "quickbooks_agent_mode": "demo",
        "vendor_name": vendor_name,
        "vendor_email": vendor_email,
    }
    return {
        "gmail_status": "Demo mode: dispute prepared and queued for Gmail delivery. Live send/monitor needs API credentials and network access.",
        "payment_hold_status": "Demo mode: payment hold recommended. Live QuickBooks hold placement needs API credentials and network access.",
        "recovery_status": "Awaiting vendor response / credit memo confirmation.",
        "notes": json.dumps(notes),
    }


def save_audit_run(
    audit_id: str,
    vendor_name: str,
    vendor_email: str,
    invoice_filename: str,
    items_scanned: int,
    items_flagged: int,
    total_overcharge: float,
    tolerance_pct: float,
    payment_hold_status: str,
    gmail_status: str,
    recovery_status: str,
    historical_vendor_trust_score: float,
    notes: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_runs (
                audit_id,
                created_at,
                vendor_name,
                vendor_email,
                invoice_filename,
                items_scanned,
                items_flagged,
                total_overcharge,
                tolerance_pct,
                payment_hold_status,
                gmail_status,
                recovery_status,
                historical_vendor_trust_score,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                datetime.utcnow().isoformat(timespec="seconds"),
                vendor_name,
                vendor_email,
                invoice_filename,
                items_scanned,
                items_flagged,
                total_overcharge,
                tolerance_pct,
                payment_hold_status,
                gmail_status,
                recovery_status,
                historical_vendor_trust_score,
                notes,
            ),
        )


def load_audit_history(vendor_name: str | None = None) -> pd.DataFrame:
    query = "SELECT * FROM audit_runs ORDER BY created_at DESC"
    params = ()
    if vendor_name:
        query = "SELECT * FROM audit_runs WHERE vendor_name = ? ORDER BY created_at DESC"
        params = (vendor_name,)
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def mark_latest_pending_resolved(vendor_name: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT audit_id
            FROM audit_runs
            WHERE vendor_name = ? AND recovery_status = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (vendor_name, "Awaiting vendor response / credit memo confirmation."),
        ).fetchone()

        if not row:
            return False

        conn.execute(
            """
            UPDATE audit_runs
            SET recovery_status = ?, gmail_status = ?, payment_hold_status = ?
            WHERE audit_id = ?
            """,
            (
                "Resolved: Credit memo received.",
                "Credit memo confirmation detected in demo mode.",
                "Payment hold released after recovery confirmation.",
                row[0],
            ),
        )
        return True


def calculate_recovery_progress() -> tuple[float, float, float]:
    with get_connection() as conn:
        history = pd.read_sql_query("SELECT total_overcharge, recovery_status FROM audit_runs", conn)

    if history.empty:
        return 0.0, 0.0, 0.0

    total_identified = float(history["total_overcharge"].sum())
    resolved = float(
        history.loc[history["recovery_status"].str.contains("Resolved", na=False), "total_overcharge"].sum()
    )
    progress_pct = (resolved / total_identified * 100.0) if total_identified > 0 else 0.0
    return round(progress_pct, 1), resolved, total_identified


def file_text_icon() -> str:
    return """
    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
      <path d="M14 2v6h6"></path>
      <path d="M16 13H8"></path>
      <path d="M16 17H8"></path>
      <path d="M10 9H8"></path>
    </svg>
    """


def zap_icon() -> str:
    return """
    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z"></path>
    </svg>
    """


def render_hero() -> None:
    logo_data_uri = ""
    if LOGO_PATH.exists():
        logo_data_uri = f"data:image/svg+xml;base64,{b64encode(LOGO_PATH.read_bytes()).decode('ascii')}"

    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="hero-grid">
                <div>
                    <div class="hero-kicker">Vendor Recovery Intelligence</div>
                    <div class="hero-title">Vetti</div>
                    <div class="hero-subheadline">The Autonomous Defense Layer for Your Bottom Line.</div>
                    <div class="hero-copy">
                        Finance teams use Vetti to catch invoice overcharges before money leaves the bank, centralize vendor risk, and push every pricing dispute through a clean recovery workflow that is easy to trust.
                    </div>
                    <div class="hero-proof">
                        <div class="hero-proof-card">
                            <div class="hero-proof-value">OCR to recovery</div>
                            <div class="hero-proof-label">One flow from intake, audit, dispute, and payment hold recommendation.</div>
                        </div>
                        <div class="hero-proof-card">
                            <div class="hero-proof-value">Persistent trust scores</div>
                            <div class="hero-proof-label">Track vendor behavior over time instead of judging invoices in isolation.</div>
                        </div>
                        <div class="hero-proof-card">
                            <div class="hero-proof-value">Small-team ready</div>
                            <div class="hero-proof-label">Built to help lean finance teams recover revenue without extra headcount.</div>
                        </div>
                    </div>
                </div>
                <div class="hero-logo-panel">
                    <img class="hero-logo-img" src="{logo_data_uri}" alt="Vetti logo" />
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_cards() -> None:
    st.markdown('<div class="dashboard-section-title">Why Teams Start Here</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    cards = [
        ("📥", "Intake", "Upload the contract once, then feed in PDF or image invoices. Vetti extracts the bill data and turns messy documents into structured audit-ready line items."),
        ("🧠", "Audit", "See what is overpriced, how far it exceeds tolerance, which categories are leaking margin, and whether the vendor is becoming riskier over time."),
        ("💸", "Recovery", "Send a dispute draft, document the hold decision, and keep a historical record of what was identified, escalated, and recovered."),
    ]
    for col, (icon, title, copy) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <div class="feature-title">{title}</div>
                    <div class="feature-copy">{copy}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_workflow_cards() -> None:
    st.markdown('<div class="dashboard-section-title">How Companies Use Vetti</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    steps = [
        ("1", "Collect", "Import the master contract and the vendor invoice so the system has both the approved rate and the billed rate."),
        ("2", "Validate", "Vetti normalizes the line items, checks every unit price, and applies the variance tolerance you define."),
        ("3", "Escalate", "Flagged discrepancies are grouped into one operator-friendly view with dispute language ready to send."),
        ("4", "Recover", "Teams track payment holds, credit memo responses, and historical vendor trust in one audit trail."),
    ]
    for col, (step, title, copy) in zip(cols, steps):
        with col:
            st.markdown(
                f"""
                <div class="workflow-card">
                    <div class="workflow-step">{step}</div>
                    <div class="workflow-title">{title}</div>
                    <div class="workflow-copy">{copy}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_value_snapshot(items_flagged: int, total_overcharge: float, trust_score: float, vendor_name: str) -> None:
    st.markdown('<div class="dashboard-section-title">What Matters Right Now</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    priority_text = "No active recovery priority. This invoice is within tolerance."
    if items_flagged > 0:
        priority_text = f"{vendor_name} has {items_flagged} flagged line item(s) requiring review before payment."
    snapshot_cards = [
        ("Highest Priority", priority_text),
        ("Financial Exposure", f"Potential overcharge exposure on the current audit is ${total_overcharge:,.2f}, creating an immediate recovery opportunity if challenged before payment."),
        ("Vendor Risk", f"Current trust score for {vendor_name} is {trust_score}. Lower scores indicate recurring pricing risk."),
    ]
    for col, (title, body) in zip(cols, snapshot_cards):
        with col:
            st.markdown(
                f"""
                <div class="workflow-card">
                    <div class="workflow-title">{title}</div>
                    <div class="workflow-copy">{body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def init_session_state() -> None:
    defaults = {
        "dashboard_started": False,
        "audit_requested": False,
        "current_page": "Dashboard",
        "dashboard_view": "Live Workspace",
        "user_profile": {
            "name": "Jack Cole",
            "title": "Founder & Finance Lead",
            "email": "jack.cole@vetti.example",
            "phone": "(555) 240-9012",
            "timezone": "America/New_York",
        },
        "company_profile": {
            "company_name": "Cole Supply Co.",
            "logo_path": str(LOGO_PATH),
            "billing_email": "finance@colesupply.example",
        },
        "team_members": [
            {"name": "Jack Cole", "email": "jack.cole@vetti.example", "role": "Admin"},
            {"name": "Maya Brooks", "email": "maya@vetti.example", "role": "Finance Ops"},
        ],
        "subscription": {
            "plan": "Pro Trial",
            "status": "Active",
            "renewal_date": "2026-05-19",
        },
        "vendor_directory": {},
        "last_agent_statuses": {
            "gmail": "Pending deploy.",
            "quickbooks": "Pending deploy.",
            "recovery": "Pending deploy.",
        },
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def sync_vendor_directory(vendor_name: str, vendor_email: str, trust_score: float) -> None:
    directory = dict(st.session_state.vendor_directory)
    existing = directory.get(
        vendor_name,
        {
            "vendor_name": vendor_name,
            "vendor_email": vendor_email,
            "contact_name": "Accounts Receivable Team",
            "trust_score": trust_score,
            "notes": "Auto-synced from dashboard activity.",
        },
    )
    existing["vendor_email"] = vendor_email
    existing["trust_score"] = trust_score
    directory[vendor_name] = existing
    st.session_state.vendor_directory = directory


def render_sidebar_footer() -> None:
    profile = st.session_state.user_profile
    initials = "".join(part[0] for part in profile["name"].split()[:2]).upper()
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
        <div class="glass-card" style="padding:0.9rem;">
            <div style="display:flex; align-items:center; gap:0.75rem;">
                <div style="width:42px; height:42px; border-radius:999px; display:flex; align-items:center; justify-content:center; font-weight:800; color:white; background:linear-gradient(135deg, {ELECTRIC_COBALT}, #2563EB);">
                    {initials}
                </div>
                <div>
                    <div style="font-weight:700; color:{WHITE};">{profile["name"]}</div>
                    <div style="font-size:0.85rem; color:#BFDBFE;">{profile["title"]}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Sign Out", use_container_width=True):
        st.session_state.dashboard_started = False
        st.session_state.current_page = "Dashboard"
        st.rerun()


def render_top_summary_card(label: str, value: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="top-summary-card">
            <div class="top-summary-label">{label}</div>
            <div class="top-summary-value">{value}</div>
            <div class="top-summary-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_topbar() -> str:
    st.markdown('<div class="dashboard-topbar">', unsafe_allow_html=True)
    left, right = st.columns([1.05, 0.95])
    with left:
        st.markdown("### Workspace")
    with right:
        dashboard_view = st.radio(
            "Dashboard View",
            ["Live Workspace", "Demo"],
            index=0 if st.session_state.dashboard_view == "Live Workspace" else 1,
            horizontal=True,
            label_visibility="collapsed",
        )
    st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.dashboard_view = dashboard_view
    return dashboard_view


def render_dashboard_page(contract_file, invoice_document, variance_tolerance: float, vendor_name: str, vendor_email: str, deploy_clicked: bool, resolve_clicked: bool) -> None:
    dashboard_view = render_dashboard_topbar()
    files_uploaded = contract_file is not None and invoice_document is not None
    using_demo = dashboard_view == "Demo"
    has_any_input = files_uploaded or using_demo

    if not has_any_input:
        render_hero()

        hero_cols = st.columns([1.2, 0.8])
        with hero_cols[0]:
            if st.button("Get Started", type="primary"):
                st.session_state.current_page = "Dashboard"
                st.rerun()
        with hero_cols[1]:
            progress_pct, recovered_amount, total_identified_amount = calculate_recovery_progress()
            render_top_summary_card(
                "Recovery Visibility",
                f"{progress_pct:.0f}%",
                f"Vetti has tracked ${total_identified_amount:,.0f} in exposure and ${recovered_amount:,.0f} in resolved recovery value across audit history.",
            )

        render_feature_cards()
    else:
        if using_demo:
            st.markdown(
                """
                <div class="demo-banner">
                    Demo Mode is active. You are viewing Vetti with preloaded contract and invoice data so the full audit and recovery workflow can be explored without uploading files.
                </div>
                """,
                unsafe_allow_html=True,
            )
        top_left, top_right = st.columns([1.15, 0.85])
        with top_left:
            st.markdown('<div class="dashboard-section-title">Live Audit Workspace</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="glass-card">
                    <div class="glass-card-title">Current Audit Context</div>
                    <div style="color:#D7E3F3; line-height:1.7;">
                        <div><b>Vendor:</b> {vendor_name}</div>
                        <div><b>Invoice Source:</b> {invoice_document.name if invoice_document is not None else ("Demo invoice dataset" if using_demo else "Not uploaded")}</div>
                        <div><b>Contract Source:</b> {contract_file.name if contract_file is not None else ("Demo contract dataset" if using_demo else "Not uploaded")}</div>
                        <div><b>Variance Tolerance:</b> {variance_tolerance}%</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with top_right:
            history_df = load_audit_history(vendor_name)
            resolved_count = int(history_df["recovery_status"].str.contains("Resolved", na=False).sum()) if not history_df.empty else 0
            render_top_summary_card(
                "Recovery Overview",
                f"{resolved_count}",
                "Resolved audits tied to this vendor. The dashboard below is focused on the current invoice and the next best action.",
            )

    if files_uploaded:
        st.success(f"Audit ready. Loaded `{contract_file.name}` and `{invoice_document.name}`.")
    elif using_demo:
        st.info("Demo Mode is supplying sample contract and invoice data for the audit experience.")
    elif contract_file is not None or invoice_document is not None:
        st.warning("Upload both a contract CSV and an invoice file to run the live audit.")
    else:
        st.info("Upload a contract CSV and an invoice file to run a live audit.")

    try:
        contract_df = make_mock_contract_data() if using_demo and contract_file is None else load_contract_csv_or_mock(contract_file)
        invoice_df, ocr_meta = extract_invoice_from_document(None if using_demo and invoice_document is None else invoice_document)
    except Exception as exc:
        st.error(f"Unable to load the source documents: {exc}")
        return

    try:
        audited_df, discrepancy_df, total_overcharge = audit_engine(contract_df, invoice_df, variance_tolerance, vendor_name)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Audit Engine failed: {exc}")
        return

    if resolve_clicked:
        if mark_latest_pending_resolved(vendor_name):
            st.success("Latest pending audit marked as resolved.")
        else:
            st.warning("No pending audit was available to resolve for this vendor.")

    items_scanned = int(len(invoice_df))
    items_flagged = int(len(discrepancy_df))
    vendor_trust_score = calculate_vendor_trust_score(vendor_name, total_overcharge, items_flagged)
    invoice_filename = invoice_document.name if invoice_document is not None else "mock_invoice_document"
    sync_vendor_directory(vendor_name, vendor_email, vendor_trust_score)

    st.markdown('<div class="metric-band">', unsafe_allow_html=True)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Items Scanned", f"{items_scanned}")
    metric_cols[1].metric("Items Flagged", f"{items_flagged}")
    metric_cols[2].metric("Total Overcharge", f"${total_overcharge:,.2f}")
    metric_cols[3].metric("Vendor Trust Score", f"{vendor_trust_score}")
    st.markdown("</div>", unsafe_allow_html=True)

    render_value_snapshot(items_flagged, total_overcharge, vendor_trust_score, vendor_name)

    control_col, summary_col = st.columns([1.05, 1.25])
    with control_col:
        status_markup = '<div class="status-pill status-safe">Audit Status: Clear</div>'
        if items_flagged != 0:
            status_markup = f'<div class="status-pill status-risk">Audit Status: {items_flagged} item(s) need recovery</div>'
        st.markdown(
            f"""
            <div class="glass-card">
                <div class="glass-card-title">Agent Controls</div>
                <div style="color:#D7E3F3; line-height:1.65;">
                    <div><b>Vendor:</b> {vendor_name}</div>
                    <div><b>Recovery email:</b> {vendor_email}</div>
                    <div><b>Tolerance threshold:</b> {variance_tolerance}%</div>
                    {status_markup}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with summary_col:
        st.markdown(
            f"""
            <div class="glass-card">
                <div class="glass-card-title">Autonomous Intake Summary</div>
                <div class="icon-row">{file_text_icon()}<span><b>OCR Status:</b> {ocr_meta['ocr_status']}</span></div>
                <div class="icon-row">{zap_icon()}<span><b>Agent Status:</b> {ocr_meta['agent_status']}</span></div>
                <div class="icon-row">{file_text_icon()}<span><b>Source Mode:</b> {ocr_meta['source_mode']}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="dashboard-section-title">Source Data</div>', unsafe_allow_html=True)
    with st.expander("View OCR and Raw Source Data"):
        st.subheader("OCR Text Preview")
        st.code(ocr_meta["raw_text_preview"], language="text")
        raw_left, raw_right = st.columns(2)
        with raw_left:
            st.subheader("Master Contract")
            st.dataframe(contract_df, use_container_width=True)
        with raw_right:
            st.subheader("Parsed Invoice Line Items")
            st.dataframe(invoice_df, use_container_width=True)

    st.markdown('<div class="dashboard-section-title">Discrepancy Analysis</div>', unsafe_allow_html=True)
    if discrepancy_df.empty:
        st.success("No flagged pricing variances exceed the tolerance threshold.")
    else:
        sunburst_df = discrepancy_df.copy()
        sunburst_df["Vendor"] = vendor_name
        sunburst_df["Product Category"] = sunburst_df["Product Category"].fillna("General")
        sunburst_df["Item Label"] = sunburst_df["Item ID"].astype(str) + " | " + sunburst_df["Item Description"].astype(str)

        sunburst = px.sunburst(
            sunburst_df,
            path=["Vendor", "Product Category", "Item Label"],
            values="Overcharge Amount",
            color="Overcharge Amount",
            color_continuous_scale="Magma",
            title="Overcharge Exposure by Vendor and Product Category",
        )
        sunburst.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": WHITE},
            margin=dict(l=10, r=10, t=55, b=10),
        )
        st.plotly_chart(sunburst, use_container_width=True)

        display_columns = [
            col
            for col in [
                "Invoice Line",
                "Vendor",
                "Item ID",
                "Item Description",
                "Product Category",
                "Quantity",
                "Contract Unit Price",
                "Invoice Unit Price",
                "Price Difference",
                "Variance %",
                "Overcharge Amount",
                "Contract Match Found",
            ]
            if col in discrepancy_df.columns or col == "Vendor"
        ]
        report_df = discrepancy_df.copy()
        report_df["Vendor"] = vendor_name
        styled_report = report_df[display_columns].style.format(
            {
                "Contract Unit Price": "${:,.2f}",
                "Invoice Unit Price": "${:,.2f}",
                "Price Difference": "${:,.2f}",
                "Variance %": "{:,.2f}%",
                "Overcharge Amount": "${:,.2f}",
            }
        )
        st.dataframe(styled_report, use_container_width=True)

    st.markdown('<div class="dashboard-section-title">Recovery Agent</div>', unsafe_allow_html=True)
    dispute_email = build_dispute_email(vendor_name, vendor_email, items_flagged, total_overcharge)
    st.text_area("Generated Dispute Email", value=dispute_email, height=240)

    if deploy_clicked:
        audit_id = str(uuid.uuid4())
        deployment = deploy_recovery_workflow(
            vendor_name=vendor_name,
            vendor_email=vendor_email,
            flagged_df=discrepancy_df,
            total_overcharge=total_overcharge,
            tolerance_pct=variance_tolerance,
            trust_score=vendor_trust_score,
        )
        save_audit_run(
            audit_id=audit_id,
            vendor_name=vendor_name,
            vendor_email=vendor_email,
            invoice_filename=invoice_filename,
            items_scanned=items_scanned,
            items_flagged=items_flagged,
            total_overcharge=total_overcharge,
            tolerance_pct=variance_tolerance,
            payment_hold_status=deployment["payment_hold_status"],
            gmail_status=deployment["gmail_status"],
            recovery_status=deployment["recovery_status"],
            historical_vendor_trust_score=vendor_trust_score,
            notes=deployment["notes"],
        )
        st.session_state.last_agent_statuses = {
            "gmail": deployment["gmail_status"],
            "quickbooks": deployment["payment_hold_status"],
            "recovery": deployment["recovery_status"],
        }
        st.success(f"Recovery agent deployed for audit {audit_id}. This run has been recorded in the local audit database.")

    action_cols = st.columns(3)
    titles = ["Gmail Agent", "QuickBooks Hold", "Recovery Status"]
    values = [
        st.session_state.last_agent_statuses["gmail"],
        st.session_state.last_agent_statuses["quickbooks"],
        st.session_state.last_agent_statuses["recovery"],
    ]
    for col, title, value in zip(action_cols, titles, values):
        with col:
            st.markdown(
                f"""
                <div class="glass-card">
                    <div class="glass-card-title">{title}</div>
                    <div style="color:#D7E3F3; line-height:1.5;">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.caption(
        "Live Gmail delivery, inbox monitoring, QuickBooks payment holds, and high-accuracy OCR still require external credentials, installed OCR dependencies, and network/API access. "
        "This version provides the branded operating surface, persistent history, and safe demo-mode orchestration locally."
    )


def render_vendor_directory_page() -> None:
    st.markdown('<div class="dashboard-section-title">Vendor Directory</div>', unsafe_allow_html=True)
    directory = st.session_state.vendor_directory
    if not directory:
        st.info("No vendors tracked yet. Open the Dashboard and run an audit to populate the directory automatically.")
        return

    vendor_df = pd.DataFrame(directory.values()).sort_values(by="trust_score", ascending=False)
    st.dataframe(vendor_df, use_container_width=True)

    vendor_options = vendor_df["vendor_name"].tolist()
    selected_vendor = st.selectbox("Manage Vendor", vendor_options)
    record = directory[selected_vendor]

    col1, col2 = st.columns(2)
    with col1:
        updated_email = st.text_input("Vendor Email", value=record["vendor_email"], key=f"vendor_email_{selected_vendor}")
        updated_contact = st.text_input("Contact Name", value=record["contact_name"], key=f"contact_name_{selected_vendor}")
    with col2:
        updated_score = st.slider("Trust Score Override", 0.0, 100.0, float(record["trust_score"]), 0.5, key=f"trust_score_{selected_vendor}")
        updated_notes = st.text_area("Notes", value=record["notes"], key=f"notes_{selected_vendor}")

    if st.button("Save Vendor Profile", key="save_vendor_profile"):
        directory[selected_vendor] = {
            "vendor_name": selected_vendor,
            "vendor_email": updated_email,
            "contact_name": updated_contact,
            "trust_score": updated_score,
            "notes": updated_notes,
        }
        st.session_state.vendor_directory = directory
        st.success(f"{selected_vendor} has been updated.")


def render_audit_history_page() -> None:
    st.markdown('<div class="dashboard-section-title">Audit History</div>', unsafe_allow_html=True)
    history_df = load_audit_history()
    if history_df.empty:
        st.info("No historical audits recorded yet. Deploy the recovery agent from the Dashboard to create the first persistent audit run.")
        return

    summary_cols = st.columns(3)
    summary_cols[0].metric("Total Audits", f"{len(history_df)}")
    summary_cols[1].metric("Historical Overcharge", f"${history_df['total_overcharge'].sum():,.2f}")
    resolved_count = int(history_df["recovery_status"].str.contains("Resolved", na=False).sum())
    summary_cols[2].metric("Resolved Audits", f"{resolved_count}")

    display_history = history_df[
        [
            "created_at",
            "vendor_name",
            "vendor_email",
            "invoice_filename",
            "items_scanned",
            "items_flagged",
            "total_overcharge",
            "payment_hold_status",
            "gmail_status",
            "recovery_status",
            "historical_vendor_trust_score",
        ]
    ].copy()
    display_history["total_overcharge"] = display_history["total_overcharge"].map(lambda value: f"${value:,.2f}")
    st.dataframe(display_history, use_container_width=True)


def render_settings_page() -> None:
    st.markdown('<div class="dashboard-section-title">Settings</div>', unsafe_allow_html=True)
    user_tab, company_tab, team_tab, subscription_tab = st.tabs(["User Profile", "Company Profile", "Team Management", "Subscription"])

    with user_tab:
        profile = st.session_state.user_profile
        profile["name"] = st.text_input("Full Name", value=profile["name"])
        profile["title"] = st.text_input("Job Title", value=profile["title"])
        profile["email"] = st.text_input("Email", value=profile["email"])
        profile["phone"] = st.text_input("Phone", value=profile["phone"])
        profile["timezone"] = st.selectbox("Timezone", ["America/New_York", "America/Chicago", "America/Los_Angeles"], index=["America/New_York", "America/Chicago", "America/Los_Angeles"].index(profile["timezone"]))
        st.session_state.user_profile = profile

    with company_tab:
        company = st.session_state.company_profile
        company["company_name"] = st.text_input("Company Name", value=company["company_name"])
        company["billing_email"] = st.text_input("Billing Email", value=company["billing_email"])
        uploaded_logo = st.file_uploader("Company Logo", type=["png", "jpg", "jpeg", "svg"], key="company_logo_uploader")
        if uploaded_logo is not None:
            company["logo_path"] = uploaded_logo.name
            st.success(f"Loaded logo: {uploaded_logo.name}")
        if company["logo_path"] and Path(company["logo_path"]).exists():
            st.image(company["logo_path"], width=120)
        else:
            st.caption(f"Current logo: {company['logo_path']}")
        st.session_state.company_profile = company

    with team_tab:
        team_df = pd.DataFrame(st.session_state.team_members)
        st.dataframe(team_df, use_container_width=True)
        invite_name = st.text_input("Coworker Name")
        invite_email = st.text_input("Coworker Email")
        invite_role = st.selectbox("Role", ["Finance Ops", "Admin", "Reviewer"])
        if st.button("Invite Coworker"):
            if invite_name and invite_email:
                st.session_state.team_members.append({"name": invite_name, "email": invite_email, "role": invite_role})
                st.success(f"Invitation prepared for {invite_name}.")
            else:
                st.warning("Enter both name and email to invite a coworker.")

    with subscription_tab:
        subscription = st.session_state.subscription
        st.markdown(
            f"""
            <div class="glass-card">
                <div class="glass-card-title">Subscription Status</div>
                <div style="color:#D7E3F3; line-height:1.8;">
                    <div><b>Plan:</b> {subscription["plan"]}</div>
                    <div><b>Status:</b> {subscription["status"]}</div>
                    <div><b>Renewal:</b> {subscription["renewal_date"]}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


init_db()
inject_global_styles()
init_session_state()
with st.sidebar:
    st.image(str(LOGO_PATH), width=72)
    st.markdown("### Workspace")
    selected_page = st.radio(
        "Navigation",
        ["Dashboard", "Vendor Directory", "Audit History", "Settings"],
        index=["Dashboard", "Vendor Directory", "Audit History", "Settings"].index(st.session_state.current_page),
        label_visibility="collapsed",
    )
    st.session_state.current_page = selected_page
    contract_file = None
    invoice_document = None
    variance_tolerance = 0
    vendor_name = "Acme Medical Supply"
    vendor_email = "billing@acmemedical.example"
    deploy_clicked = False
    resolve_clicked = False
    run_audit_clicked = False
    if st.session_state.current_page == "Dashboard":
        st.markdown("### Dashboard Controls")
        contract_file = st.file_uploader("Master Contract Pricing (CSV)", type="csv")
        invoice_document = st.file_uploader("Vendor Invoice (CSV / PDF / PNG / JPG)", type=["csv", "pdf", "png", "jpg", "jpeg"])
        variance_tolerance = st.slider("Variance Tolerance (%)", min_value=0, max_value=20, value=0, step=1)
        vendor_name = st.text_input("Vendor Name", value="Acme Medical Supply")
        vendor_email = st.text_input("Vendor Recovery Email", value="billing@acmemedical.example")
        run_audit_clicked = st.button("Run Audit", use_container_width=True)
        deploy_clicked = st.button("Deploy Recovery Agent", type="primary", use_container_width=True)
        resolve_clicked = st.button("Simulate Credit Memo Received", use_container_width=True)
        if run_audit_clicked:
            st.rerun()
        if contract_file is not None and invoice_document is not None:
            st.caption("Both files loaded. The audit will run automatically below.")
        else:
            st.caption("Upload both files for a live audit. Use the Demo tab in the top bar if you want to explore the product with sample data.")
    else:
        st.markdown("### Page Context")
        st.caption("Use the navigation menu to move across the Vetti workspace. Dashboard-specific audit controls appear when you return to Dashboard.")
    render_sidebar_footer()

if st.session_state.current_page == "Dashboard":
    render_dashboard_page(contract_file, invoice_document, variance_tolerance, vendor_name, vendor_email, deploy_clicked, resolve_clicked)
elif st.session_state.current_page == "Vendor Directory":
    render_vendor_directory_page()
elif st.session_state.current_page == "Audit History":
    render_audit_history_page()
else:
    render_settings_page()
