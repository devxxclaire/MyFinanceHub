import streamlit as st
import sqlite3
import re
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime

# ---------------------------
# Styling setup block
# ---------------------------
st.markdown("""
    <style>
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #E5E7EB; /* Light gray */
        padding: 1rem;
        color: #111827; /* Dark text for contrast */
    }

    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] p {
        color: #111827 !important;
        font-weight: 500;
    }

    /* Buttons */
    div.stButton > button {
        background-color: #4F46E5;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #4338CA;
        transform: scale(1.03);
    }

    /* Headers */
    h1, h2, h3 {
        color: #1E3A8A;
        font-weight: 600;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #EEF2FF;
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.05);
        transition: 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Database setup
# ---------------------------
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

# Users table
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL
)
""")

# Expenses table
c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    category TEXT,
    amount REAL,
    date TEXT,
    description TEXT
)
""")
conn.commit()

# ---------------------------
# Helper functions
# ---------------------------
def password_valid(pw):
    """Check password rules."""
    return len(pw) >= 8 and re.search(r"[A-Z]", pw) and re.search(r"[a-z]", pw) and re.search(r"[0-9]", pw)

def register_user(username, password):
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone()

def add_expense(username, category, amount, date, description):
    c.execute("INSERT INTO expenses (username, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
              (username, category, amount, date, description))
    conn.commit()

def get_expenses(username):
    c.execute("SELECT * FROM expenses WHERE username=? ORDER BY date ASC", (username,))
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=["ID", "Username", "Category", "Amount", "Date", "Description"])
    return df

def reset_expense_ids(username):
    """Dynamically reset IDs after deletion to keep them sequential."""
    df = get_expenses(username)
    c.execute("DELETE FROM expenses WHERE username=?", (username,))
    conn.commit()
    for i, row in df.iterrows():
        c.execute("INSERT INTO expenses (username, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
                  (row["Username"], row["Category"], row["Amount"], row["Date"], row["Description"]))
    conn.commit()

# ---------------------------
# App State
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

# Predefined categories used throughout the app
categories = ["Food", "Transportation", "Utilities", "Entertainment", "Health", "Education", "Other"]

# ---------------------------
# Login/Register Section
# ---------------------------
def login_screen():
    st.title("💰 MyFinanceHub")
    st.image("Hublogowithcharts.png", width=450)  # Replace with your own logo
    st.markdown("<h4 style='text-align:center;'>Smart Spending. Secure Future.</h4>", unsafe_allow_html=True)

    st.subheader("Login or Register")
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])

    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.current_page = "Welcome"
                st.success("Login successful!")
            else:
                st.error("Invalid username or password")

    with tab2:
        new_user = st.text_input("Create Username", key="reg_username")
        new_pass = st.text_input("Create Password", type="password", key="reg_password")
        confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_password")

        if st.button("Register"):
            if not password_valid(new_pass):
                st.warning("Password must have at least 8 characters, 1 uppercase, 1 lowercase, and 1 digit.")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match.")
            else:
                try:
                    register_user(new_user, new_pass)
                    st.success("Account created successfully! Please log in.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists.")

# ---------------------------
# Welcome Page
# ---------------------------
def welcome_page():
    # ---------------------------
    # Logo & Slogan
    # ---------------------------
    st.image("Hublogowithcharts.png", width=250)  # Replace with your logo file
    st.markdown("<h4 style='text-align:center; color:#1E3A8A;'>Smart Spending. Secure Future.</h4>", unsafe_allow_html=True)

    st.markdown(f"### 👋 Welcome back, {st.session_state.username}!")
    st.markdown("#### *Track your spending. Grow your savings.*")

    st.write("What would you like to do today?")

    # ---------------------------
    # Buttons as Metric Cards
    # ---------------------------
    buttons = [
        ("➕ Add Expense", "Add Expense"),
        ("📋 View & Manage Expenses", "View & Manage Expenses"),
        ("📊 View Expense Distribution", "View Expense Distribution"),
        ("⬇️ Export Data", "Export Data"),
        ("⚙️ Profile Settings", "Profile Settings")
    ]

    # Dynamically create one column per button
    num_buttons = len(buttons)
    cols = st.columns(num_buttons, gap="medium")  # Gap ensures spacing between buttons

    for i, (label, page_name) in enumerate(buttons):
        with cols[i]:
            # Metric-style container with hover effect
            if st.button(label, key=f"welcome_btn_{i}"):
                st.session_state.current_page = page_name
                st.rerun()

# ---------------------------
# Dashboard
# ---------------------------
def dashboard():
    st.sidebar.title(f"Welcome, {st.session_state.username}")
    menu = ["Welcome", "Add Expense", "View & Manage Expenses", "View Expense Distribution", "Export Data", "Profile Settings", "Logout"]
    choice = st.sidebar.radio("Navigate", menu, index=menu.index(st.session_state.current_page) if st.session_state.current_page in menu else 0)
    st.session_state.current_page = choice

    # Logout
    if choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.current_page = "Home"
        st.experimental_set_query_params()
        st.rerun()

    # Welcome Page
    elif choice == "Welcome":
        welcome_page()

    # Add Expense Page
    elif choice == "Add Expense":
        st.header("➕ Add Expense")
        category = st.selectbox("Category", categories)
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        date = st.date_input("Date", value=datetime.now())
        desc = st.text_area("Description")

        if st.button("Save Expense"):
            add_expense(st.session_state.username, category, amount, date.strftime("%Y-%m-%d"), desc)
            st.success("Expense added successfully!")

    # View & Manage Expenses
    elif choice == "View & Manage Expenses":
        st.header("📋 Manage Your Expenses")
        df = get_expenses(st.session_state.username)

        if df.empty:
            st.info("You have no recorded expenses yet.")
            return

        # Reset IDs to ensure sequential numbering
        df = df.reset_index(drop=True)
        df.index += 1
        df["ID"] = df.index

        # Search & filter
        st.subheader("🔍 Search & Filter Expenses")
        col1, col2 = st.columns(2)
        with col1:
            category_filter = st.selectbox("Filter by Category", options=["All"] + categories)
        with col2:
            search_query = st.text_input("Search Description")

        filtered_df = df.copy()
        if category_filter != "All":
            filtered_df = filtered_df[filtered_df["Category"] == category_filter]
        if search_query:
            filtered_df = filtered_df[filtered_df["Description"].str.contains(search_query, case=False, na=False)]

        st.dataframe(filtered_df, use_container_width=True)

        # Edit/Delete
        st.subheader("✏️ Edit or Remove an Expense")
        if not filtered_df.empty:
            selected_id = st.selectbox("Select Expense ID to Manage", filtered_df["ID"])
            selected_row = df[df["ID"] == selected_id].iloc[0]

            new_date = st.date_input("📅 Date", pd.to_datetime(selected_row["Date"]))
            new_category = st.selectbox("🏷️ Category", options=categories, index=categories.index(selected_row["Category"]))
            new_description = st.text_input("🧾 Description", selected_row["Description"])
            new_amount = st.number_input("💸 Amount (R)", min_value=0.0, value=float(selected_row["Amount"]), step=1.0)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Update Expense"):
                    c.execute("""
                        UPDATE expenses
                        SET date=?, category=?, description=?, amount=?
                        WHERE rowid=? AND username=?
                    """, (new_date.strftime("%Y-%m-%d"), new_category, new_description, new_amount, selected_id, st.session_state.username))
                    conn.commit()
                    st.success("✅ Expense updated successfully!")
                    st.rerun()

            with col2:
                delete_confirm = st.checkbox("⚠️ Confirm Delete")
                if st.button("🗑️ Delete Expense"):
                    if delete_confirm:
                        c.execute("DELETE FROM expenses WHERE rowid=? AND username=?", (selected_id, st.session_state.username))
                        conn.commit()
                        reset_expense_ids(st.session_state.username)
                        st.warning("🗑️ Expense deleted successfully!")
                        st.rerun()
                    else:
                        st.info("Please check 'Confirm Delete' before deleting.")

    # View Expense Distribution
    elif choice == "View Expense Distribution":
        st.header("📊 Expense Distribution")
        df = get_expenses(st.session_state.username)
        if df.empty:
            st.info("No expenses to display yet.")
            return

        # Filter by month/year
        st.subheader("📅 Filter by Date")
        df["Date"] = pd.to_datetime(df["Date"])
        months = ["All"] + [datetime(2000, i, 1).strftime('%B') for i in range(1, 13)]
        month_filter = st.selectbox("Month", options=months)
        years = ["All"] + sorted(df["Date"].dt.year.unique().tolist())
        year_filter = st.selectbox("Year", options=years)

        # Filter by date range
        start_date = st.date_input("Start Date", df["Date"].min())
        end_date = st.date_input("End Date", df["Date"].max())

        filtered_df = df.copy()
        if month_filter != "All":
            filtered_df = filtered_df[filtered_df["Date"].dt.month == datetime.strptime(month_filter, "%B").month]
        if year_filter != "All":
            filtered_df = filtered_df[filtered_df["Date"].dt.year == year_filter]
        filtered_df = filtered_df[(filtered_df["Date"] >= pd.to_datetime(start_date)) & (filtered_df["Date"] <= pd.to_datetime(end_date))]

        if filtered_df.empty:
            st.info("No expenses in the selected period.")
            return

        category_summary = filtered_df.groupby("Category", as_index=False)["Amount"].sum()

        # Interactive Pie Chart
        pie_fig = px.pie(
            category_summary,
            names="Category",
            values="Amount",
            title="Expense Breakdown by Category",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hole=0.3
        )
        pie_fig.update_traces(textinfo="percent+label", hoverinfo="label+percent+value", pull=[0.05]*len(category_summary))
        st.plotly_chart(pie_fig, use_container_width=True)

        # Interactive Bar Chart
        bar_fig = px.bar(
            category_summary,
            x="Category",
            y="Amount",
            text_auto=".2s",
            color="Category",
            title="Expense Amount per Category",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        bar_fig.update_traces(marker_line_width=1, marker_line_color="black", hovertemplate="<b>%{x}</b><br>Amount: R%{y:,.2f}")
        bar_fig.update_layout(xaxis_title="", yaxis_title="Amount (R)", template="plotly_white")
        st.plotly_chart(bar_fig, use_container_width=True)

    # Export Data
    elif choice == "Export Data":
        st.header("⬇️ Export Your Data")
        df = get_expenses(st.session_state.username)
        if df.empty:
            st.info("No data available for export.")
        else:
            csv = df.to_csv(index=False).encode("utf-8")
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False, engine="openpyxl")
            st.download_button("Download CSV", csv, "expenses.csv", "text/csv")
            st.download_button("Download Excel", excel_buffer.getvalue(), "expenses.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Profile Settings
    elif choice == "Profile Settings":
        st.header("⚙️ Profile Settings")
        st.subheader("Change Password")
        current_pass = st.text_input("Current Password", type="password")
        new_pass = st.text_input("New Password", type="password")
        confirm_new_pass = st.text_input("Confirm New Password", type="password")

        if st.button("Update Password"):
            if not current_pass or not new_pass or not confirm_new_pass:
                st.warning("Please fill in all fields.")
            elif new_pass != confirm_new_pass:
                st.error("New passwords do not match.")
            elif not password_valid(new_pass):
                st.error("Password must have at least 8 chars, include upper, lower, and number.")
            else:
                user = login_user(st.session_state.username, current_pass)
                if user:
                    c.execute("UPDATE users SET password=? WHERE username=?", (new_pass, st.session_state.username))
                    conn.commit()
                    st.success("Password updated successfully! 🎉")
                else:
                    st.error("Incorrect current password.")

# ---------------------------
# App Runner
# ---------------------------
if not st.session_state.logged_in:
    login_screen()
else:
    dashboard()