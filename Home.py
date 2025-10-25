# Home.py — MyFinanceHub (integrated)
# Features: login/register, horizontal nav, light/dark toggle, expenses, incomes, budgets,
# charts (plotly), export, profile settings (change password), login analytics, email placeholder.
#
# Requirements: streamlit, pandas, plotly, openpyxl
# Put your logo file (Hublogowithcharts.png) in same folder.

import streamlit as st
import sqlite3
import re
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime, timedelta
import os

# ===============================
# Email Functionality Setup
# ===============================
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os


# Load environment variables from .env or Streamlit secrets
load_dotenv()

def send_email(recipient_email, subject, body):
    """
    Sends an email using Gmail SMTP server.
    Loads credentials securely from environment variables or Streamlit secrets.
    """
    try:
        # Try environment variables first
        sender_email = os.getenv("EMAIL_USER")
        sender_password = os.getenv("EMAIL_PASS")

        # Fallback to Streamlit secrets if available
        if not sender_email and "EMAIL_USER" in st.secrets:
            sender_email = st.secrets["EMAIL_USER"]
            sender_password = st.secrets["EMAIL_PASS"]

        # Email setup
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to Gmail SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return True
    except Exception as e:
        st.error(f"❌ Email sending failed: {e}")
        return False

# ------------------------
# Page config
# ------------------------
st.set_page_config(page_title="MyFinanceHub", page_icon="💰", layout="wide")

# ------------------------
# Styling snippets for light/dark mode (simple)
# ------------------------
# Light theme cards
LIGHT_CSS = """
<style>
.metric-card { 
    background-color: #4F46E5;  /* deep purple */
    color: #ffffff;              /* white text */
    padding: 1rem; 
    border-radius: 12px; 
}
</style>
"""

# Dark theme cards
DARK_CSS = """
<style>
.metric-card { 
    background-color: #0f1724;  /* dark blue */
    color: #ffffff; 
    padding: 1rem; 
    border-radius: 12px; 
}
</style>
"""

# initialize theme toggle
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"

# apply CSS based on theme
if st.session_state["theme"] == "light":
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)
else:
    st.markdown(DARK_CSS, unsafe_allow_html=True)

# ------------------------
# Database setup (SQLite)
# ------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# Users table (store username, password, email optional)
c.execute(
    """CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        email TEXT
    )"""
)

# Expenses table
c.execute(
    """CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        category TEXT,
        amount REAL,
        date TEXT,
        description TEXT
    )"""
)

# Incomes table
c.execute(
    """CREATE TABLE IF NOT EXISTS incomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        amount REAL,
        date TEXT,
        description TEXT
    )"""
)

# Budgets table (per user, category, month, year)
c.execute(
    """CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        category TEXT,
        month INTEGER,
        year INTEGER,
        amount REAL
    )"""
)

# Login analytics
c.execute(
    """CREATE TABLE IF NOT EXISTS logins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        ts TEXT
    )"""
)

conn.commit()

# ------------------------
# Global categories & helpers
# ------------------------
CATEGORIES = ["Food", "Transportation", "Utilities", "Entertainment", "Health", "Education", "Other"]

def password_valid(pw: str) -> bool:
    """Simple password rule: >=8 chars, upper, lower, digit."""
    return bool(re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$', pw))

def register_user(username: str, password: str, email: str = None):
    try:
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", (username, password, email))
        conn.commit()
        return True, "Registered"
    except sqlite3.IntegrityError:
        return False, "Username already exists"

def authenticate(username: str, password: str):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone() is not None

def log_login(username: str):
    c.execute("INSERT INTO logins (username, ts) VALUES (?, ?)", (username, datetime.utcnow().isoformat()))
    conn.commit()

def add_expense(username, category, amount, date, description):
    c.execute("INSERT INTO expenses (username, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
              (username, category, amount, date, description))
    conn.commit()

def get_expenses_df(username) -> pd.DataFrame:
    c.execute("SELECT id, username, category, amount, date, description FROM expenses WHERE username=? ORDER BY date ASC", (username,))
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=["ID", "Username", "Category", "Amount", "Date", "Description"])
    if not df.empty:
        # convert 'Date' safely to datetime
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")  
        df = df.dropna(subset=["Date"])  # remove rows with invalid/missing dates
    return df

