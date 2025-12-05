# streamlit_dairy_billing.py
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date

st.set_page_config(page_title="Dairy Farm Management ", layout="wide")

# --- Google Sheets config (use your existing secrets) ---
INVESTMENT_SHEET_ID = st.secrets["sheets"]["INVESTMENT_SHEET_ID"]
MILK_DIS_M_SHEET_ID = st.secrets["sheets"]["MILK_DIS_M_SHEET_ID"]
MILK_DIS_E_SHEET_ID = st.secrets["sheets"]["MILK_DIS_E_SHEET_ID"]
EXPENSE_SHEET_ID = st.secrets["sheets"]["EXPENSE_SHEET_ID"]
COW_LOG_SHEET_ID = st.secrets["sheets"]["COW_LOG_SHEET_ID"]
PAYMENT_SHEET_ID = st.secrets["sheets"]["PAYMENT_SHEET_ID"]

INVESTMENT_SHEET_NAME = "investment"
INVESTMENT_CSV_URL = f"https://docs.google.com/spreadsheets/d/{INVESTMENT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={INVESTMENT_SHEET_NAME}"

MILK_DIS_M_SHEET_NAME = "morning"
MILK_DIS_M_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MILK_DIS_M_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={MILK_DIS_M_SHEET_NAME}"

MILK_DIS_E_SHEET_NAME = "evening"
MILK_DIS_E_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MILK_DIS_E_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={MILK_DIS_E_SHEET_NAME}"

EXPENSE_SHEET_NAME = "expense"
EXPENSE_CSV_URL = f"https://docs.google.com/spreadsheets/d/{EXPENSE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={EXPENSE_SHEET_NAME}"

COW_LOG_SHEET_NAME = "dailylog"
COW_LOG_CSV_URL = f"https://docs.google.com/spreadsheets/d/{COW_LOG_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={COW_LOG_SHEET_NAME}"

PAYMENT_SHEET_NAME = "payment"
PAYMENT_CSV_URL = f"https://docs.google.com/spreadsheets/d/{PAYMENT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={PAYMENT_SHEET_NAME}"


@st.cache_data(ttl=600)
def load_csv(url, drop_cols=None):
    try:
        df = pd.read_csv(url)
        if drop_cols:
            df = df.drop(columns=[col for col in drop_cols if col in df.columns])
        return df
    except Exception as e:
        # return empty df (caller will handle)
        return pd.DataFrame()


def normalize_milk_df(df, default_shift_label):
    """
    Normalize incoming milk sheet into columns:
      - customer_id (or customer), date, litres (float)
    Accepts many common column names.
    """
    if df.empty:
        return df

    df = df.copy()
    # Normalize column names to lowercase for detection
    cols = {c: c.lower() for c in df.columns}
    df.columns = [cols[c] for c in df.columns]

    # find customer column
    cust_col = None
    for candidate in ['customer_id', 'customer', 'cust_id', 'cust', 'id']:
        if candidate in df.columns:
            cust_col = candidate
            break
    if not cust_col:
        # fallback: first column
        cust_col = df.columns[0]

    # find date column
    date_col = None
    for candidate in ['date', 'day', 'timestamp', 'ts']:
        if candidate in df.columns:
            date_col = candidate
            break
    if not date_col:
        # try to detect any column containing 'date' in name
        for c in df.columns:
            if 'date' in c:
                date_col = c
                break
    if not date_col:
        # fallback: second column if exists
        date_col = df.columns[1] if len(df.columns) > 1 else None

    # find litres column
    litres_col = None
    for candidate in ['litres', 'liters', 'qty', 'quantity', 'milk']:
        if candidate in df.columns:
            litres_col = candidate
            break
    if not litres_col:
        # fallback: any numeric column other than date
        for c in df.columns:
            if c not in [cust_col, date_col] and pd.api.types.is_numeric_dtype(df[c]):
                litres_col = c
                break

    if litres_col is None:
        # no numeric column -> create litres as 0
        df['litres'] = 0.0
        litres_col = 'litres'

    # keep only relevant cols
    df = df[[cust_col, date_col, litres_col]].rename(columns={
        cust_col: 'customer_id',
        date_col: 'date',
        litres_col: 'litres'
    })

    # parse dates
    def safe_parse(d):
        try:
            return pd.to_datetime(d).date()
        except Exception:
            try:
                return parse_date(str(d)).date()
            except Exception:
                return None

    df['date'] = df['date'].apply(safe_parse)
    df = df.dropna(subset=['date'])
    # normalize customer_id to string
    df['customer_id'] = df['customer_id'].astype(str)
    # numeric litres
    df['litres'] = pd.to_numeric(df['litres'], errors='coerce').fillna(0.0)
    df['shift'] = default_shift_label
    return df


