import streamlit as st
import pandas as pd

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(page_title="Dairy Farm Management", layout="wide")

# ============================================================
# GOOGLE SHEET IDS (from Streamlit Secrets)
# ============================================================
INVESTMENT_SHEET_ID = st.secrets["sheets"]["INVESTMENT_SHEET_ID"]
MILK_DIS_M_SHEET_ID = st.secrets["sheets"]["MILK_DIS_M_SHEET_ID"]
MILK_DIS_E_SHEET_ID = st.secrets["sheets"]["MILK_DIS_E_SHEET_ID"]
EXPENSE_SHEET_ID = st.secrets["sheets"]["EXPENSE_SHEET_ID"]
COW_LOG_SHEET_ID = st.secrets["sheets"]["COW_LOG_SHEET_ID"]
PAYMENT_SHEET_ID = st.secrets["sheets"]["PAYMENT_SHEET_ID"]
BILLING_SHEET_ID = st.secrets["sheets"]["BILLING_SHEET_ID"]

# ============================================================
# GOOGLE SHEET CSV EXPORT LINKS
# ============================================================
INVESTMENT_CSV_URL = f"https://docs.google.com/spreadsheets/d/{INVESTMENT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=investment"
MILK_DIS_M_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MILK_DIS_M_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=morning"
MILK_DIS_E_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MILK_DIS_E_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=evening"
EXPENSE_CSV_URL = f"https://docs.google.com/spreadsheets/d/{EXPENSE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=expense"
COW_LOG_CSV_URL = f"https://docs.google.com/spreadsheets/d/{COW_LOG_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=dailylog"
PAYMENT_CSV_URL = f"https://docs.google.com/spreadsheets/d/{PAYMENT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=payment"
BILLING_CSV_URL = f"https://docs.google.com/spreadsheets/d/{BILLING_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Bills"

# ============================================================
# UTILITY FUNCTIONS
# ============================================================
@st.cache_data(ttl=600)
def load_csv(url, drop_cols=None):
    """Load a CSV from Google Sheets"""
    try:
        df = pd.read_csv(url)
        if drop_cols:
            df = df.drop(columns=[col for col in drop_cols if col in df.columns])
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()


def sum_numeric_columns(df, exclude_cols=None):
    """Sum all numeric columns except excluded ones"""
    if df is None or df.empty:
        return 0
    if exclude_cols is None:
        exclude_cols = []
    numeric_cols = [col for col in df.columns if col not in exclude_cols]
    df_numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return df_numeric.sum().sum()


# -------------------- Missing-entry helpers --------------------
def normalize_date_col(df, candidates=("Date", "date")):
    """Find a date column, parse it to datetime and standardize name to 'Date'."""
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    for c in candidates:
        if c in df.columns:
            df = df.copy()
            df["Date"] = pd.to_datetime(df[c], errors="coerce")
            return df
    # fallback: if any column name contains 'date' case-insensitive
    for c in df.columns:
        if "date" in c.lower():
            df = df.copy()
            df["Date"] = pd.to_datetime(df[c], errors="coerce")
            return df
    return df  # no date column found; return unchanged


def detect_milk_col(df):
    """Return first column name that looks like milk (case-insensitive)."""
    if df is None or df.empty:
        return None
    for c in df.columns:
        if "milk" in c.lower() or "दूध" in c.lower():
            return c
    return None


def has_valid_milk_for_date(df, date, milk_col):
    """Return True if for given date df has at least one numeric milk value > 0."""
    if df is None or df.empty or milk_col is None:
        return False
    if "Date" not in df.columns:
        return False
    df_date = df[df["Date"].dt.normalize() == pd.Timestamp(date).normalize()]
    if df_date.empty:
        return False
    vals = pd.to_numeric(df_date[milk_col], errors="coerce")
    return (vals.fillna(0) > 0).any()


def has_valid_distribution_for_date(df, date):
    """
    Return True if for given date df has any numeric value > 0
    in non-Date / non-Timestamp columns.
    """
    if df is None or df.empty or "Date" not in df.columns:
        return False
    df_date = df[df["Date"].dt.normalize() == pd.Timestamp(date).normalize()]
    if df_date.empty:
        return False
    # drop Date / Timestamp-like columns then coerce numeric
    numeric_df = df_date.drop(columns=[c for c in df_date.columns if c.lower() in ("date", "timestamp")], errors="ignore")
    if numeric_df.empty:
        return False
    numeric_df = numeric_df.apply(lambda col: pd.to_numeric(col, errors="coerce"))
    row_sums = numeric_df.sum(axis=1, skipna=True).fillna(0)
    return (row_sums > 0).any()


def find_missing_dates_for_sheet(df, start_date, end_date, validator_fn):
    """
    Generic: expected dates from start_date..end_date (inclusive).
    validator_fn(df, date) should return True if the date has valid data.
    Returns sorted list of pd.Timestamp (dates) that are missing.
    """
    if pd.isna(start_date) or pd.isna(end_date) or end_date < start_date:
        return []
    expected = pd.date_range(start=start_date.normalize(), end=end_date.normalize(), freq="D")
    missing = []
    for d in expected:
        if not validator_fn(df, d):
            missing.append(pd.Timestamp(d))
    return missing


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "🏠 Dashboard",
        "Milking & Feeding",
        "Milk Distribution",
        "Expense",
        "Payments",
        "Billing",
        "Investments",
    ],
)