def add_income(username, amount, date, description):
    c.execute("INSERT INTO incomes (username, amount, date, description) VALUES (?, ?, ?, ?)",
              (username, amount, date, description))
    conn.commit()

def get_incomes_df(username) -> pd.DataFrame:
    c.execute("SELECT id, username, amount, date, description FROM incomes WHERE username=? ORDER BY date ASC", (username,))
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=["ID", "Username", "Amount", "Date", "Description"])
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
    return df

def set_budget(username, category, month, year, amount):
    c.execute("DELETE FROM budgets WHERE username=? AND category=? AND month=? AND year=?", (username, category, month, year))
    c.execute("INSERT INTO budgets (username, category, month, year, amount) VALUES (?, ?, ?, ?, ?)",
              (username, category, month, year, amount))
    conn.commit()

def get_budgets(username, month, year) -> pd.DataFrame:
    c.execute("SELECT id, category, amount FROM budgets WHERE username=? AND month=? AND year=?", (username, month, year))
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=["id", "Category", "Amount"])
    return df

def send_email(recipient, subject, body, html=False):
    msg = MIMEMultipart("alternative")
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = recipient
    msg["Subject"] = subject

    if html:
        msg.attach(MIMEText(body, "html"))
    else:
        msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        server.send_message(msg)

    return True


# ------------------------
# Session state defaults
# ------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Welcome"

# ------------------------
# Top horizontal navigation (responsive with columns)
# ------------------------
def top_nav():
    # Navigation labels and internal page keys
    nav = [
        ("🏠 Dashboard", "Welcome"),
        ("💸 Expenses", "Add/View"),
        ("📈 Insights", "Insights"),
        ("➕ Income", "Income"),
        ("💰 Budgets", "Budgets"),
        ("⬇️ Export", "Export"),
        ("⚙️ Settings", "Profile")
    ]
    cols = st.columns(len(nav), gap="small")
    for i, (label, key) in enumerate(nav):
        with cols[i]:
            if st.button(label, key=f"topnav_{i}"):
                st.session_state["current_page"] = key
                st.rerun()