def load_and_merge_morning_evening():
    df_m = load_csv(MILK_DIS_M_CSV_URL, drop_cols=["Timestamp"])
    df_e = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])
    df_m_n = normalize_milk_df(df_m, 'M') if not df_m.empty else pd.DataFrame(columns=['customer_id','date','litres','shift'])
    df_e_n = normalize_milk_df(df_e, 'E') if not df_e.empty else pd.DataFrame(columns=['customer_id','date','litres','shift'])
    merged = pd.concat([df_m_n, df_e_n], ignore_index=True, sort=False)
    if merged.empty:
        return merged
    # group duplicates (if multiple entries exist for same cust/date/shift, sum)
    merged = merged.groupby(['customer_id','date','shift'], as_index=False).agg({'litres':'sum'})
    return merged


def load_payments():
    df_p = load_csv(PAYMENT_CSV_URL, drop_cols=["Timestamp"])
    if df_p.empty:
        return df_p
    # try to find customer and amount
    df = df_p.copy()
    cols = {c: c.lower() for c in df.columns}
    df.columns = [cols[c] for c in df.columns]
    cust_col = None
    for candidate in ['customer_id', 'customer', 'cust_id', 'cust']:
        if candidate in df.columns:
            cust_col = candidate
            break
    if not cust_col:
        cust_col = df.columns[0]
    amt_col = None
    for candidate in ['amount', 'amt', 'payment', 'paid']:
        if candidate in df.columns:
            amt_col = candidate
            break
    if not amt_col:
        # pick numeric column
        for c in df.columns:
            if c != cust_col and pd.api.types.is_numeric_dtype(df[c]):
                amt_col = c
                break
    date_col = None
    for candidate in ['date', 'payment_date', 'timestamp', 'ts']:
        if candidate in df.columns:
            date_col = candidate
            break

    if amt_col is None:
        # no amount column -> drop
        return pd.DataFrame()

    df = df[[cust_col, amt_col] + ([date_col] if date_col else [])]
    df = df.rename(columns={cust_col: 'customer_id', amt_col: 'amount'})
    if date_col:
        df = df.rename(columns={date_col: 'date'})
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    else:
        df['date'] = None
    df['customer_id'] = df['customer_id'].astype(str)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    return df


