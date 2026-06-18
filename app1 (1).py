import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from sklearn.linear_model import LinearRegression
import time
import sqlite3
import hashlib
import os
import re
from datetime import datetime

# ── optional bcrypt ──────────────────────────────────────────────────────────
try:
    import bcrypt
    USE_BCRYPT = True
except ImportError:
    USE_BCRYPT = False

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Business Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── DB & AUTH HELPERS ─────────────────────────────────────────────────────────
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table with base columns if it doesn't exist at all
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    username TEXT UNIQUE,
                    password TEXT,
                    last_login TEXT)''')

    # Get existing columns
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(users)")}

    # Auto-add any missing columns (safe for old databases)
    migrations = [
        ("failed_attempts", "INTEGER DEFAULT 0"),
        ("locked_until",    "TEXT DEFAULT NULL"),
    ]
    for col_name, col_def in migrations:
        if col_name not in existing_cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")

    conn.commit()
    conn.close()

init_db()

# ── Password hashing (bcrypt preferred, SHA-256+salt fallback) ────────────────
def hash_password(password: str) -> str:
    if USE_BCRYPT:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, stored: str) -> bool:
    if USE_BCRYPT:
        try:
            return bcrypt.checkpw(password.encode(), stored.encode())
        except Exception:
            pass
    if ":" in stored:
        salt, hashed = stored.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    # legacy plain SHA-256 (migrate on next login)
    return hashlib.sha256(password.encode()).hexdigest() == stored

def add_userdata(company_name, username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'INSERT INTO users(company_name, username, password, last_login) VALUES (?,?,?,?)',
        (company_name, username, hash_password(password),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def login_user(username: str, password: str):
    """
    Returns (success: bool, message: str, company: str)
    Implements a 5-attempt lockout for 5 minutes.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT password, failed_attempts, locked_until, company_name FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "Incorrect username or password.", ""

    stored_pw, failed, locked_until, company = row

    # Check lockout
    if locked_until:
        lock_dt = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < lock_dt:
            remaining = int((lock_dt - datetime.now()).total_seconds() // 60) + 1
            conn.close()
            return False, f"Account locked. Try again in {remaining} minute(s).", ""
        else:
            c.execute('UPDATE users SET failed_attempts=0, locked_until=NULL WHERE username=?', (username,))
            conn.commit()
            failed = 0

    if verify_password(password, stored_pw):
        # Re-hash with modern algorithm if legacy hash detected
        if not USE_BCRYPT and ":" not in stored_pw:
            c.execute('UPDATE users SET password=? WHERE username=?', (hash_password(password), username))
        c.execute('UPDATE users SET last_login=?, failed_attempts=0, locked_until=NULL WHERE username=?',
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
        conn.commit()
        conn.close()
        return True, f"Welcome back, {username}!", company
    else:
        failed += 1
        locked = None
        if failed >= 5:
            from datetime import timedelta
            locked = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute('UPDATE users SET failed_attempts=?, locked_until=? WHERE username=?',
                  (failed, locked, username))
        conn.commit()
        conn.close()
        attempts_left = max(0, 5 - failed)
        msg = "Incorrect username or password."
        if attempts_left > 0:
            msg += f" {attempts_left} attempt(s) remaining before lockout."
        else:
            msg = "Account locked for 5 minutes due to too many failed attempts."
        return False, msg, ""

# ── Validate password strength ────────────────────────────────────────────────
def validate_password(pw: str):
    errors = []
    if len(pw) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", pw):
        errors.append("one uppercase letter")
    if not re.search(r"\d", pw):
        errors.append("one number")
    return errors

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for key, default in [("logged_in", False), ("username", ""), ("company", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── AUTHENTICATION SCREEN ─────────────────────────────────────────────────────
if not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;color:#111827;'>Welcome to Smart Business Dashboard</h1>",
                unsafe_allow_html=True)
    menu_auth = st.sidebar.selectbox("Login / Sign Up", ["Login", "Sign Up"])

    if menu_auth == "Login":
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                ok, msg, company = login_user(username, password)
                if ok:
                    st.success(msg)
                    st.session_state.update(logged_in=True, username=username, company=company)
                    st.rerun()
                else:
                    st.error(msg)

    else:
        st.subheader("Create New Account")
        new_company  = st.text_input("Company Name")
        new_user     = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        confirm_pw   = st.text_input("Confirm Password", type="password")

        if st.button("Sign Up"):
            if not all([new_company, new_user, new_password, confirm_pw]):
                st.warning("All fields are required.")
            elif new_password != confirm_pw:
                st.error("Passwords do not match.")
            else:
                pw_errors = validate_password(new_password)
                if pw_errors:
                    st.error("Password must contain: " + ", ".join(pw_errors) + ".")
                else:
                    try:
                        add_userdata(new_company, new_user, new_password)
                        st.success("Account created! Go to Login to continue.")
                    except sqlite3.IntegrityError:
                        st.error("Username already exists. Please choose a different one.")
    st.stop()

# ── SIDEBAR – logged in ───────────────────────────────────────────────────────
st.sidebar.markdown(f"**👤 {st.session_state['username']}**")
if st.session_state["company"]:
    st.sidebar.caption(st.session_state["company"])
st.sidebar.button("Logout", on_click=lambda: st.session_state.update(
    logged_in=False, username="", company=""))

# ── HELPERS ───────────────────────────────────────────────────────────────────
def find_column(df, possible_names):
    normalized = {col.strip().lower(): col for col in df.columns}
    for name in possible_names:
        if name.strip().lower() in normalized:
            return normalized[name.strip().lower()]
    return None

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

def format_inr(value):
    try:
        return f"₹{float(value):,.0f}"
    except Exception:
        return f"₹{value}"

def clean_money_col(df, col):
    if col is None:
        return df
    df[col] = (df[col].astype(str)
               .str.replace("₹", "", regex=False)
               .str.replace(",", "", regex=False)
               .str.replace("%", "", regex=False)
               .str.strip())
    df[col] = safe_numeric(df[col])
    return df

# ── STYLING ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:linear-gradient(135deg,#f8fafc 0%,#eef2ff 100%);color:#111827;}
.block-container{padding-top:4rem;padding-bottom:1rem;}
.main-title{text-align:center;font-size:42px;font-weight:800;color:#111827;margin-bottom:6px;}
.sub-title{text-align:center;font-size:17px;color:#6b7280;margin-bottom:26px;}
.glass-card{background:rgba(255,255,255,0.82);backdrop-filter:blur(12px);
    border:1px solid rgba(255,255,255,0.45);border-radius:18px;padding:18px;
    box-shadow:0 10px 30px rgba(15,23,42,0.08);margin-bottom:16px;}
.metric-card{background:linear-gradient(135deg,#ffffff 0%,#f8fafc 100%);
    border:1px solid #e5e7eb;border-radius:18px;padding:22px 18px;text-align:center;
    box-shadow:0 10px 24px rgba(15,23,42,0.08);transition:all 0.25s ease;}
.metric-card:hover{transform:translateY(-4px);box-shadow:0 16px 30px rgba(15,23,42,0.12);}
.metric-label{font-size:14px;color:#6b7280;font-weight:600;margin-bottom:8px;}
.metric-value{font-size:30px;font-weight:800;color:#111827;}
.metric-sub{font-size:12px;color:#9ca3af;margin-top:8px;}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#111827 0%,#1f2937 100%);
    border-right:1px solid rgba(255,255,255,0.08);}
section[data-testid="stSidebar"] *{color:white !important;}
.stButton>button,.stDownloadButton>button{width:100%;
    background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);color:white;
    border:none;border-radius:12px;padding:0.6rem 1rem;font-weight:600;
    box-shadow:0 8px 18px rgba(79,70,229,0.25);}
.stButton>button:hover,.stDownloadButton>button:hover{
    background:linear-gradient(135deg,#4338ca 0%,#6d28d9 100%);color:white;}
div[data-testid="stFileUploader"]{background:rgba(255,255,255,0.75);padding:10px;
    border-radius:16px;border:1px dashed #cbd5e1;}
div[data-testid="stAlert"]{background-color:#fee2e2 !important;
    border-color:#cc0000 !important;color:#ffffff !important;}
</style>
""", unsafe_allow_html=True)

# ── LOADER ────────────────────────────────────────────────────────────────────
with st.spinner("🚀 Launching dashboard..."):
    time.sleep(0.6)

# ── SIDEBAR NAVIGATION ────────────────────────────────────────────────────────
st.sidebar.markdown("## 📂 Dashboard Control")
menu = st.sidebar.radio("Navigate", ["Overview", "Analysis", "Insights", "Data Preview"])
st.sidebar.markdown("---")
st.sidebar.caption("Upload a CSV to begin")

# ── TITLE ─────────────────────────────────────────────────────────────────────
st.markdown("<div class='main-title'>📊 Smart Business Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Beautiful, interactive dashboard for Sales & Product/Review datasets</div>",
            unsafe_allow_html=True)

# ── FILE UPLOAD ───────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file:
    # ── Safe CSV read ─────────────────────────────────────────────────────────
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read the CSV file: {e}")
        st.stop()

    if df.empty:
        st.error("The uploaded file is empty. Please upload a valid CSV.")
        st.stop()

    original_df = df.copy()
    df.columns = df.columns.str.strip()

    # ── AUTO-DETECT COLUMNS ───────────────────────────────────────────────────
    sales_col           = find_column(df, ["Sales","Revenue","Amount","Total","Total Sales","Sale Amount"])
    date_col            = find_column(df, ["Order Date","Date","Purchase Date","Invoice Date","Sales Date"])
    product_col         = find_column(df, ["Product Name","Product","Item","Item Name","product_name"])
    category_col        = find_column(df, ["Category","Segment","Type","category"])
    profit_col          = find_column(df, ["Profit","Margin","Net Profit"])
    location_col        = find_column(df, ["City","Region","State","Location"])
    rating_col          = find_column(df, ["Rating","rating"])
    rating_count_col    = find_column(df, ["rating_count","Rating Count","review_count","Review Count"])
    actual_price_col    = find_column(df, ["actual_price","Actual Price","Price","price"])
    discounted_price_col= find_column(df, ["discounted_price","Discounted Price","Sale Price"])
    discount_col        = find_column(df, ["discount_percentage","Discount Percentage","Discount %"])
    review_title_col    = find_column(df, ["review_title","Review Title"])
    review_content_col  = find_column(df, ["review_content","Review Content"])
    user_col            = find_column(df, ["user_name","User","Customer Name"])

    # ── DATASET TYPE ──────────────────────────────────────────────────────────
    is_sales_dataset   = sales_col is not None
    is_product_dataset = any(c is not None for c in [
        product_col, rating_col, actual_price_col, discounted_price_col, review_title_col
    ])

    # ── WARN if nothing detected ──────────────────────────────────────────────
    if not is_sales_dataset and not is_product_dataset:
        st.warning(
            "⚠️ We couldn't detect standard Sales or Product columns in this file. "
            "Some charts may be missing. Check the **Data Preview** tab to verify your column names."
        )

    # ── CLEAN NUMERIC COLUMNS ─────────────────────────────────────────────────
    for col in [sales_col, profit_col, rating_col, rating_count_col,
                actual_price_col, discounted_price_col]:
        df = clean_money_col(df, col)

    if discount_col:
        df[discount_col] = safe_numeric(
            df[discount_col].astype(str).str.replace("%","",regex=False).str.strip()
        )

    # ── PARSE DATES ───────────────────────────────────────────────────────────
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        valid_dates = df[date_col].notna().sum()
        if valid_dates == 0:
            st.warning(f"Column '{date_col}' was detected as a date column but no valid dates could be parsed.")
            date_col = None
        else:
            df = df.dropna(subset=[date_col])
            df["Month"] = df[date_col].dt.to_period("M").astype(str)

    # ── TOP INFO PANEL ────────────────────────────────────────────────────────
    top1, top2 = st.columns([3, 1])
    with top1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("**Detected CSV Columns**")
        st.code(list(df.columns))
        st.markdown("</div>", unsafe_allow_html=True)
    with top2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        dataset_label = (
            "Sales Dataset" if is_sales_dataset
            else "Product / Review Dataset" if is_product_dataset
            else "Generic CSV"
        )
        st.write("**Detected Type**")
        st.success(dataset_label)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── SIDEBAR FILTERS ───────────────────────────────────────────────────────
    if category_col:
        category_values = sorted(df[category_col].dropna().astype(str).unique())
        selected_categories = st.sidebar.multiselect(
            "Filter by Category", category_values,
            default=category_values[:10] if len(category_values) > 10 else category_values
        )
        if selected_categories:
            df = df[df[category_col].astype(str).isin(selected_categories)]
        if df.empty:
            st.warning("No data matches the selected filters.")
            st.stop()

    # ── EXPORT ────────────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 Export Options")
    report_lines = [
        "Smart Business Dashboard Report",
        f"Generated by : {st.session_state.get('username','N/A')}",
        f"Report Date  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Rows   : {len(df)}",
    ]
    if is_sales_dataset:
        report_lines.append(f"Total Sales  : {format_inr(df[sales_col].sum())}")
        if profit_col:
            report_lines.append(f"Total Profit : {format_inr(df[profit_col].sum())}")
    elif is_product_dataset and product_col:
        report_lines.append(f"Unique Products: {df[product_col].nunique()}")
    report_text = "\n".join(report_lines)

    st.sidebar.download_button("📄 Download Summary Report", data=report_text,
                               file_name="Summary_Report.txt")
    st.sidebar.caption("Hover any chart → click 📷 to export as PNG.")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button("📥 Raw Data", original_df.to_csv(index=False), "raw_data.csv")
    with d2:
        st.download_button("📥 Processed Data", df.to_csv(index=False), "processed_data.csv")

    # ══════════════════════════════════════════════════════════════════════════
    # OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    if menu == "Overview":
        st.subheader("✨ Key Metrics")
        c1, c2, c3, c4 = st.columns(4)

        if is_sales_dataset:
            total_sales  = df[sales_col].sum()
            avg_sales    = df[sales_col].mean()
            total_profit = df[profit_col].sum() if profit_col else 0
            total_orders = len(df)

            metrics = [
                ("Total Sales",    format_inr(total_sales),   "Overall revenue"),
                ("Average Sale",   format_inr(avg_sales),     "Per record"),
                ("Total Profit",   format_inr(total_profit),  "If available"),
                ("Orders",         f"{total_orders:,}",       "Total entries"),
            ]
            for col, (label, value, sub) in zip([c1,c2,c3,c4], metrics):
                with col:
                    st.markdown(f"""
                    <div class='metric-card'>
                        <div class='metric-label'>{label}</div>
                        <div class='metric-value'>{value}</div>
                        <div class='metric-sub'>{sub}</div>
                    </div>""", unsafe_allow_html=True)

        elif is_product_dataset:
            total_products      = df[product_col].nunique() if product_col else len(df)
            avg_rating          = df[rating_col].mean()          if rating_col          else 0
            avg_actual_price    = df[actual_price_col].mean()    if actual_price_col    else 0
            avg_discounted_price= df[discounted_price_col].mean()if discounted_price_col else 0

            metrics = [
                ("Products",         f"{int(total_products):,}", "Unique products"),
                ("Avg Rating",       f"{avg_rating:.2f}",        "Customer feedback"),
                ("Avg Actual Price", format_inr(avg_actual_price),"Original price"),
                ("Avg Disc. Price",  format_inr(avg_discounted_price),"After discount"),
            ]
            for col, (label, value, sub) in zip([c1,c2,c3,c4], metrics):
                with col:
                    st.markdown(f"""
                    <div class='metric-card'>
                        <div class='metric-label'>{label}</div>
                        <div class='metric-value'>{value}</div>
                        <div class='metric-sub'>{sub}</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Charts
        if is_sales_dataset and "Month" in df.columns:
            monthly = (df.groupby("Month")[sales_col].sum()
                       .reset_index().rename(columns={sales_col:"Sales"})
                       .sort_values("Month"))
            fig = px.line(monthly, x="Month", y="Sales", markers=True,
                          title="📈 Monthly Sales Trend", template="plotly_white")
            fig.update_xaxes(rangeslider_visible=True)
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)

        elif is_product_dataset:
            ch1, ch2 = st.columns(2)
            with ch1:
                if category_col and product_col:
                    cc = (df.groupby(category_col)[product_col].count()
                          .reset_index().rename(columns={product_col:"Count"})
                          .sort_values("Count", ascending=False).head(10))
                    fig = px.bar(cc, x=category_col, y="Count",
                                 title="📦 Top Categories by Product Count",
                                 template="plotly_white")
                    fig.update_layout(height=420)
                    st.plotly_chart(fig, use_container_width=True)
            with ch2:
                if rating_col:
                    fig2 = px.histogram(df, x=rating_col, nbins=20,
                                        title="⭐ Rating Distribution",
                                        template="plotly_white")
                    fig2.update_layout(height=420)
                    st.plotly_chart(fig2, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "Analysis":
        tab1, tab2, tab3 = st.tabs(["📊 Main Analysis", "📌 Category View", "🧾 Detailed Summary"])

        with tab1:
            left, right = st.columns(2)
            with left:
                if is_sales_dataset and product_col:
                    top = (df.groupby(product_col)[sales_col].sum()
                           .nlargest(10).reset_index()
                           .rename(columns={sales_col:"Sales"}))
                    fig = px.bar(top, x="Sales", y=product_col, orientation="h",
                                 title="Top Products by Sales", template="plotly_white")
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                elif is_product_dataset and actual_price_col and product_col:
                    tp = (df[[product_col, actual_price_col]].dropna()
                          .sort_values(actual_price_col, ascending=False).head(10))
                    fig = px.bar(tp, x=actual_price_col, y=product_col, orientation="h",
                                 title="Top Expensive Products", template="plotly_white")
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)

            with right:
                if category_col:
                    if is_sales_dataset:
                        cat = (df.groupby(category_col)[sales_col].sum()
                               .reset_index().rename(columns={sales_col:"Sales"}))
                        fig2 = px.pie(cat, names=category_col, values="Sales",
                                      title="Category-wise Sales Share",
                                      template="plotly_white")
                    elif is_product_dataset and product_col:
                        cat = (df.groupby(category_col)[product_col].count()
                               .reset_index().rename(columns={product_col:"Count"}))
                        fig2 = px.pie(cat, names=category_col, values="Count",
                                      title="Category-wise Product Share",
                                      template="plotly_white")
                    else:
                        fig2 = None
                    if fig2:
                        fig2.update_layout(height=500)
                        st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            if category_col:
                metric_col = (sales_col if is_sales_dataset
                              else rating_col if rating_col
                              else actual_price_col)
                if metric_col:
                    grouped = (df.groupby(category_col)[metric_col].mean()
                               .reset_index().sort_values(metric_col, ascending=False))
                    fig3 = px.bar(grouped.head(15), x=category_col, y=metric_col,
                                  title=f"Category-wise Average {metric_col}",
                                  template="plotly_white")
                    fig3.update_layout(height=450)
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.info("No numeric metric found for category view.")
            else:
                st.info("No category column found in this dataset.")

        with tab3:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Dataset Summary")
            try:
                st.dataframe(df.describe(include="all").T, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not generate summary: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # INSIGHTS  (data-driven, not hardcoded strings)
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "Insights":
        st.subheader("💡 Smart Insights")

        ib1, ib2 = st.columns(2)

        with ib1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Key Findings")

            if is_sales_dataset:
                # ── Profitability ──────────────────────────────────────────
                if profit_col:
                    total_profit = df[profit_col].sum()
                    total_sales  = df[sales_col].sum()
                    margin_pct   = (total_profit / total_sales * 100) if total_sales else 0

                    if total_profit > 0:
                        st.success(f"✅ Business is profitable — net margin **{margin_pct:.1f}%**.")
                    else:
                        st.error(f"❌ Business is running at a loss (margin: **{margin_pct:.1f}%**).")

                    # Identify loss-making categories
                    if category_col:
                        cat_profit = df.groupby(category_col)[profit_col].sum()
                        losing = cat_profit[cat_profit < 0]
                        if not losing.empty:
                            st.warning(
                                f"⚠️ Loss-making categories: **{', '.join(losing.index.tolist())}**"
                            )

                # ── Best & worst product ────────────────────────────────────
                if product_col:
                    prod_sales = df.groupby(product_col)[sales_col].sum()
                    best_prod  = prod_sales.idxmax()
                    worst_prod = prod_sales.idxmin()
                    st.info(f"🏆 Best selling product: **{best_prod}** ({format_inr(prod_sales.max())})")
                    st.info(f"📉 Lowest selling product: **{worst_prod}** ({format_inr(prod_sales.min())})")

                # ── Best category ──────────────────────────────────────────
                if category_col:
                    cat_sales  = df.groupby(category_col)[sales_col].sum()
                    best_cat   = cat_sales.idxmax()
                    worst_cat  = cat_sales.idxmin()
                    st.info(f"📦 Top category: **{best_cat}** ({format_inr(cat_sales.max())})")
                    st.info(f"📦 Weakest category: **{worst_cat}** ({format_inr(cat_sales.min())})")

                # ── Monthly growth rate ────────────────────────────────────
                if "Month" in df.columns:
                    monthly = (df.groupby("Month")[sales_col].sum()
                               .sort_index())
                    if len(monthly) >= 2:
                        first, last = monthly.iloc[0], monthly.iloc[-1]
                        growth = ((last - first) / first * 100) if first else 0
                        arrow  = "📈" if growth >= 0 else "📉"
                        st.info(f"{arrow} Sales growth (first→last month): **{growth:+.1f}%**")

            elif is_product_dataset:
                if product_col and rating_col:
                    prod_rating = df.groupby(product_col)[rating_col].mean()
                    best_rated  = prod_rating.idxmax()
                    worst_rated = prod_rating.idxmin()
                    st.info(f"⭐ Best rated product: **{best_rated}** ({prod_rating.max():.2f})")
                    st.info(f"⚠️ Lowest rated product: **{worst_rated}** ({prod_rating.min():.2f})")

                    # Flag products with low rating AND high rating count (visible problem)
                    if rating_count_col:
                        high_reviews = df[rating_count_col].quantile(0.75)
                        low_rating   = df[rating_col].quantile(0.25)
                        problem_prods = df[
                            (df[rating_col] <= low_rating) &
                            (df[rating_count_col] >= high_reviews)
                        ]
                        if not problem_prods.empty and product_col:
                            names = problem_prods[product_col].dropna().unique()[:3]
                            st.warning(
                                f"🚨 Highly-reviewed but poorly-rated products: **{', '.join(names)}**"
                            )

                if category_col and rating_col:
                    cat_rating = df.groupby(category_col)[rating_col].mean()
                    st.info(f"🏅 Best rated category: **{cat_rating.idxmax()}** ({cat_rating.max():.2f})")
                    st.info(f"📉 Worst rated category: **{cat_rating.idxmin()}** ({cat_rating.min():.2f})")

                if discount_col:
                    avg_disc = df[discount_col].mean()
                    max_disc = df[discount_col].max()
                    st.info(f"🏷️ Average discount: **{avg_disc:.1f}%** | Max discount: **{max_disc:.1f}%**")

                if actual_price_col and discounted_price_col:
                    df["_savings"] = df[actual_price_col] - df[discounted_price_col]
                    avg_savings    = df["_savings"].mean()
                    if avg_savings > 0:
                        st.info(f"💰 Customers save on average **{format_inr(avg_savings)}** per product.")

            else:
                st.write("Upload a Sales or Product CSV to see data-driven insights.")

            st.markdown("</div>", unsafe_allow_html=True)

        with ib2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Recommendations")

            if is_sales_dataset:
                if profit_col:
                    margin_pct = (df[profit_col].sum() / df[sales_col].sum() * 100) if df[sales_col].sum() else 0
                    if margin_pct < 10:
                        st.warning("⚠️ Profit margin below 10% — review pricing or cost structure.")
                    elif margin_pct < 20:
                        st.info("📌 Margin is moderate (10–20%). Explore upselling opportunities.")
                    else:
                        st.success("✅ Healthy margin above 20%. Focus on volume growth.")

                if product_col:
                    prod_sales    = df.groupby(product_col)[sales_col].sum()
                    bottom_20_pct = prod_sales.quantile(0.20)
                    low_products  = prod_sales[prod_sales <= bottom_20_pct]
                    st.info(f"🗂️ Consider reviewing/discontinuing **{len(low_products)}** underperforming product(s).")

                if "Month" in df.columns:
                    monthly = df.groupby("Month")[sales_col].sum().sort_index()
                    if len(monthly) >= 3:
                        recent_3  = monthly.iloc[-3:].mean()
                        earlier_3 = monthly.iloc[:3].mean() if len(monthly) >= 6 else monthly.iloc[:-3].mean()
                        if recent_3 < earlier_3:
                            st.warning("📉 Recent months are underperforming vs earlier period — investigate demand drivers.")
                        else:
                            st.success("📈 Recent months are trending upward — maintain momentum.")

            elif is_product_dataset:
                if rating_col:
                    low_rated  = df[df[rating_col] < 3.0]
                    high_rated = df[df[rating_col] >= 4.0]
                    st.info(f"🔴 **{len(low_rated)}** products rated below 3.0 — prioritise quality improvements.")
                    st.success(f"🟢 **{len(high_rated)}** products rated 4.0+ — promote these more aggressively.")

                if actual_price_col and discounted_price_col:
                    df["_disc_pct"] = ((df[actual_price_col] - df[discounted_price_col])
                                       / df[actual_price_col].replace(0, np.nan) * 100)
                    over_discounted = df[df["_disc_pct"] > 50]
                    if not over_discounted.empty:
                        st.warning(f"⚠️ **{len(over_discounted)}** products discounted >50% — "
                                   f"check if this is sustainable.")

                if discount_col:
                    avg_disc = df[discount_col].mean()
                    if avg_disc > 40:
                        st.warning("🏷️ Average discount exceeds 40% — may be eroding margins.")
                    else:
                        st.success("✅ Discount levels appear reasonable.")
            else:
                st.write("Clean and structure your dataset for better recommendations.")

            st.markdown("</div>", unsafe_allow_html=True)

        # ── SALES FORECAST ────────────────────────────────────────────────────
        if is_sales_dataset and date_col and "Month" in df.columns:
            monthly = (df.groupby(df[date_col].dt.to_period("M"))[sales_col].sum()
                       .reset_index().rename(columns={sales_col:"Sales"}))
            monthly[date_col] = monthly[date_col].astype(str)
            monthly = monthly.sort_values(date_col)

            if len(monthly) >= 3:
                monthly["Index"] = np.arange(len(monthly))
                model = LinearRegression()
                model.fit(monthly[["Index"]], monthly["Sales"])

                future_idx   = np.arange(len(monthly), len(monthly) + 6).reshape(-1, 1)
                future_sales = model.predict(future_idx)
                future_months= [f"Future+{i+1}" for i in range(6)]

                pred_df = pd.DataFrame({
                    "Month": list(monthly[date_col]) + future_months,
                    "Sales": list(monthly["Sales"]) + list(future_sales),
                   "Type" : ["Actual"] * len(monthly) + ["Predicted"] * 6
                })

                # Clamp negative predictions to 0
                pred_df["Sales"] = pred_df["Sales"].clip(lower=0)

                st.subheader("📈 Sales Forecast (Linear Trend)")
               

                fig = px.line(pred_df, x="Month", y="Sales", color="Type",
                              markers=True, template="plotly_white")
                fig.update_xaxes(rangeslider_visible=True)
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

                next_month = max(future_sales[0], 0)
                r2 = model.score(monthly[["Index"]], monthly["Sales"])
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    st.success(f"Predicted next-month sales: **{format_inr(next_month)}**")
            else:
                st.info("Need at least 3 months of data for forecasting.")

    # ══════════════════════════════════════════════════════════════════════════
    # DATA PREVIEW
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "Data Preview":
        st.subheader("🧾 Data Preview")
        pt1, pt2 = st.tabs(["First 20 Rows", "Column Info"])

        with pt1:
            st.dataframe(df.head(20), use_container_width=True)

        with pt2:
            info_df = pd.DataFrame({
                "Column":         df.columns,
                "Type":           [str(t) for t in df.dtypes],
                "Missing":        [df[c].isna().sum() for c in df.columns],
                "Missing %":      [f"{df[c].isna().mean()*100:.1f}%" for c in df.columns],
                "Unique Values":  [df[c].nunique() for c in df.columns],
                "Sample Value":   [df[c].dropna().iloc[0] if df[c].notna().any() else "N/A"
                                   for c in df.columns],
            })
            st.dataframe(info_df, use_container_width=True)

else:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.info("👆 Upload a CSV file to start exploring your dashboard.")
    st.markdown("</div>", unsafe_allow_html=True)