# ============================================================
# 🏠 DASHBOARD PAGE
# ============================================================
if page == "🏠 Dashboard":

    # -------------------- Custom Dark Mode CSS --------------------
    st.markdown(
        """
        <style>
        :root {
            --bg-color: #0e1117;
            --card-bg: #1a1d23;
            --text-color: #f0f2f6;
            --accent: #00FFFF;
            --border-color: #00FFFF44;
            --shadow-color: #00FFFF22;
        }
        @media (prefers-color-scheme: light) {
            :root {
                --bg-color: #f9f9f9;
                --card-bg: #ffffff;
                --text-color: #000000;
                --accent: #0077ff;
                --border-color: #0077ff33;
                --shadow-color: #0077ff11;
            }
        }
        .main { background-color: var(--bg-color); color: var(--text-color); }
        div[data-testid="stMetric"] {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 0 8px var(--shadow-color);
            text-align: center;
        }
        h1, h2, h3 { color: var(--accent); }
        hr { border: 1px solid var(--border-color); }
        label, .stRadio { color: var(--text-color) !important; }
        @media (max-width: 768px) {
            div[data-testid="stMetric"] { padding: 10px; font-size: 0.85rem; }
            h1, h2, h3 { font-size: 1rem; }
        }
        .radio-center { display: flex; justify-content: center; margin-top: 10px; margin-bottom: 25px; }
        div[data-testid="stRadio"] > div { justify-content: center !important; }
        div[data-testid="stRadio"] label { color: var(--text-color) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.header("🐄 Dairy Farm Dashboard")

    # -------------------- Load Data --------------------
    START_DATE = pd.Timestamp("2025-11-01")
    df_cow_log = load_csv(COW_LOG_CSV_URL, drop_cols=["Timestamp"])
    df_expense = load_csv(EXPENSE_CSV_URL, drop_cols=["Timestamp"])
    df_milk_m = load_csv(MILK_DIS_M_CSV_URL, drop_cols=["Timestamp"])
    df_milk_e = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])
    df_payment_received = load_csv(PAYMENT_CSV_URL, drop_cols=["Timestamp"])
    df_investment = load_csv(INVESTMENT_CSV_URL, drop_cols=["Timestamp"])

    # -------------------- Filter from START_DATE (apply filters to variables correctly) --------------------
    def filter_from_start(df, start):
        if df is None or df.empty or "Date" not in df.columns:
            return df if df is not None else pd.DataFrame()
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        return df[df["Date"] >= start]

    df_cow_log = filter_from_start(df_cow_log, START_DATE)
    df_expense = filter_from_start(df_expense, START_DATE)
    df_milk_m = filter_from_start(df_milk_m, START_DATE)
    df_milk_e = filter_from_start(df_milk_e, START_DATE)
    df_payment_received = filter_from_start(df_payment_received, START_DATE)
    df_investment = filter_from_start(df_investment, START_DATE)

    # -------------------- Normalize Date columns for missing-checks --------------------
    df_cow_log = normalize_date_col(df_cow_log)
    df_milk_m = normalize_date_col(df_milk_m)
    df_milk_e = normalize_date_col(df_milk_e)

    # warn if sheets missing date column
    if df_cow_log is None or "Date" not in df_cow_log.columns:
        st.warning("Cow log sheet does not contain a recognized Date column — missing-entry detection will mark all dates as missing.")
    if df_milk_m is None or "Date" not in df_milk_m.columns:
        st.warning("Morning distribution sheet does not contain a recognized Date column — missing-entry detection will mark all dates as missing.")
    if df_milk_e is None or "Date" not in df_milk_e.columns:
        st.warning("Evening distribution sheet does not contain a recognized Date column — missing-entry detection will mark all dates as missing.")

    # -------------------- Lifetime Summary --------------------
    st.subheader("📊 Overall Summary")

    milk_col = detect_milk_col(df_cow_log)
    total_milk_produced = pd.to_numeric(df_cow_log[milk_col], errors="coerce").sum() if milk_col and not (df_cow_log is None or df_cow_log.empty) else 0

    total_milk_m = sum_numeric_columns(df_milk_m, exclude_cols=["Timestamp", "Date"])
    total_milk_e = sum_numeric_columns(df_milk_e, exclude_cols=["Timestamp", "Date"])
    total_milk_distributed = total_milk_m + total_milk_e
    remaining_milk = total_milk_produced - total_milk_distributed

    total_expense = pd.to_numeric(df_expense["Amount"], errors="coerce").sum() if not df_expense.empty else 0
    total_payment_received = pd.to_numeric(df_payment_received["Amount"], errors="coerce").sum() if not df_payment_received.empty else 0
    total_investment = pd.to_numeric(df_investment["Amount"], errors="coerce").sum() if not df_investment.empty else 0

    investment_bipin = (
        df_investment.loc[df_investment["Paid To"] == "Bipin Kumar", "Amount"].sum()
        if "Paid To" in df_investment.columns
        else 0
    )
    received_bipin = (
        df_payment_received.loc[df_payment_received["Received By"] == "Bipin Kumar", "Amount"].sum()
        if "Received By" in df_payment_received.columns
        else 0
    )
    expense_bipin = (
        df_expense.loc[df_expense["Expense By"] == "Bipin Kumar", "Amount"].sum()
        if "Expense By" in df_expense.columns
        else 0
    )
    fund_bipin = investment_bipin + received_bipin - expense_bipin

    # -------------------- Metrics --------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🥛 Total Milk Produced", f"{total_milk_produced:.2f} L")
    c2.metric("🚚 Total Milk Distributed", f"{total_milk_distributed:.2f} L")
    c3.metric("❗ Remaining / Lost Milk", f"{remaining_milk:.2f} L")
    c4.metric("💸 Total Expense", f"₹{total_expense:,.2f}")

    c5, c6, c7 = st.columns(3)
    c5.metric("💰 Total Payment Received", f"₹{total_payment_received:,.2f}")
    c6.metric("📈 Total Investment", f"₹{total_investment:,.2f}")
    c7.metric("🏦 Fund (Bipin Kumar)", f"₹{fund_bipin:,.2f}")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # -------------------- Latest Summary --------------------
    st.subheader("🕒 Latest Summary")
    
    # --- Find last 2 milk produced records ---
    if df_cow_log is None or df_cow_log.empty or "Date" not in df_cow_log.columns:
        df_sorted_prod = pd.DataFrame()
    else:
        df_sorted_prod = df_cow_log.sort_values("Date", ascending=False).head(2)

    def get_shift_total(row):
        shift = row["Shift - पहर"] if "Shift - पहर" in row else row.get("Shift", "")
        milk_value = row[milk_col] if milk_col in row else 0
        milk_value = pd.to_numeric(milk_value, errors="coerce")
        return shift, milk_value

    latest_prod_1 = None
    latest_prod_2 = None
    if not df_sorted_prod.empty and len(df_sorted_prod) >= 1:
        latest_prod_1 = df_sorted_prod.iloc[0]
    if not df_sorted_prod.empty and len(df_sorted_prod) >= 2:
        latest_prod_2 = df_sorted_prod.iloc[1]

    # safe defaults
    if latest_prod_1 is None:
        p1_date = ""
        p1_shift = ""
        p1_total = 0
    else:
        shift1, milk1 = get_shift_total(latest_prod_1)
        p1_shift, p1_total = (shift1, milk1 if pd.notna(milk1) else 0)
        p1_date = latest_prod_1["Date"].strftime("%d-%m-%Y") if pd.notna(latest_prod_1["Date"]) else ""

    if latest_prod_2 is None:
        p2_date = ""
        p2_shift = ""
        p2_total = 0
    else:
        shift2, milk2 = get_shift_total(latest_prod_2)
        p2_shift, p2_total = (shift2, milk2 if pd.notna(milk2) else 0)
        p2_date = latest_prod_2["Date"].strftime("%d-%m-%Y") if pd.notna(latest_prod_2["Date"]) else ""

    # --- Determine which distribution file to pick ---
    def get_latest_delivery(shift):
        if not isinstance(shift, str):
            shift = str(shift) if pd.notna(shift) else ""
        shift_lower = shift.lower() if shift else ""
        target_df = df_milk_m if "morning" in shift_lower else df_milk_e
        if target_df is None or target_df.empty or "Date" not in target_df.columns:
            return None, shift, 0

        df_sorted = target_df.sort_values("Date", ascending=False)
        if df_sorted.empty:
            return None, shift, 0

        row = df_sorted.iloc[0]

        # Convert all columns except "Date" to numeric and sum
        numeric = row.drop(labels=["Date"], errors="ignore").apply(pd.to_numeric, errors="coerce")
        total = numeric.fillna(0).sum()

        date = row["Date"].strftime("%d-%m-%Y") if pd.notna(row["Date"]) else ""
        return date, shift, total

    # Case based assignment:
    # If latest produced shift is Morning → order: P(M), D(M), P(E), D(E)
    # If Evening → order: P(E), D(E), P(M), D(M)
    is_morning_first = isinstance(p1_shift, str) and p1_shift.lower() == "morning"

    if is_morning_first:
        p1_date, p1_shift, p1_total = p1_date, p1_shift, p1_total
        d1_date, d1_shift, d1_total = get_latest_delivery("morning")
        p2_date, p2_shift, p2_total = p2_date, p2_shift, p2_total
        d2_date, d2_shift, d2_total = get_latest_delivery("evening")
    else:
        p1_date, p1_shift, p1_total = p1_date, p1_shift, p1_total
        d1_date, d1_shift, d1_total = get_latest_delivery("evening")
        p2_date, p2_shift, p2_total = p2_date, p2_shift, p2_total
        d2_date, d2_shift, d2_total = get_latest_delivery("morning")

    # --- Layout: 4 Metric Blocks in ONE ROW ---
    lc1, lc2, lc3, lc4 = st.columns(4)

    lc1.metric(f"🥛 Last Milk Produced ({p1_shift})", f"{p1_total} L", p1_date)
    lc2.metric(f"🚚 Last Milk Delivered ({d1_shift})", f"{d1_total} L", d1_date)

    lc3.metric(f"🥛 Previous Milk Produced ({p2_shift})", f"{p2_total} L", p2_date)
    lc4.metric(f"🚚 Previous Milk Delivered ({d2_shift})", f"{d2_total} L", d2_date)

    st.markdown("<hr/>", unsafe_allow_html=True)

    # -------------------- Missing Entries UI --------------------
    # compute missing dates (today as end)
    today_for_missing = pd.Timestamp.today()

    missing_cow_dates = find_missing_dates_for_sheet(
        df_cow_log, START_DATE, today_for_missing, lambda df, d: has_valid_milk_for_date(df, d, milk_col)
    )

    missing_morning_dates = find_missing_dates_for_sheet(
        df_milk_m, START_DATE, today_for_missing, lambda df, d: has_valid_distribution_for_date(df, d)
    )

    missing_evening_dates = find_missing_dates_for_sheet(
        df_milk_e, START_DATE, today_for_missing, lambda df, d: has_valid_distribution_for_date(df, d)
    )

    st.subheader("⚠️ Missing Entries (from 01-11-2025)")

    m1, m2, m3 = st.columns(3)
    m1.metric("Milking missing", f"{len(missing_cow_dates)} days")
    m2.metric("Morning dist missing", f"{len(missing_morning_dates)} days")
    m3.metric("Evening dist missing", f"{len(missing_evening_dates)} days")

    st.markdown("")  # small spacer

    # Build compact table for most recent missing dates (show latest first)
    rows = []
    for d in sorted(missing_cow_dates, reverse=True)[:10]:
        rows.append({"Date": d.strftime("%d-%m-%Y"), "Type": "Milking"})
    for d in sorted(missing_morning_dates, reverse=True)[:10]:
        rows.append({"Date": d.strftime("%d-%m-%Y"), "Type": "Morning Dist"})
    for d in sorted(missing_evening_dates, reverse=True)[:10]:
        rows.append({"Date": d.strftime("%d-%m-%Y"), "Type": "Evening Dist"})

    if rows:
        df_missing_display = pd.DataFrame(rows).sort_values(["Date", "Type"], ascending=[False, True])
        st.dataframe(df_missing_display, use_container_width=True)
        if st.checkbox("Show all missing dates"):
            st.write("### All missing Milking dates")
            st.write([d.strftime("%d-%m-%Y") for d in missing_cow_dates])
            st.write("### All missing Morning Distribution dates")
            st.write([d.strftime("%d-%m-%Y") for d in missing_morning_dates])
            st.write("### All missing Evening Distribution dates")
            st.write([d.strftime("%d-%m-%Y") for d in missing_evening_dates])
    else:
        st.info("No missing entries detected between 01-11-2025 and today.")

    st.markdown("<hr/>", unsafe_allow_html=True)


    # -------------------- Current Month Summary --------------------
    today = pd.Timestamp.today()
    current_month_name = today.strftime("%B %Y")
    st.subheader(f"📅 Current Month Summary ({current_month_name})")

    def filter_month(df):
        if df is None or df.empty or "Date" not in df.columns:
            return df if df is not None else pd.DataFrame()
        return df[df["Date"].dt.month == today.month]

    df_month_expense = filter_month(df_expense)
    df_month_milk_m = filter_month(df_milk_m)
    df_month_milk_e = filter_month(df_milk_e)
    df_month_cow_log = filter_month(df_cow_log)
    df_month_payment = filter_month(df_payment_received)

    milk_col = detect_milk_col(df_month_cow_log)
    milk_month = pd.to_numeric(df_month_cow_log[milk_col], errors="coerce").sum() if milk_col and not (df_month_cow_log is None or df_month_cow_log.empty) else 0
    milk_m_month = sum_numeric_columns(df_month_milk_m, exclude_cols=["Timestamp", "Date"])
    milk_e_month = sum_numeric_columns(df_month_milk_e, exclude_cols=["Timestamp", "Date"])
    milk_distributed_month = milk_m_month + milk_e_month
    remaining_milk_month = milk_month - milk_distributed_month

    expense_month = pd.to_numeric(df_month_expense["Amount"], errors="coerce").sum() if not df_month_expense.empty else 0
    payment_month = pd.to_numeric(df_month_payment["Amount"], errors="coerce").sum() if not df_month_payment.empty else 0

    cm1, cm2, cm3, cm4, cm5 = st.columns(5)
    cm1.metric("🥛 Milk Produced (This Month)", f"{milk_month:.2f} L")
    cm2.metric("🚚 Milk Distributed (This Month)", f"{milk_distributed_month:.2f} L")
    cm3.metric("❗ Remaining Milk (This Month)", f"{remaining_milk_month:.2f} L")
    cm4.metric("💸 Expense (This Month)", f"₹{expense_month:,.2f}")
    cm5.metric("💰 Payment Received (This Month)", f"₹{payment_month:,.2f}")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # -------------------- Milk Production vs Delivery Graph --------------------
    st.subheader("📈 Milk Production vs Delivery Trend")
    
    # --- Centered Radio Button for Date Range
    col1, col2, col3 = st.columns([1, 3, 1])  # Center alignment
    with col2:
        range_option = st.radio(
            "",
            ["1 Week", "1 Month", "3 Months", "6 Months", "1 Year", "3 Years", "5 Years", "Max"],
            horizontal=True,
            index=2,  # Default to "3 Months"
        )
    
    # --- Determine date range based on selection
    today = pd.Timestamp.today()
    date_limit = {
        "1 Week": today - pd.Timedelta(weeks=1),
        "1 Month": today - pd.DateOffset(months=1),
        "3 Months": today - pd.DateOffset(months=3),
        "6 Months": today - pd.DateOffset(months=6),
        "1 Year": today - pd.DateOffset(years=1),
        "3 Years": today - pd.DateOffset(years=3),
        "5 Years": today - pd.DateOffset(years=5),
        "Max": START_DATE,
    }[range_option]
    
    # --- Prepare production data
    if not (df_cow_log is None) and not df_cow_log.empty and milk_col:
        # ensure Date column is datetime
        df_cow_log["Date"] = pd.to_datetime(df_cow_log["Date"], errors="coerce")
        df_cow_log = df_cow_log[df_cow_log["Date"] >= date_limit]
        daily_prod = df_cow_log.groupby("Date")[milk_col].sum().reset_index()
    else:
        daily_prod = pd.DataFrame(columns=["Date", "Produced"])
    
    # --- Combine morning & evening distribution
    def combine_distribution(df1, df2):
        df_all = pd.concat([df1, df2])
        if df_all is None or df_all.empty or "Date" not in df_all.columns:
            return pd.DataFrame(columns=["Date", "Total"])
        df_all = df_all.copy()
        df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")
        # coerce non-date columns to numeric and sum per row
        numeric_cols = [c for c in df_all.columns if c.lower() not in ("date", "timestamp")]
        for c in numeric_cols:
            df_all[c] = pd.to_numeric(df_all[c], errors="coerce").fillna(0)
        df_all["Total"] = df_all[numeric_cols].sum(axis=1)
        return df_all.groupby("Date")["Total"].sum().reset_index()
    
    df_delivery = combine_distribution(df_milk_m, df_milk_e)
    if not df_delivery.empty:
        df_delivery = df_delivery[df_delivery["Date"] >= date_limit]
    
    # --- Display line chart
    if not daily_prod.empty and not df_delivery.empty:
        chart_df = pd.merge(daily_prod, df_delivery, on="Date", how="outer").fillna(0)
        chart_df = chart_df.rename(columns={milk_col: "Produced", "Total": "Delivered"})
        # ensure index is Date
        chart_df = chart_df.sort_values("Date")
        chart_df = chart_df.set_index("Date")
        st.line_chart(chart_df)
    else:
        st.info("No sufficient data for chart.")

# ----------------------------
# MILKING & FEEDING PAGE
# ----------------------------
elif page == "Milking & Feeding":
    st.title("🐄 Milking & Feeding Analysis")

    # layout placeholder (no quick-form button)
    col1, col2 = st.columns([6, 1])
    with col2:
        st.write("")  # intentionally left blank (button removed)
    
        # ─────────────────────────────────────────────────────

    # --- Load data ---
    df = load_csv(COW_LOG_CSV_URL, drop_cols=["Timestamp"])
    df_morning = load_csv(MILK_DIS_M_CSV_URL, drop_cols=["Timestamp"])
    df_evening = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])

    # --- Date setup ---
    start_date = pd.Timestamp("2025-11-01")
    now = pd.Timestamp.now()
    this_month = now.month
    this_year = now.year

    # --- Clean and filter helper ---
    def clean_and_filter(df):
        if df is None or df.empty or "Date" not in df.columns:
            return df if df is not None else pd.DataFrame()
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"] >= start_date]
        df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")
        return df

    df = clean_and_filter(df)
    df_morning = clean_and_filter(df_morning)
    df_evening = clean_and_filter(df_evening)

    # --- Detect milk column dynamically ---
    milk_col = None
    for c in df.columns:
        if "milk" in c.lower() or "दूध" in c:
            milk_col = c
            break

    # --- Ensure numeric ---
    if not df.empty and milk_col:
        df[milk_col] = pd.to_numeric(df[milk_col], errors="coerce")

    # --- Total milk produced ---
    total_milk_produced = df[milk_col].sum() if not df.empty and milk_col else 0

    # --- Total milk this month ---
    total_milk_month = 0
    if not df.empty and milk_col:
        df["Date_dt"] = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce")
        df_this_month = df[
            (df["Date_dt"].dt.month == this_month) & (df["Date_dt"].dt.year == this_year)
        ]
        if not df_this_month.empty:
            total_milk_month = df_this_month[milk_col].sum()

    # --- Cow-wise total ---
    cow_wise = pd.DataFrame()
    if not df.empty and "CowID" in df.columns and milk_col:
        cow_wise = (
            df.groupby("CowID")[milk_col]
            .sum()
            .reset_index()
            .rename(columns={milk_col: "Total Milk (L)"})
            .sort_values("Total Milk (L)", ascending=False)
        )

    # --- Total Milk Distributed ---
    def total_milk_distributed(df):
        if df is None or df.empty:
            return 0
        numeric_cols = [c for c in df.columns if c not in ["Timestamp", "Date"]]
        df_numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return df_numeric.sum().sum()

    total_distributed_morning = total_milk_distributed(df_morning)
    total_distributed_evening = total_milk_distributed(df_evening)
    total_distributed = total_distributed_morning + total_distributed_evening

    # --- KPIs ---
    st.subheader("📊 Key Metrics (From 1 Nov 2025)")
    col1, col2, col3 = st.columns(3)
    col1.metric("🥛 Total Milk Produced", f"{total_milk_produced:.2f} L")
    col2.metric("📅 Milk Produced This Month", f"{total_milk_month:.2f} L")
    col3.metric("🚚 Total Milk Delivered", f"{total_distributed:.2f} L")

    # --- Cow-wise production ---
    st.divider()
    st.subheader("🐮 Cow-wise Milk Production (From 1 Nov 2025)")
    if not cow_wise.empty:
        st.dataframe(cow_wise, use_container_width=True)
    else:
        st.info("No cow-wise milking data available yet.")

    # --- Daily trend ---
    st.divider()
    st.subheader("📅 Daily Milk Production Trend")
    if not df.empty and milk_col:
        df_daily = df.copy()
        df_daily["Date_dt"] = pd.to_datetime(df_daily["Date"], format="%d-%m-%Y", errors="coerce")
        daily_summary = (
            df_daily.groupby("Date_dt")[milk_col].sum().reset_index().sort_values("Date_dt")
        )
        st.line_chart(daily_summary.set_index("Date_dt"))
    else:
        st.info("No daily milking data to display.")

    # --- Raw data ---
    st.divider()
    st.subheader("📋 Raw Milking & Feeding Data (From 1 Nov 2025)")
    if not df.empty:
        df_display = df.sort_values(by="Date", ascending=False)
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No milking & feeding data available after 1 Nov 2025.")


# ----------------------------
# MILK DISTRIBUTION PAGE
# ----------------------------
elif page == "Milk Distribution":
    st.title("🥛 Milk Distribution")

    # --- Load data ---
    df_morning = load_csv(MILK_DIS_M_CSV_URL, drop_cols=["Timestamp"])
    df_evening = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])
    df_cow_log = load_csv(COW_LOG_CSV_URL, drop_cols=["Timestamp"])

    # --- Date filtering: only include records from 1 Nov 2025 onward ---
    start_date = pd.Timestamp("2025-11-01")

    def clean_and_filter(df):
        if df is None or df.empty or "Date" not in df.columns:
            return df if df is not None else pd.DataFrame()
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"] >= start_date]  # Filter only from 1 Nov 2025
        df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")  # Format date
        return df

    df_morning = clean_and_filter(df_morning)
    df_evening = clean_and_filter(df_evening)

    # --- Total milk distributed (sum numeric columns except date) ---
    def total_milk_distributed(df):
        if df is None or df.empty:
            return 0
        numeric_cols = [c for c in df.columns if c not in ["Timestamp", "Date"]]
        df_numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return df_numeric.sum().sum()

    total_morning = total_milk_distributed(df_morning)
    total_evening = total_milk_distributed(df_evening)
    total_distributed = total_morning + total_evening

    # --- Monthly totals ---
    this_month = pd.Timestamp.now().month
    this_year = pd.Timestamp.now().year

    def monthly_distribution(df):
        if df is None or df.empty or "Date" not in df.columns:
            return 0
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce")
        df_this_month = df[
            (df["Date"].dt.month == this_month) & (df["Date"].dt.year == this_year)
        ]
        return total_milk_distributed(df_this_month)

    monthly_morning = monthly_distribution(df_morning)
    monthly_evening = monthly_distribution(df_evening)
    monthly_distributed = monthly_morning + monthly_evening

    # --- Total milk produced this month from cow log (filter from 1 Nov 2025) ---
    total_milk_produced_month = 0
    if not (df_cow_log is None) and not df_cow_log.empty:
        df_cow_log.columns = [c.strip().lower() for c in df_cow_log.columns]
        if "date" in df_cow_log.columns and "milking -दूध" in df_cow_log.columns:
            df_cow_log["date"] = pd.to_datetime(df_cow_log["date"], errors="coerce")
            df_cow_log = df_cow_log[df_cow_log["date"] >= start_date]  # Filter Nov 1 onward
            df_cow_log["month"] = df_cow_log["date"].dt.month
            df_cow_log["year"] = df_cow_log["date"].dt.year
            df_month = df_cow_log[
                (df_cow_log["month"] == this_month) & (df_cow_log["year"] == this_year)
            ]
            total_milk_produced_month = pd.to_numeric(
                df_month["milking -दूध"], errors="coerce"
            ).sum()

    remaining_milk = total_milk_produced_month - monthly_distributed

    # --- KPI Metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric("🥛 Total Milk Distributed (from 1 Nov 2025)", f"{total_distributed:.2f} L")
    col2.metric("📅 This Month's Distribution", f"{monthly_distributed:.2f} L")
    col3.metric("🧾 Remaining Milk (This Month)", f"{remaining_milk:.2f} L")

    st.divider()

    # Morning Distribution placeholder (button removed)
    col1, col2 = st.columns([6, 1])
    with col1:
        st.subheader("🌅 Morning Distribution")
    with col2:
        st.write("")  # morning distribution quick-button removed
    
    if not (df_morning is None) and not df_morning.empty:
        df_morning_display = df_morning.sort_values("Date", ascending=False)
        st.dataframe(df_morning_display, use_container_width=True)
    else:
        st.info("No morning distribution data available after 1 Nov 2025.")

    # Evening Distribution placeholder (button removed)
    col1, col2 = st.columns([6, 1])
    with col1:
        st.subheader("🌇 Evening Distribution")
    with col2:
        st.write("")  # evening distribution quick-button removed

    if not (df_evening is None) and not df_evening.empty:
        df_evening_display = df_evening.sort_values("Date", ascending=False)
        st.dataframe(df_evening_display, use_container_width=True)
    else:
        st.info("No evening distribution data available after 1 Nov 2025.")

    # --- Trend Chart ---
    st.divider()
    st.subheader("📈 Daily Milk Distribution Trend (from 1 Nov 2025)")

    if not (df_morning is None) or not (df_evening is None):
        df_morning_chart = df_morning.copy() if not (df_morning is None) and not df_morning.empty else pd.DataFrame()
        df_evening_chart = df_evening.copy() if not (df_evening is None) and not df_evening.empty else pd.DataFrame()

        for df_temp in [df_morning_chart, df_evening_chart]:
            if df_temp is None or df_temp.empty:
                continue
            df_temp["Date"] = pd.to_datetime(df_temp["Date"], format="%d-%m-%Y", errors="coerce")
            numeric_cols = [c for c in df_temp.columns if c.lower() not in ("date", "timestamp")]
            for c in numeric_cols:
                df_temp[c] = pd.to_numeric(df_temp[c], errors="coerce").fillna(0)
            df_temp["Total"] = df_temp[numeric_cols].sum(axis=1)

        pieces = []
        if not (df_morning_chart is None) and not df_morning_chart.empty:
            pieces.append(df_morning_chart[["Date", "Total"]])
        if not (df_evening_chart is None) and not df_evening_chart.empty:
            pieces.append(df_evening_chart[["Date", "Total"]])

        if pieces:
            df_chart = pd.concat(pieces)
            df_chart = df_chart.groupby("Date")["Total"].sum().reset_index().sort_values("Date")
            st.line_chart(df_chart.set_index("Date"))
        else:
            st.info("No distribution data available to plot.")
    else:
        st.info("No distribution data available to plot.")


# ----------------------------
# EXPENSE, PAYMENTS, INVESTMENTS (unchanged)
# ----------------------------
elif page == "Expense":
    st.title("💸 Expense Tracker")

    # Add Expense  Button
    col1, col2 = st.columns([6, 1])
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/1hCkiBgU8sQKw87S8" target="_blank">'
            f'<button style="background-color:#C62828; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Add Expense</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────

    df_expense = load_csv(EXPENSE_CSV_URL, drop_cols=["Timestamp"])

    if not df_expense.empty:
        # --- Convert Date column properly ---
        if "Date" in df_expense.columns:
            df_expense["Date"] = pd.to_datetime(df_expense["Date"], errors="coerce")
            df_expense = df_expense.sort_values("Date", ascending=False)

        # --- Total Expense ---
        total_expense = df_expense["Amount"].sum()

        # --- Current Month Expense ---
        current_month = pd.Timestamp.now().month
        current_year = pd.Timestamp.now().year
        df_this_month = df_expense[
            (df_expense["Date"].dt.month == current_month)
            & (df_expense["Date"].dt.year == current_year)
        ]
        monthly_expense = df_this_month["Amount"].sum()

        # --- KPIs ---
        col1, col2 = st.columns(2)
        col1.metric("💰 Total Expense", f"₹{total_expense:,.2f}")
        col2.metric("📅 This Month's Expense", f"₹{monthly_expense:,.2f}")

        st.divider()

        # --- Expense by Type ---
        if "Expense Type" in df_expense.columns:
            expense_by_type = (
                df_expense.groupby("Expense Type")["Amount"].sum().sort_values(ascending=False)
            )
            st.subheader("📊 Expense by Type")
            st.bar_chart(expense_by_type)

        # --- Expense by Person ---
        if "Expense By" in df_expense.columns:
            expense_by_person = (
                df_expense.groupby("Expense By")["Amount"].sum().sort_values(ascending=False)
            )
            st.subheader("👤 Expense by Person")
            st.bar_chart(expense_by_person)

        st.divider()
        st.subheader("🧾 Detailed Expense Records")
        st.dataframe(df_expense, use_container_width=True)

    else:
        st.info("No expense records found.")


elif page == "Payments":
    st.title("💰 Payments Record")
    # Add Payment  Button
    col1, col2 = st.columns([6, 1])
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/jjaWGAUeTKkkoabX6" target="_blank">'
            f'<button style="background-color:#9C27B0; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Add Payment</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────
    
    df_payment = load_csv(PAYMENT_CSV_URL, drop_cols=["Timestamp"])
    st.dataframe(df_payment, use_container_width=True if not df_payment.empty else False)


# ----------------------------
# BILLING PAGE 
# ----------------------------
elif page == "Billing":
    import calendar
    from datetime import timedelta
    from io import BytesIO

    st.title("🧾 Billing")

    # ---------------- Config ----------------
    FIXED_RATE_PER_L = 60.0  # ₹60 per litre (hard-coded)

    # ---------------- Load data ----------------
    df_morning = load_csv(MILK_DIS_M_CSV_URL, drop_cols=["Timestamp"])
    df_evening = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])
    df_payments = load_csv(PAYMENT_CSV_URL, drop_cols=["Timestamp"])

    # try load existing billing sheet (optional; may be empty)
    BILLING_CSV_URL = None
    try:
        BILLING_SHEET_ID = st.secrets["sheets"].get("BILLING_SHEET_ID")
        if BILLING_SHEET_ID:
            BILLING_CSV_URL = f"https://docs.google.com/spreadsheets/d/{BILLING_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Bills"
    except Exception:
        BILLING_CSV_URL = None

    df_bills_existing = load_csv(BILLING_CSV_URL, drop_cols=None) if BILLING_CSV_URL else pd.DataFrame()

    # ---------------- normalize date cols helper ----------------
    def ensure_date_col(df):
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            return df
        for c in df.columns:
            if "date" in c.lower():
                df["Date"] = pd.to_datetime(df[c], errors="coerce")
                return df
        return df

    df_morning = ensure_date_col(df_morning)
    df_evening = ensure_date_col(df_evening)
    df_payments = ensure_date_col(df_payments)
    df_bills_existing = ensure_date_col(df_bills_existing) if not df_bills_existing.empty else pd.DataFrame()

    # ---------------- name normalization ----------------
    def norm_name(x):
        if pd.isna(x):
            return ""
        return " ".join(str(x).strip().lower().split())

    # ---------------- customers list ----------------
    def customers_from_sheets(dfm, dfe, dfp):
        cols_m = [c for c in dfm.columns if c.lower() not in ("date", "timestamp")] if dfm is not None else []
        cols_e = [c for c in dfe.columns if c.lower() not in ("date", "timestamp")] if dfe is not None else []
        cols_p = []
        if dfp is not None and not dfp.empty:
            name_col = next((c for c in dfp.columns if c.lower() in ("name","customer","received by","receivedby")), None)
            if name_col:
                cols_p = dfp[name_col].dropna().astype(str).unique().tolist()
        custs = sorted(set(cols_m) | set(cols_e) | set(cols_p))
        custs = [c for c in custs if str(c).strip() != ""]
        return ["All customers"] + custs

    customers = customers_from_sheets(df_morning, df_evening, df_payments)

    # ---------------- UI: select customer + period ----------------
    st.subheader("Generate invoices")
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        start_date = st.date_input("Start date", value=pd.Timestamp.today().replace(day=1).date())
    with col2:
        end_date = st.date_input("End date", value=pd.Timestamp.today().date())
    with col3:
        rate_l = st.number_input("Rate (₹/L)", value=float(FIXED_RATE_PER_L), step=1.0)
    st.markdown("---")
    cust_choice = st.selectbox("Choose Customer", options=customers, index=0)

    # ---------------- Calendar builder (updated dark palette) ----------------
    def build_delivery_calendar_html(df_morn, df_even, cust_raw, start_ts, end_ts):
        if df_morn is None:
            df_morn = pd.DataFrame()
        if df_even is None:
            df_even = pd.DataFrame()

        for df in (df_morn, df_even):
            if df is not None and not df.empty and "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        day_map = {}
        days = pd.date_range(start=start_ts, end=end_ts, freq="D")
        for d in days:
            m_val = 0.0
            e_val = 0.0
            if cust_raw == "All customers":
                if not (df_morn is None) and not df_morn.empty and "Date" in df_morn.columns:
                    mask = df_morn["Date"].dt.normalize() == d.normalize()
                    if mask.any():
                        cols = [c for c in df_morn.columns if c.lower() not in ("date","timestamp")]
                        if cols:
                            m_val = pd.to_numeric(df_morn.loc[mask, cols], errors="coerce").fillna(0).sum().sum()
                if not (df_even is None) and not df_even.empty and "Date" in df_even.columns:
                    mask = df_even["Date"].dt.normalize() == d.normalize()
                    if mask.any():
                        cols = [c for c in df_even.columns if c.lower() not in ("date","timestamp")]
                        if cols:
                            e_val = pd.to_numeric(df_even.loc[mask, cols], errors="coerce").fillna(0).sum().sum()
            else:
                if not (df_morn is None) and not df_morn.empty and cust_raw in df_morn.columns:
                    mask = df_morn["Date"].dt.normalize() == d.normalize()
                    if mask.any():
                        m_val = pd.to_numeric(df_morn.loc[mask, cust_raw], errors="coerce").fillna(0).sum()
                if not (df_even is None) and not df_even.empty and cust_raw in df_even.columns:
                    mask = df_even["Date"].dt.normalize() == d.normalize()
                    if mask.any():
                        e_val = pd.to_numeric(df_even.loc[mask, cust_raw], errors="coerce").fillna(0).sum()
            day_map[d.date()] = (float(m_val), float(e_val))

        start_d = start_ts.date()
        end_d = end_ts.date()
        start_monday = start_d - timedelta(days=start_d.weekday())
        end_sunday = end_d + timedelta(days=(6 - end_d.weekday()))

        css = """
        <style>
          .cal-wrap { font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; max-width:980px; }
          .cal-legend { display:flex; gap:18px; margin-bottom:10px; align-items:center; flex-wrap:wrap; }
          .legend-item { display:flex; gap:8px; align-items:center; font-size:0.95rem; color:#e6eef2; }
          .legend-swatch { width:18px; height:18px; border-radius:4px; border:1px solid rgba(255,255,255,0.08); }
          .cal-table { border-collapse: collapse; width:100%; }
          .cal-table th { padding:10px; text-align:center; color: #bcd3da; font-size:0.95rem; background: transparent; }
          .cal-table td { width:14.28%; vertical-align:top; border:1px solid rgba(255,255,255,0.04); padding:10px; min-height:86px; }
          .day-num { font-weight:700; font-size:0.98rem; margin-bottom:6px; display:block; }
          .mval, .eval { font-size:0.88rem; display:block; margin-top:4px; }
          .white-cell { background: #e8f5e9; color:#062018; }   /* both shifts */
          .yellow-cell { background: #FFD54F; color:#1b1700; }  /* only morning */
          .pink-cell { background: #FF80AB; color:#2b0018; }    /* only evening */
          .red-cell { background: #EF9A9A; color:#2b0000; }     /* no shift */
          .muted { color:#6f7a80; font-size:0.92rem; background:transparent; }
          .today { box-shadow: inset 0 0 0 2px rgba(0,255,255,0.12); border-radius:6px; }
          .cal-table td span { line-height:1.2; }
        </style>
        """

        html = '<div class="cal-wrap">' + css
        html += '<div class="cal-legend">'
        html += '<div class="legend-item"><div class="legend-swatch" style="background:#e8f5e9;border:1px solid rgba(0,0,0,0.06)"></div><div>Both shifts delivered</div></div>'
        html += '<div class="legend-item"><div class="legend-swatch" style="background:#FFD54F"></div><div>No evening (only morning)</div></div>'
        html += '<div class="legend-item"><div class="legend-swatch" style="background:#FF80AB"></div><div>No morning (only evening)</div></div>'
        html += '<div class="legend-item"><div class="legend-swatch" style="background:#EF9A9A"></div><div>No shift delivery</div></div>'
        html += '</div>'

        html += '<table class="cal-table"><thead><tr>'
        for wd in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:
            html += f'<th>{wd}</th>'
        html += '</tr></thead><tbody>'

        cur = start_monday
        while cur <= end_sunday:
            html += '<tr>'
            for i in range(7):
                cell_date = cur
                if cell_date < start_d or cell_date > end_d:
                    html += f'<td class="muted"><span class="day-num">{cell_date.day}</span></td>'
                else:
                    mval, eval_ = day_map.get(cell_date, (0.0,0.0))
                    morning_ok = mval > 0
                    evening_ok = eval_ > 0
                    if morning_ok and evening_ok:
                        cls = "white-cell"
                    elif morning_ok and not evening_ok:
                        cls = "yellow-cell"
                    elif not morning_ok and evening_ok:
                        cls = "pink-cell"
                    else:
                        cls = "red-cell"
                    today_cls = " today" if cell_date == pd.Timestamp.today().date() else ""
                    html += f'<td class="{cls}{today_cls}"><span class="day-num">{cell_date.day}</span>'
                    html += f'<span class="mval">M: {mval:.2f} L</span>'
                    html += f'<span class="eval">E: {eval_:.2f} L</span>'
                    html += '</td>'
                cur = cur + timedelta(days=1)
            html += '</tr>'
        html += '</tbody></table></div>'
        return html

    # ---------------- generate button ----------------
    if st.button("View billing for selection"):
        start_ts = pd.to_datetime(pd.Timestamp(start_date).normalize())
        end_ts = pd.to_datetime(pd.Timestamp(end_date).normalize())

        # ---------------- helpers for totals ----------------
        def total_delivered_for_customer(df_morn, df_even, cust, start, end):
            total = 0.0
            if df_morn is not None and not df_morn.empty and cust in df_morn.columns:
                mask = (df_morn["Date"] >= start) & (df_morn["Date"] <= end)
                total += pd.to_numeric(df_morn.loc[mask, cust], errors="coerce").fillna(0).sum()
            if df_even is not None and not df_even.empty and cust in df_even.columns:
                mask = (df_even["Date"] >= start) & (df_even["Date"] <= end)
                total += pd.to_numeric(df_even.loc[mask, cust], errors="coerce").fillna(0).sum()
            return float(total)

        def payments_for_customer_in_period(pay_df, cust_raw, start, end):
            if pay_df is None or pay_df.empty:
                return 0.0, pd.DataFrame()
            name_col = next((c for c in pay_df.columns if c.lower() in ("name","customer","received by","receivedby")), None)
            amount_col = next((c for c in pay_df.columns if "amount" in c.lower()), None)
            if amount_col is None:
                return 0.0, pd.DataFrame()
            dfp = pay_df.copy()
            dfp["Name_norm"] = dfp[name_col].apply(norm_name) if name_col else ""
            dfp["Amt_num"] = pd.to_numeric(dfp[amount_col], errors="coerce").fillna(0.0)
            dfp["Date_dt"] = pd.to_datetime(dfp["Date"], errors="coerce") if "Date" in dfp.columns else pd.NaT
            mask = (dfp["Date_dt"] >= start) & (dfp["Date_dt"] <= end)
            dfp_period = dfp[mask].copy()
            if cust_raw == "All customers":
                total_pay = dfp_period["Amt_num"].sum()
            else:
                total_pay = dfp_period.loc[dfp_period["Name_norm"] == norm_name(cust_raw), "Amt_num"].sum()
            return float(total_pay), dfp_period

        def current_outstanding_from_bills(bills_df, cust_raw):
            if bills_df is None or bills_df.empty:
                return 0.0, pd.DataFrame()
            dfb = bills_df.copy()
            if "CustomerName" not in dfb.columns:
                name_col = next((c for c in dfb.columns if "customer" in c.lower()), None)
                if name_col:
                    dfb["CustomerName"] = dfb[name_col]
                else:
                    return 0.0, pd.DataFrame()
            dfb["Customer_norm"] = dfb["CustomerName"].apply(norm_name)
            if "AmountBilled" in dfb.columns:
                dfb["AmountBilled_num"] = pd.to_numeric(dfb["AmountBilled"], errors="coerce").fillna(0.0)
            else:
                dfb["AmountBilled_num"] = 0.0
            if "PaymentsApplied" in dfb.columns:
                dfb["PaymentsApplied_num"] = pd.to_numeric(dfb["PaymentsApplied"], errors="coerce").fillna(0.0)
            else:
                dfb["PaymentsApplied_num"] = 0.0
            if "Balance" in dfb.columns:
                dfb["Balance_num"] = pd.to_numeric(dfb["Balance"], errors="coerce").fillna(dfb["AmountBilled_num"] - dfb["PaymentsApplied_num"])
            else:
                dfb["Balance_num"] = dfb["AmountBilled_num"] - dfb["PaymentsApplied_num"]

            if cust_raw == "All customers":
                tot = dfb["Balance_num"].sum()
                subset = dfb
            else:
                tot = dfb.loc[dfb["Customer_norm"] == norm_name(cust_raw), "Balance_num"].sum()
                subset = dfb.loc[dfb["Customer_norm"] == norm_name(cust_raw)].copy()
            return float(tot), subset

        # ---------------- Compute quick figures & invoice preview ----------------
        if cust_choice == "All customers":
            custs_list = [c for c in ( [c for c in df_morning.columns if c.lower() not in ("date","timestamp")] + [c for c in df_evening.columns if c.lower() not in ("date","timestamp")]) if str(c).strip() != ""]
            custs_list = sorted(set(custs_list))
            generated_total = 0.0
            for c in custs_list:
                generated_total += round(total_delivered_for_customer(df_morning, df_evening, c, start_ts, end_ts) * float(rate_l), 2)
            payments_period_total, payments_df_period = payments_for_customer_in_period(df_payments, "All customers", start_ts, end_ts)
            current_outstanding_total, _ = current_outstanding_from_bills(df_bills_existing, "All customers")
            quick_due_estimate = round(current_outstanding_total + generated_total - payments_period_total, 2)
            st.metric("Quick Due Estimate (All customers)", f"₹{quick_due_estimate:,.2f}")
            st.write(f"- Current outstanding from existing Bills sheet: ₹{current_outstanding_total:,.2f}")
            st.write(f"- Generated billing amount (period): ₹{generated_total:,.2f}")
            st.write(f"- Payments already received in period: ₹{payments_period_total:,.2f}")

            # show calendar for All customers
            calendar_html = build_delivery_calendar_html(df_morning, df_evening, "All customers", start_ts, end_ts)
            st.markdown(calendar_html, unsafe_allow_html=True)

        else:
            total_l = total_delivered_for_customer(df_morning, df_evening, cust_choice, start_ts, end_ts)
            generated_amount = round(total_l * float(rate_l), 2)
            payments_period, payments_df_period = payments_for_customer_in_period(df_payments, cust_choice, start_ts, end_ts)
            current_outstanding, bills_subset = current_outstanding_from_bills(df_bills_existing, cust_choice)
            quick_due_estimate = round(current_outstanding + generated_amount - payments_period, 2)

            # show top summary to the user (quick estimate BEFORE detailed calc)
            st.subheader(f"Quick Due Estimate for: {cust_choice}")
            colA, colB, colC, colD = st.columns(4)
            colA.metric("Current outstanding", f"₹{current_outstanding:,.2f}")
            colB.metric("Generated (this period)", f"₹{generated_amount:,.2f}")
            colC.metric("Payments in period", f"₹{payments_period:,.2f}")
            colD.metric("Quick Due Estimate", f"₹{quick_due_estimate:,.2f}")

            st.markdown("**Notes:** Quick Due Estimate = Current outstanding + Generated amount − Payments in period.")
            if not bills_subset.empty:
                st.caption("Recent existing bills for this customer (from Billing sheet):")
                st.dataframe(bills_subset.sort_values(by="EndDate", ascending=False).head(10), use_container_width=True)

            # ---------------- Generate and show detailed invoice row for verification ----------------
            st.subheader("Detailed invoice preview (for verification)")
            billid = f"INV-{start_ts.strftime('%Y%m%d')}-{end_ts.strftime('%Y%m%d')}-{str(cust_choice).replace(' ','_')}"
            invoice_row = {
                "BillID": billid,
                "CustomerName": cust_choice,
                "StartDate": start_ts.date(),
                "EndDate": end_ts.date(),
                "CreatedDate": pd.Timestamp.now(),
                "DueDate": (end_ts + pd.Timedelta(days=7)).date(),
                "TotalMilkLitres": round(total_l, 3),
                "RatePerL": float(rate_l),
                "MilkCharge": round(total_l * float(rate_l), 2),
                "AmountBilled": round(total_l * float(rate_l), 2),
                "PaymentsApplied": 0.0,
                "Balance": round(total_l * float(rate_l), 2),
                "Status": "DUE",
                "Notes": ""
            }
            df_invoice_preview = pd.DataFrame([invoice_row])
            st.dataframe(df_invoice_preview, use_container_width=True)

            # ---------------- show calendar for selected customer ----------------
            calendar_html = build_delivery_calendar_html(df_morning, df_evening, cust_choice, start_ts, end_ts)
            st.markdown(calendar_html, unsafe_allow_html=True)

    else:
        st.info("Choose a customer and period, then click 'View billing for selection'.")





elif page == "Investments":
    st.title("📈 Investment Log")
    # Add Investment  Button
    col1, col2 = st.columns([6, 1])
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/usPuRopj64DuxVpJA" target="_blank">'
            f'<button style="background-color:#2E7D32; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Add Investment</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────
    df_invest = load_csv(INVESTMENT_CSV_URL, drop_cols=["Timestamp"])
    st.dataframe(df_invest, use_container_width=True if not df_invest.empty else False)

# ----------------------------
# REFRESH BUTTON
# ----------------------------
if st.sidebar.button("🔁 Refresh"):
    st.rerun()