def compute_cycle_for_customer(merged_shifts, payments, customer_id, cycle_start_date, cycle_length_days=30, price_per_litre=45.0):
    """
    merged_shifts: dataframe with customer_id,date,shift,litres
    payments: dataframe with customer_id,amount,date (date nullable)
    cycle_start_date: date object
    returns dict with cycle summary and day-level data
    """
    cycle_start = cycle_start_date
    cycle_end = cycle_start + timedelta(days=cycle_length_days - 1)
    # build date range
    dates = [cycle_start + timedelta(days=i) for i in range(cycle_length_days)]
    # filter shifts for customer in cycle
    df_c = merged_shifts[merged_shifts['customer_id'] == str(customer_id)]
    # pivot to have M and E in columns
    if df_c.empty:
        pivot = pd.DataFrame({'date': dates})
    else:
        pivot = df_c.pivot_table(index='date', columns='shift', values='litres', aggfunc='sum').reset_index()
        pivot = pivot.rename_axis(None, axis=1)
        # ensure date col is datetime.date
    pivot['date'] = pd.to_datetime(pivot['date']).dt.date
    # ensure all cycle dates exist
    pivot_all = pd.DataFrame({'date': dates})
    pivot_all = pivot_all.merge(pivot, on='date', how='left')
    pivot_all['M'] = pivot_all.get('M', 0).fillna(0.0)
    pivot_all['E'] = pivot_all.get('E', 0).fillna(0.0)
    pivot_all['total'] = pivot_all['M'] + pivot_all['E']

    total_litres = float(pivot_all['total'].sum())
    # default pricing per day -> simple multiply (if you want per-day price, extend this)
    amount = total_litres * price_per_litre

    # payments for this customer within or before cycle_end considered early/within cycle
    df_pay = payments[payments['customer_id'] == str(customer_id)].copy() if not payments.empty else pd.DataFrame(columns=['customer_id','amount','date'])
    # treat payments with date <= cycle_end as early payments
    if 'date' in df_pay.columns:
        df_pay['date'] = pd.to_datetime(df_pay['date']).dt.date
        early_payments = df_pay[(df_pay['date'].notna()) & (df_pay['date'] <= cycle_end)]['amount'].sum()
    else:
        early_payments = df_pay['amount'].sum() if not df_pay.empty else 0.0

    final_payable = amount - early_payments
    credit = 0.0
    if final_payable < 0:
        credit = -final_payable
        final_payable = 0.0

    # day status used for calendar coloring
    def day_status(row):
        m = row['M']
        e = row['E']
        if (m == 0) and (e == 0):
            return 'both_missing'  # red (customer skipped)
        elif (m == 0) and (e > 0):
            return 'M_missing'     # pink
        elif (m > 0) and (e == 0):
            return 'E_missing'     # orange
        else:
            return 'both_present'  # white

    pivot_all['status'] = pivot_all.apply(day_status, axis=1)
    result = {
        'cycle_start': cycle_start,
        'cycle_end': cycle_end,
        'total_litres': total_litres,
        'amount': amount,
        'early_payments': early_payments,
        'final_payable': final_payable,
        'credit': credit,
        'days': pivot_all
    }
    return result


# ---------- UI ----------
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Milking & Feeding", "Milk Distribution", "Expense", "Payments", "Investments", "Billing"]
)

# Keep simple other pages (you can paste your old content back)
if page == "Milking & Feeding":
    st.title("🐄 Milking & Feeding Log")
    st.caption("Daily cow log data including milk quantity, feed, and health details.")
    df = load_csv(COW_LOG_CSV_URL, drop_cols=["Timestamp"])
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No milking & feeding data available yet.")

elif page == "Milk Distribution":
    st.title("🥛 Milk Distribution")
    st.subheader("Morning Distribution")
    df_morning = load_csv(MILK_DIS_M_CSV_URL,drop_cols=["Timestamp"])
    if not df_morning.empty:
        st.dataframe(df_morning, use_container_width=True)
    else:
        st.info("No morning distribution data available.")
    st.subheader("Evening Distribution")
    df_evening = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])
    if not df_evening.empty:
        st.dataframe(df_evening, use_container_width=True)
    else:
        st.info("No evening distribution data available.")

elif page == "Expense":
    st.title("💸 Expense Tracker")
    df_expense = load_csv(EXPENSE_CSV_URL, drop_cols=["Timestamp"])
    if not df_expense.empty:
        st.dataframe(df_expense, use_container_width=True)
    else:
        st.info("No expense records found.")

elif page == "Payments":
    st.title("💰 Payments Record")
    df_payment = load_csv(PAYMENT_CSV_URL, drop_cols=["Timestamp"])
    if not df_payment.empty:
        st.dataframe(df_payment, use_container_width=True)
    else:
        st.info("No payment records found.")

