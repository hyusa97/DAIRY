import streamlit as st 
import pandas as pd


st.set_page_config(page_title="Dairy Farm Management ", layout="wide")

# Load Google Sheet IDs securely
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
        st.error(f"❌ Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()
    

def show_transposed_table(df):
    if df.empty:
        st.warning("No records found.")
        return
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values(by="Date", ascending=False)

    df_t = df.set_index("Date").T
    st.dataframe(df_t, use_container_width=True)





st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Milking & Feeding", "Milk Distribution", "Expense", "Payments", "Investments"]
)

if page == "Milking & Feeding":
    st.title("🐄 Milking & Feeding Log")
    st.caption("Daily cow log data including milk quantity, feed, and health details.")
    
    df = load_csv(COW_LOG_CSV_URL, drop_cols=["Timestamp"])
    if not df.empty:
        #st.dataframe(df, use_container_width=True)
        show_transposed_table(df)
    else:
        st.info("No milking & feeding data available yet.")


elif page == "Milk Distribution":
    st.title("🥛 Milk Distribution")

    st.subheader("Morning Distribution")
    df_morning = load_csv(MILK_DIS_M_CSV_URL,drop_cols=["Timestamp"])
    if not df_morning.empty:
        #st.dataframe(df_morning, use_container_width=True)
        show_transposed_table(df_morning)
    else:
        st.info("No morning distribution data available.")

    st.subheader("Evening Distribution")
    df_evening = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])
    if not df_evening.empty:
        #st.dataframe(df_evening, use_container_width=True)
        show_transposed_table(df_evening)
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
        #st.dataframe(df_invest, use_container_width=True)
        show_transposed_table(df_invest)
    else:
        st.info("No investment data found yet.")