# ------------------------
# Welcome / Dashboard page (polished with metrics + responsive nav)
# ------------------------
def page_welcome():
    # Top navigation
    top_nav()

    # Logo + slogan
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image("Hublogowithcharts.png", width=130)
    with c2:
        st.markdown("<h2 style='margin:0;'>MyFinanceHub</h2>", unsafe_allow_html=True)
        st.markdown("<div style='color:gray; margin-top:-10px;'>Smart Spending. Secure Future.</div>", unsafe_allow_html=True)

    st.markdown("---")

    username = st.session_state["username"]
    now = datetime.now()
    df_exp = get_expenses_df(username)
    df_inc = get_incomes_df(username)

    # Fail-safe: empty DataFrames
    if df_exp.empty:
        df_exp = pd.DataFrame(columns=["ID", "Username", "Category", "Amount", "Date", "Description"])
    if df_inc.empty:
        df_inc = pd.DataFrame(columns=["ID", "Username", "Amount", "Date", "Description"])

    # Filter current month safely
    if not df_exp.empty and pd.api.types.is_datetime64_any_dtype(df_exp["Date"]):
        this_month_exp = df_exp[(df_exp["Date"].dt.year == now.year) & (df_exp["Date"].dt.month == now.month)]
    else:
        this_month_exp = pd.DataFrame(columns=df_exp.columns)

    total_exp_month = this_month_exp["Amount"].sum() if not this_month_exp.empty else 0.0

    if not df_inc.empty and pd.api.types.is_datetime64_any_dtype(df_inc["Date"]):
        this_month_inc = df_inc[(df_inc["Date"].dt.year == now.year) & (df_inc["Date"].dt.month == now.month)]
    else:
        this_month_inc = pd.DataFrame(columns=df_inc.columns)

    total_inc_month = this_month_inc["Amount"].sum() if not this_month_inc.empty else 0.0
    net_month = total_inc_month - total_exp_month

    # Top category this month
    if not this_month_exp.empty:
        top_cat = this_month_exp.groupby("Category")["Amount"].sum().idxmax()
    else:
        top_cat = "—"

    # Layout for four metric cards responsive
    mcols = st.columns(4)
    card_colors = ["#4F46E5", "#06b6d4", "#F59E0B", "#10B981"]  # new dashboard colors
    card_text = [
        (f"Total Spent (This Month)", f"R {total_exp_month:,.2f}"),
        (f"Total Income (This Month)", f"R {total_inc_month:,.2f}"),
        (f"Net (This Month)", f"R {net_month:,.2f}"),
        (f"Top Category", top_cat)
    ]

    for i, col in enumerate(mcols):
        label, value = card_text[i]
        color = card_colors[i % len(card_colors)]
        col.markdown(
            f"<div style='background-color:{color}; padding:1rem; border-radius:12px; color:white;'>"
            f"<h3>{label}</h3><h2>{value}</h2></div>", unsafe_allow_html=True
        )

    st.markdown("---")

    # Quick action buttons
    actions = [
        ("➕ Add Expense", "Add/View"),
        ("📋 Manage Expenses", "Add/View"),
        ("📊 View Insights", "Insights"),
        ("➕ Add Income", "Income"),
        ("💰 Budgets", "Budgets")
    ]
    cols = st.columns(len(actions), gap="small")
    for i, (label, page) in enumerate(actions):
        with cols[i]:
            if st.button(label, key=f"action_{i}"):
                st.session_state["current_page"] = page
                st.rerun()

    # Show login analytics small card
    st.markdown("### Activity")
    c.execute("SELECT ts FROM logins WHERE username=? ORDER BY ts DESC LIMIT 5", (username,))
    recent = c.fetchall()
    if recent:
        for r in recent:
            st.write(f"- {pd.to_datetime(r[0]).strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        st.write("No recent logins recorded.")

# ------------------------
# Expenses pages (Add / View / Manage)
# ------------------------
def page_add_view_expenses():
    top_nav()
    st.header("💸 Expenses")

    tab = st.radio("Choose action", ["Add Expense", "View & Manage Expenses"], index=0, horizontal=True)
    if tab == "Add Expense":
        st.subheader("➕ Add Expense")
        category = st.selectbox("Category", CATEGORIES)
        amount = st.number_input("Amount (R)", min_value=0.0, format="%.2f")
        date = st.date_input("Date", value=datetime.now())
        desc = st.text_area("Description (optional)")
        if st.button("Save Expense"):
            add_expense(st.session_state["username"], category, float(amount), date.strftime("%Y-%m-%d"), desc)
            st.success("Expense added.")
            st.rerun()
    else:
        # View & Manage
        st.subheader("📋 View & Manage Expenses")
        df = get_expenses_df(st.session_state["username"])
        if df.empty:
            st.info("No expenses yet.")
            return

        # Display sequential "No." for user friendliness
        disp = df.copy().sort_values("Date", ascending=False).reset_index(drop=True)
        disp.insert(0, "No.", range(1, len(disp) + 1))

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            cat_filter = st.selectbox("Filter by Category", options=["All"] + CATEGORIES)
        with col2:
            q = st.text_input("Search description")

        filtered = disp.copy()
        if cat_filter != "All":
            filtered = filtered[filtered["Category"] == cat_filter]
        if q:
            filtered = filtered[filtered["Description"].str.contains(q, case=False, na=False)]

        st.dataframe(filtered[["No.", "Date", "Category", "Amount", "Description"]], use_container_width=True)

        # Edit/Delete selection by No. (map to actual DB ID)
        st.subheader("✏️ Edit / Delete")
        selected_no = st.selectbox("Select No.", options=filtered["No."])
        # Map No. back to DB ID
        selected_row = filtered[filtered["No."] == selected_no].iloc[0]
        # find DB ID by matching Date+Amount+Description (safer method could use stored DB ID column)
        # we still have the original ID in column 'ID' — use it:
        db_id = selected_row["ID"]

        # Editable form
        new_date = st.date_input("Date", pd.to_datetime(selected_row["Date"]))
        new_cat = st.selectbox("Category", options=CATEGORIES, index=CATEGORIES.index(selected_row["Category"]) if selected_row["Category"] in CATEGORIES else 0)
        new_desc = st.text_input("Description", value=selected_row["Description"])
        new_amount = st.number_input("Amount (R)", min_value=0.0, value=float(selected_row["Amount"]))

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Update Expense"):
                c.execute("""UPDATE expenses SET date=?, category=?, description=?, amount=? WHERE id=? AND username=?""",
                          (new_date.strftime("%Y-%m-%d"), new_cat, new_desc, new_amount, db_id, st.session_state["username"]))
                conn.commit()
                st.success("Updated.")
                st.rerun()
        with c2:
            confirm = st.checkbox("Confirm delete")
            if st.button("Delete Expense"):
                if confirm:
                    c.execute("DELETE FROM expenses WHERE id=? AND username=?", (db_id, st.session_state["username"]))
                    conn.commit()
                    st.success("Deleted.")
                    st.rerun()
                else:
                    st.warning("Check confirm to delete.")

# ------------------------
# Income page
# ------------------------
def page_income():
    top_nav()
    st.header("💰 Income")
    tab = st.radio("Action", ["Add Income", "View Incomes"], horizontal=True)
    if tab == "Add Income":
        st.subheader("➕ Add Income")
        amount = st.number_input("Amount (R)", min_value=0.0, format="%.2f")
        date = st.date_input("Date", value=datetime.now())
        desc = st.text_input("Description (optional)")
        if st.button("Save Income"):
            add_income(st.session_state["username"], float(amount), date.strftime("%Y-%m-%d"), desc)
            st.success("Income saved.")
            st.rerun()
    else:
        df = get_incomes_df(st.session_state["username"])
        if df.empty:
            st.info("No incomes recorded.")
            return
        disp = df.sort_values("Date", ascending=False).reset_index(drop=True)
        disp.insert(0, "No.", range(1, len(disp) + 1))
        st.dataframe(disp[["No.", "Date", "Amount", "Description"]], use_container_width=True)

# ------------------------
# Budgets page
# ------------------------
def page_budgets():
    top_nav()
    st.header("💡 Budgets")
    st.subheader("Set monthly budget per category")
    col1, col2, col3 = st.columns(3)
    with col1:
        sel_month = st.selectbox("Month", [i for i in range(1, 13)], format_func=lambda x: datetime(2000, x, 1).strftime("%B"))
    with col2:
        sel_year = st.selectbox("Year", [datetime.now().year, datetime.now().year + 1])
    with col3:
        sel_cat = st.selectbox("Category", CATEGORIES)

    amount = st.number_input("Budget amount (R)", min_value=0.0, format="%.2f")
    if st.button("Save Budget"):
        set_budget(st.session_state["username"], sel_cat, sel_month, sel_year, float(amount))
        st.success("Budget saved.")

    st.markdown("### Current budgets")
    budgets_df = get_budgets(st.session_state["username"], sel_month, sel_year)
    if budgets_df.empty:
        st.info("No budgets for selected month/year.")
    else:
        st.dataframe(budgets_df[["Category", "Amount"]], use_container_width=True)

    # Visualize progress against budgets
    df = get_expenses_df(st.session_state["username"])
    if not df.empty:
        df = df[(df["Date"].dt.month == sel_month) & (df["Date"].dt.year == sel_year)]
        if not df.empty:
            spent_by_cat = df.groupby("Category", as_index=False)["Amount"].sum()
            merged = pd.merge(budgets_df, spent_by_cat, how="left", left_on="Category", right_on="Category").fillna(0)
            merged["Pct"] = merged["Amount_y"] / merged["Amount"] * 100
            merged = merged.rename(columns={"Amount_x": "Budget", "Amount_y": "Spent"})
            if not merged.empty:
                st.markdown("#### Budget progress")
                for _, row in merged.iterrows():
                    pct = min((row["Spent"] / row["Budget"]) if row["Budget"] > 0 else 0, 1)
                    st.write(f"**{row['Category']}** — Spent R{row['Spent']:.2f} / Budget R{row['Budget']:.2f}")
                    st.progress(pct)

# ------------------------
# Insights page (trends, category insights)
# ------------------------
def page_insights():
    top_nav()
    st.header("📈 Insights")

    df_exp = get_expenses_df(st.session_state["username"])
    df_inc = get_incomes_df(st.session_state["username"])

    if df_exp.empty and df_inc.empty:
        st.info("No data yet for insights.")
        return

    # Date range selection
    min_date = df_exp["Date"].min() if not df_exp.empty else datetime.now() - timedelta(days=180)
    max_date = df_exp["Date"].max() if not df_exp.empty else datetime.now()
    start, end = st.date_input("Select date range", [min_date, max_date])

    masked_exp = df_exp[(df_exp["Date"] >= pd.to_datetime(start)) & (df_exp["Date"] <= pd.to_datetime(end))] if not df_exp.empty else pd.DataFrame()
    masked_inc = df_inc[(df_inc["Date"] >= pd.to_datetime(start)) & (df_inc["Date"] <= pd.to_datetime(end))] if not df_inc.empty else pd.DataFrame()

    # Expense trend last 6 months
    st.subheader("Spending trend (last 6 months)")
    today = datetime.now()
    six_months_ago = today - pd.DateOffset(months=5)
    trend_df = df_exp[df_exp["Date"] >= six_months_ago] if not df_exp.empty else pd.DataFrame()
    if not trend_df.empty:
        trend = trend_df.copy()
        trend["YM"] = trend["Date"].dt.to_period("M").dt.to_timestamp()
        monthly = trend.groupby("YM")["Amount"].sum().reset_index()
        fig = px.line(monthly, x="YM", y="Amount", title="Monthly Spending (last 6 months)", markers=True)
        fig.update_layout(transition_duration=400, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data for trend chart.")

    # Category insights: top 3 categories highlighted
    st.subheader("Category insights")
    if not masked_exp.empty:
        cat_sum = masked_exp.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
        top3 = cat_sum.head(3)

        # Define colors: top3 get distinct colors, others gray
        colors = {}
        top_colors = ["#FF6B6B", "#4ECDC4", "#FDCB6E"]  # top 3
        for i, cat in enumerate(top3["Category"]):
            colors[cat] = top_colors[i]
        for cat in cat_sum["Category"]:
            if cat not in colors:
                colors[cat] = "#C0C0C0"  # gray for others

        st.markdown("**Top 3 categories**")
        st.bar_chart(top3.set_index("Category")["Amount"])

        st.markdown("**All categories**")
        fig2 = px.bar(cat_sum, x="Category", y="Amount", color="Category",
                      color_discrete_map=colors, template="plotly_white",
                      title="Spending by category")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No expenses in selected range for category insights.")

    # Income vs Expense (net savings)
    st.subheader("Income vs Expenses")
    if not masked_inc.empty or not masked_exp.empty:
        # Aggregate per month
        def monthly_agg(df, col_amount, name):
            temp = df.copy()
            temp["YM"] = temp["Date"].dt.to_period("M").dt.to_timestamp()
            return temp.groupby("YM")[col_amount].sum().reset_index().rename(columns={col_amount: name})

        m_exp = monthly_agg(masked_exp, "Amount", "Expenses") if not masked_exp.empty else pd.DataFrame(columns=["YM", "Expenses"])
        m_inc = monthly_agg(masked_inc, "Amount", "Income") if not masked_inc.empty else pd.DataFrame(columns=["YM", "Income"])
        merged = pd.merge(m_exp, m_inc, on="YM", how="outer").fillna(0).sort_values("YM")
        if not merged.empty:
            fig3 = px.line(merged, x="YM", y=["Income", "Expenses"], title="Income vs Expenses", markers=True)
            fig3.update_layout(template="plotly_white")
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No income/expense data in range.")
        

# ===============================
# 📬 Monthly Email Summary Feature (HTML-Styled)
# ===============================
st.markdown("### 📧 Email Your Monthly Summary")

with st.expander("Send a Summary Report via Email"):
    st.write("Get a beautiful monthly summary of your expenses sent directly to your inbox.")

    # Fetch user data for the current month
    username = st.session_state.get("username")
    if username:
        df_exp = get_expenses_df(username)
        df_inc = get_incomes_df(username)

        now = datetime.now()
        df_exp_month = df_exp[(df_exp["Date"].dt.year == now.year) & (df_exp["Date"].dt.month == now.month)] if not df_exp.empty else pd.DataFrame()
        df_inc_month = df_inc[(df_inc["Date"].dt.year == now.year) & (df_inc["Date"].dt.month == now.month)] if not df_inc.empty else pd.DataFrame()

        total_spent = df_exp_month["Amount"].sum() if not df_exp_month.empty else 0.0
        total_income = df_inc_month["Amount"].sum() if not df_inc_month.empty else 0.0
        net_savings = total_income - total_spent
        top_category = df_exp_month.groupby("Category")["Amount"].sum().idxmax() if not df_exp_month.empty else "N/A"
    else:
        df_exp_month, total_spent, total_income, net_savings, top_category = pd.DataFrame(), 0.0, 0.0, 0.0, "N/A"

    recipient_email = st.text_input("Enter your email address")

    if st.button("Send Monthly Summary"):
        if not recipient_email:
            st.warning("Please enter your email address.")
        else:
            subject = f"📊 MyFinanceHub - Monthly Summary ({now.strftime('%B %Y')})"

            # -------------------------------
            # HTML Body Template
            # -------------------------------
            body_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f9fafc; color: #333; padding: 20px;">
                    <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); padding: 25px;">
                        <h2 style="color: #2C3E50; text-align: center;">💰 MyFinanceHub Monthly Summary</h2>
                        <p style="font-size: 16px;">Hello <strong>{username or 'User'}</strong>,</p>
                        <p>Here’s your financial overview for <strong>{now.strftime('%B %Y')}</strong>:</p>

                        <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Total Income</td>
                                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right; color: #27AE60;">R{total_income:,.2f}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Total Expenses</td>
                                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right; color: #E74C3C;">R{total_spent:,.2f}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Net Savings</td>
                                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right; color: #2980B9;">R{net_savings:,.2f}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px;">Top Spending Category</td>
                                <td style="padding: 10px; text-align: right;">{top_category}</td>
                            </tr>
                        </table>

                        <p style="margin-top: 20px;">Keep tracking and growing your finances wisely! 🌱</p>
                        <p style="text-align: center; font-size: 14px; color: #888;">– The MyFinanceHub Team</p>
                    </div>
                </body>
            </html>
            """

            # Send the email using HTML
            if send_email(recipient_email, subject, body_html, html=True):
                st.success("✅ Styled summary email sent successfully!")
            else:
                st.error("❌ Failed to send summary email. Please check your email configuration.")

# ------------------------
# Export page (export filtered or all)
# ------------------------
def page_export():
    top_nav()
    st.header("⬇️ Export Data")
    df = get_expenses_df(st.session_state["username"])
    if df.empty:
        st.info("No data to export.")
        return
    st.write("You may export all data or choose a date range.")

    start, end = st.date_input("Range", [df["Date"].min(), df["Date"].max()])
    filtered = df[(df["Date"] >= pd.to_datetime(start)) & (df["Date"] <= pd.to_datetime(end))]
    st.write(f"Exporting {len(filtered)} records.")

    csv = filtered.to_csv(index=False).encode("utf-8")
    excel_buffer = BytesIO()
    filtered.to_excel(excel_buffer, index=False, engine="openpyxl")
    st.download_button("Download CSV", csv, "expenses.csv", "text/csv")
    st.download_button("Download Excel", excel_buffer.getvalue(), "expenses.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ------------------------
# Profile settings (change pw, email, toggle theme, email summary)
# ------------------------
def page_profile():
    top_nav()
    st.header("⚙️ Profile Settings")

    # change password
    st.subheader("Change password")
    current = st.text_input("Current password", type="password")
    newpw = st.text_input("New password", type="password")
    confirm = st.text_input("Confirm new password", type="password")
    if st.button("Update Password"):
        if not current or not newpw or not confirm:
            st.warning("Fill all fields")
        elif newpw != confirm:
            st.error("New passwords do not match.")
        elif not password_valid(newpw):
            st.error("Password must be >=8 chars with upper and digit.")
        else:
            ok = authenticate(st.session_state["username"], current)
            if ok:
                c.execute("UPDATE users SET password=? WHERE username=?", (newpw, st.session_state["username"]))
                conn.commit()
                st.success("Password updated.")
            else:
                st.error("Incorrect current password.")

    # email for summary (placeholder)
    st.subheader("Email summary (optional)")
    st.markdown("Configure SMTP in code or with env vars. This UI only collects recipient address for now.")
    recipient = st.text_input("Recipient email for monthly summary (optional)")
    if st.button("Send a test summary (placeholder)"):
        # DON'T PUT SMTP creds here. This is a placeholder demo.
        st.info("This would send an email if SMTP settings are configured in the environment.")
        st.write(f"A summary would be emailed to: {recipient}")

    # theme toggle
    st.subheader("Theme")
    if st.session_state["theme"] == "light":
        if st.button("Switch to Dark Mode"):
            st.session_state["theme"] = "dark"
            st.rerun()
    else:
        if st.button("Switch to Light Mode"):
            st.session_state["theme"] = "light"
            st.rerun()

# ------------------------
# Authentication UI (login/register)
# ------------------------
def page_auth():
    st.title("Welcome to MyFinanceHub")
    st.image("Hublogowithcharts.png", width=260)
    st.markdown("<h4 style='text-align:center;'>Smart Spending. Secure Future.</h4>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        user = st.text_input("Username", key="login_user")
        pw = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            if authenticate(user, pw):
                st.session_state["logged_in"] = True
                st.session_state["username"] = user
                log_login(user)  # record login
                st.success("Logged in.")
                st.rerun()
            else:
                st.error("Invalid credentials.")
    with tab2:
        newu = st.text_input("Choose username", key="reg_user")
        newpw = st.text_input("Choose password", type="password", key="reg_pw")
        newpw2 = st.text_input("Confirm password", type="password", key="reg_pw2")
        email = st.text_input("Email (optional)", key="reg_email")
        if st.button("Register"):
            if newpw != newpw2:
                st.error("Passwords don't match.")
            elif not password_valid(newpw):
                st.error("Password must be >=8 chars, contain upper and digit.")
            else:
                ok, msg = register_user(newu, newpw, email)
                if ok:
                    st.success("Registered. Please login.")
                else:
                    st.error(msg)

# ------------------------
# Router: render pages based on session state
# ------------------------
def router():
    if not st.session_state["logged_in"]:
        page_auth()
        return

    page = st.session_state.get("current_page", "Welcome")
    if page == "Welcome":
        page_welcome()
    elif page == "Add/View":
        page_add_view_expenses()
    elif page == "Income":
        page_income()
    elif page == "Budgets":
        page_budgets()
    elif page == "Insights":
        page_insights()
    elif page == "Export":
        page_export()
    elif page == "Profile":
        page_profile()
    else:
        page_welcome()

# ------------------------
# Run app
# ------------------------
router()