elif page == "Investments":
    st.title("📈 Investment Log")
    df_invest = load_csv(INVESTMENT_CSV_URL, drop_cols=["Timestamp"])
    if not df_invest.empty:
        st.dataframe(df_invest, use_container_width=True)
    else:
        st.info("No investment data found yet.")

# ---------------- Billing page ----------------
elif page == "Billing":
    st.title("🧾 Billing / Invoice Generator")
    st.write("Compute cycle totals (30-day by default), apply early payments, and view calendar status per day.")

    # load and normalize
    with st.spinner("Loading milk distribution and payments..."):
        merged_shifts = load_and_merge_morning_evening()
        payments = load_payments()

    if merged_shifts.empty:
        st.warning("No milk distribution data found (morning + evening sheets empty). You can still test with sample data below.")
    # list customers
    customers = sorted(merged_shifts['customer_id'].unique().tolist()) if not merged_shifts.empty else []
    # also include customers from payments if not present
    if not payments.empty:
        payments_customers = sorted(payments['customer_id'].unique().tolist())
        for c in payments_customers:
            if c not in customers:
                customers.append(c)

    # sample/test data generator
    if st.checkbox("🔁 Create sample data for quick testing (local only, does NOT write to Sheets)"):
        # create sample merged_shifts and payments in-memory
        today = datetime.today().date()
        sample_customers = ['CUST001','CUST002']
        rows = []
        for cust in sample_customers:
            start = today - timedelta(days=10)
            for i in range(12):
                d = start + timedelta(days=i)
                rows.append({'customer_id':cust, 'date': d, 'shift': 'M', 'litres': round(1.5 + (i%3)*0.5,2)})
                rows.append({'customer_id':cust, 'date': d, 'shift': 'E', 'litres': round(1.1 + (i%2)*0.4,2)})
        merged_shifts = pd.DataFrame(rows)
        payments = pd.DataFrame([{'customer_id':'CUST001','amount':200.0,'date':today - timedelta(days=2)},
                                 {'customer_id':'CUST002','amount':100.0,'date':today - timedelta(days=1)}])
        customers = sample_customers
        st.success("Sample data loaded (in-memory).")

    if not customers:
        st.info("No customers detected. If you want to test, enable sample data above.")
    else:
        st.sidebar.subheader("Billing options")
        default_price = st.sidebar.number_input("Global price per litre (₹)", value=45.0, min_value=0.0, step=1.0)
        cycle_length = st.sidebar.number_input("Cycle length (days)", value=30, min_value=7, max_value=90, step=1)
        cust_sel = st.sidebar.selectbox("Select customer", options=customers)
        # determine customer's first distribution (for cycle anchor)
        cust_shifts = merged_shifts[merged_shifts['customer_id']==str(cust_sel)]
        if not cust_shifts.empty:
            first_date = cust_shifts['date'].min()
        else:
            # fallback to today
            first_date = datetime.today().date()
        # allow override
        st.sidebar.write("Cycle anchor (customer first distribution). Change if needed:")
        cycle_anchor = st.sidebar.date_input("Cycle start date", value=first_date)

        # allow optional per-customer price override
        price_override = st.sidebar.checkbox("Use per-customer price override?")
        if price_override:
            cust_price = st.sidebar.number_input(f"Price per litre for {cust_sel} (₹)", value=default_price, min_value=0.0, step=1.0)
        else:
            cust_price = default_price

        if st.button("▶ Generate invoice & calendar"):
            with st.spinner("Calculating invoice..."):
                summary = compute_cycle_for_customer(merged_shifts, payments, cust_sel, cycle_anchor, cycle_length_days=cycle_length, price_per_litre=cust_price)
                st.subheader(f"Invoice for {cust_sel}")
                st.markdown(f"**Cycle:** {summary['cycle_start'].isoformat()} → {summary['cycle_end'].isoformat()}  \n"
                            f"**Total litres:** {summary['total_litres']:.3f} L  \n"
                            f"**Amount (@ ₹{cust_price:.2f}/L):** ₹{summary['amount']:.2f}  \n"
                            f"**Early payments applied:** ₹{summary['early_payments']:.2f}  \n"
                            f"**Final payable:** ₹{summary['final_payable']:.2f}  \n"
                            f"**Credit (if any):** ₹{summary['credit']:.2f}")

                # show day-level table
                st.subheader("Day-level details (first 100 rows)")
                days = summary['days'].copy()
                days_display = days[['date','M','E','total','status']].head(100)
                days_display['date'] = days_display['date'].astype(str)
                st.dataframe(days_display, use_container_width=True)

                # render calendar (HTML table)
                st.subheader("Calendar view")
                cal_html = build_calendar_html(summary['days'])
                st.markdown(cal_html, unsafe_allow_html=True)

                # show payments applied
                st.subheader("Payments for this customer (detected)")
                df_pay_c = payments[payments['customer_id']==str(cust_sel)].copy() if not payments.empty else pd.DataFrame()
                if not df_pay_c.empty:
                    st.dataframe(df_pay_c, use_container_width=True)
                else:
                    st.info("No payments found for this customer.")


# helper to build calendar html (simple single-column weeks)
def build_calendar_html(days_df):
    """
    days_df: dataframe with date, M, E, total, status
    returns HTML string
    """
    # create small legend + table
    css = """
    <style>
      .cal { border-collapse: collapse; width:100%; }
      .cal td, .cal th { border:1px solid #ddd; padding:6px; text-align:center; vertical-align:top; }
      .daynum { font-weight:600; font-size:14px; display:block; margin-bottom:6px; }
      .mval { font-size:12px; }
      .legend { display:flex; gap:10px; margin-bottom:8px; align-items:center; }
      .legend div { display:flex; align-items:center; gap:6px; }
      .box { width:16px;height:12px;border-radius:3px; display:inline-block; }
    </style>
    """
    legend = """
    <div class="legend">
      <div><span class="box" style="background:#ffffff;border:1px solid #ccc"></span> Both present</div>
      <div><span class="box" style="background:#ffc0cb"></span> Morning missing (M)</div>
      <div><span class="box" style="background:#ffcc99"></span> Evening missing (E)</div>
      <div><span class="box" style="background:#ff9999"></span> Both missing (customer skipped)</div>
    </div>
    """
    rows = ""
    # arrange as 7 columns per week for nicer grid
    days_sorted = days_df.sort_values('date').reset_index(drop=True)
    # find the first week's weekday (Mon=0)
    first_date = pd.to_datetime(days_sorted.loc[0,'date']).date()
    # start weekday index (Sunday=6? We'll assume Monday start)
    # Build weeks
    week = []
    # pad initial empty cells so first date aligns to weekday (optional)
    # We'll just render as a grid of 7 columns starting from the first date
    for idx, r in days_sorted.iterrows():
        dstr = r['date'].isoformat() if hasattr(r['date'],'isoformat') else str(r['date'])
        m = float(r.get('M',0.0) or 0.0)
        e = float(r.get('E',0.0) or 0.0)
        status = r.get('status','both_present')
        if status == 'both_present':
            bgcolor = '#ffffff'
        elif status == 'M_missing':
            bgcolor = '#ffc0cb'
        elif status == 'E_missing':
            bgcolor = '#ffcc99'
        else:
            bgcolor = '#ff9999'
        cell_html = f"""
         <td style="background:{bgcolor}; width:120px; height:80px;">
           <span class="daynum">{dstr}</span>
           <div class="mval"><strong>M:</strong> {m:.2f} L</div>
           <div class="mval"><strong>E:</strong> {e:.2f} L</div>
         </td>
        """
        week.append(cell_html)
    # pad last week to multiple of 7
    while len(week) % 7 != 0:
        week.append('<td></td>')
    # join into rows
    for i in range(0, len(week), 7):
        rows += "<tr>" + "".join(week[i:i+7]) + "</tr>"

    table = f"{css}{legend}<table class='cal'>{rows}</table>"
    return table


if st.sidebar.button("🔁 Refresh all"):
    st.experimental_rerun()
