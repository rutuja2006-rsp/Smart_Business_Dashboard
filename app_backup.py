import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from sklearn.linear_model import LinearRegression
import time
import sqlite3
import hashlib
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Smart Business Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- DB & AUTH HELPERS ----------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    username TEXT UNIQUE,
                    password TEXT,
                    last_login TEXT)''')
    conn.commit()
    conn.close()

init_db()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_userdata(company_name, username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('INSERT INTO users(company_name, username, password, last_login) VALUES (?,?,?,?)', 
              (company_name, username, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def login_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    data = c.fetchall()
    if data:
        c.execute('UPDATE users SET last_login = ? WHERE username = ?', 
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
        conn.commit()
    conn.close()
    return data

# ---------------- AUTHENTICATION ----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

if not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align: center; color: #111827;'>Welcome to Smart Business Dashboard</h1>", unsafe_allow_html=True)
    menu_auth = st.sidebar.selectbox("Login / Sign Up", ["Login", "Sign Up"])
    if menu_auth == "Login":
        st.subheader("Login Section")
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')
        if st.button("Login"):
            hashed_pswd = make_hashes(password)
            result = login_user(username, hashed_pswd)
            if result:
                st.success(f"Logged In as {username}")
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.warning("Incorrect Username/Password")

    elif menu_auth == "Sign Up":
        st.subheader("Create New Account")
        new_company = st.text_input("Company Name")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')
        if st.button("Signup"):
            try:
                add_userdata(new_company, new_user, make_hashes(new_password))
                st.success("You have successfully created a valid Account")
                st.info("Go to Login Menu to login")
            except sqlite3.IntegrityError:
                st.error("Username already exists. Please choose a different one.")
    st.stop()

# Show User Logout
st.sidebar.markdown(f"**👤 User:** {st.session_state['username']}")
st.sidebar.button("Logout", on_click=lambda: st.session_state.update(logged_in=False, username=""))

# ---------------- HELPERS ----------------
def find_column(df, possible_names):
    normalized = {col.strip().lower(): col for col in df.columns}
    for name in possible_names:
        key = name.strip().lower()
        if key in normalized:
            return normalized[key]
    return None


def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def format_inr(value):
    try:
        return f"₹{value:,.0f}"
    except Exception:
        return f"₹{value}"


# ---------------- STYLING ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
    color: #111827;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
}

.main-title {
    text-align: center;
    font-size: 42px;
    font-weight: 800;
    color: #111827;
    margin-bottom: 6px;
}

.sub-title {
    text-align: center;
    font-size: 17px;
    color: #6b7280;
    margin-bottom: 26px;
}

.glass-card {
    background: rgba(255,255,255,0.82);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.45);
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    margin-bottom: 16px;
}

.metric-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 22px 18px;
    text-align: center;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    transition: all 0.25s ease;
}

.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 30px rgba(15, 23, 42, 0.12);
}

.metric-label {
    font-size: 14px;
    color: #6b7280;
    font-weight: 600;
    margin-bottom: 8px;
}

.metric-value {
    font-size: 30px;
    font-weight: 800;
    color: #111827;
}

.metric-sub {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 8px;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827 0%, #1f2937 100%);
    border-right: 1px solid rgba(255,255,255,0.08);
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

.stButton > button, .stDownloadButton > button {
    width: 100%;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 0.6rem 1rem;
    font-weight: 600;
    box-shadow: 0 8px 18px rgba(79, 70, 229, 0.25);
}

.stButton > button:hover, .stDownloadButton > button:hover {
    background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%);
    color: white;
}

div[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.75);
    padding: 10px;
    border-radius: 16px;
    border: 1px dashed #cbd5e1;
}

hr {
    margin-top: 0.8rem !important;
    margin-bottom: 0.8rem !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- LOADER ----------------
with st.spinner("🚀 Launching dashboard..."):
    time.sleep(0.8)

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("## 📂 Dashboard Control")
menu = st.sidebar.radio(
    "Navigate",
    ["Overview", "Analysis", "Insights", "Data Preview"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Upload a CSV to begin")

# ---------------- TITLE ----------------
st.markdown("<div class='main-title'>📊 Smart Business Dashboard</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Beautiful, interactive dashboard for Sales datasets and Product/Review datasets</div>",
    unsafe_allow_html=True
)

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    original_df = df.copy()
    df.columns = df.columns.str.strip()

    # ---------------- AUTO DETECT COLUMNS ----------------
    sales_col = find_column(df, ["Sales", "Revenue", "Amount", "Total", "Total Sales", "Sale Amount"])
    date_col = find_column(df, ["Order Date", "Date", "Purchase Date", "Invoice Date", "Sales Date"])
    product_col = find_column(df, ["Product Name", "Product", "Item", "Item Name", "product_name"])
    category_col = find_column(df, ["Category", "Segment", "Type", "category"])
    profit_col = find_column(df, ["Profit", "Margin", "Net Profit"])
    location_col = find_column(df, ["City", "Region", "State", "Location"])
    rating_col = find_column(df, ["Rating", "rating"])
    rating_count_col = find_column(df, ["rating_count", "Rating Count", "review_count", "Review Count"])
    actual_price_col = find_column(df, ["actual_price", "Actual Price", "Price", "price"])
    discounted_price_col = find_column(df, ["discounted_price", "Discounted Price", "Sale Price"])
    discount_col = find_column(df, ["discount_percentage", "Discount Percentage", "Discount %"])
    review_title_col = find_column(df, ["review_title", "Review Title"])
    review_content_col = find_column(df, ["review_content", "Review Content"])
    user_col = find_column(df, ["user_name", "User", "Customer Name"])

    # ---------------- DATASET TYPE ----------------
    is_sales_dataset = sales_col is not None
    is_product_dataset = any(col is not None for col in [
        product_col, rating_col, actual_price_col, discounted_price_col, review_title_col
    ])

    # ---------------- CLEAN IMPORTANT COLUMNS ----------------
    numeric_candidates = [
        sales_col, profit_col, rating_col, rating_count_col,
        actual_price_col, discounted_price_col
    ]

    for col in numeric_candidates:
        if col:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("₹", "", regex=False)
                .str.replace(",", "", regex=False)
                .str.replace("%", "", regex=False)
                .str.strip()
            )
            df[col] = safe_numeric(df[col])

    if discount_col:
        df[discount_col] = (
            df[discount_col]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.strip()
        )
        df[discount_col] = safe_numeric(df[discount_col])

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        if df[date_col].notna().sum() > 0:
            df = df.dropna(subset=[date_col])
            df["Month"] = df[date_col].dt.to_period("M").astype(str)

    # ---------------- TOP PANEL ----------------
    top1, top2 = st.columns([3, 1])
    with top1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("**Detected CSV Columns**")
        st.code(list(df.columns))
        st.markdown("</div>", unsafe_allow_html=True)

    with top2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        dataset_name = "Sales Dataset" if is_sales_dataset else "Product / Review Dataset" if is_product_dataset else "Generic CSV"
        st.write("**Detected Type**")
        st.success(dataset_name)
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- FILTERS ----------------
    if category_col:
        category_values = sorted(df[category_col].dropna().astype(str).unique())
        selected_categories = st.sidebar.multiselect(
            "Filter by Category",
            category_values,
            default=category_values[:10] if len(category_values) > 10 else category_values
        )
        if selected_categories:
            df = df[df[category_col].astype(str).isin(selected_categories)]

    # ---------------- EXPORT & DOWNLOAD ----------------
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 Export Options")
    
    report_text = f"Smart Business Dashboard Report\n" \
                  f"Generated by: {st.session_state.get('username', 'N/A')}\n" \
                  f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                  f"Total Rows: {len(df)}\n"
    if is_sales_dataset:
        report_text += f"Total Sales: {format_inr(df[sales_col].sum())}\n"
    elif is_product_dataset and product_col:
        report_text += f"Total Unique Products: {df[product_col].nunique()}\n"
        
    st.sidebar.download_button("📄 Download Summary Report", data=report_text, file_name="Summary_Report.txt")
    st.sidebar.caption("Tip: Hover over any graph and click the camera icon (📷) to export it as a PNG image.")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button("📥 Download Raw Data", original_df.to_csv(index=False), "raw_data.csv")
    with d2:
        st.download_button("📥 Download Processed Data", df.to_csv(index=False), "processed_data.csv")

    # =====================================================
    # OVERVIEW
    # =====================================================
    if menu == "Overview":
        st.subheader("✨ Key Metrics")

        c1, c2, c3, c4 = st.columns(4)

        if is_sales_dataset:
            total_sales = df[sales_col].sum()
            avg_sales = df[sales_col].mean()
            total_profit = df[profit_col].sum() if profit_col else 0
            total_orders = len(df)

            with c1:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Total Sales</div>
                    <div class='metric-value'>{format_inr(total_sales)}</div>
                    <div class='metric-sub'>Overall revenue</div>
                </div>
                """, unsafe_allow_html=True)

            with c2:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Average Sales</div>
                    <div class='metric-value'>{format_inr(avg_sales)}</div>
                    <div class='metric-sub'>Per record average</div>
                </div>
                """, unsafe_allow_html=True)

            with c3:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Total Profit</div>
                    <div class='metric-value'>{format_inr(total_profit)}</div>
                    <div class='metric-sub'>If available</div>
                </div>
                """, unsafe_allow_html=True)

            with c4:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Orders</div>
                    <div class='metric-value'>{total_orders:,}</div>
                    <div class='metric-sub'>Total entries</div>
                </div>
                """, unsafe_allow_html=True)

        elif is_product_dataset:
            total_products = df[product_col].nunique() if product_col else len(df)
            avg_rating = df[rating_col].mean() if rating_col else 0
            avg_actual_price = df[actual_price_col].mean() if actual_price_col else 0
            avg_discounted_price = df[discounted_price_col].mean() if discounted_price_col else 0

            with c1:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Products</div>
                    <div class='metric-value'>{int(total_products):,}</div>
                    <div class='metric-sub'>Unique products</div>
                </div>
                """, unsafe_allow_html=True)

            with c2:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Average Rating</div>
                    <div class='metric-value'>{avg_rating:.2f}</div>
                    <div class='metric-sub'>Customer feedback</div>
                </div>
                """, unsafe_allow_html=True)

            with c3:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Avg Actual Price</div>
                    <div class='metric-value'>{format_inr(avg_actual_price)}</div>
                    <div class='metric-sub'>Original price</div>
                </div>
                """, unsafe_allow_html=True)

            with c4:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Avg Discounted Price</div>
                    <div class='metric-value'>{format_inr(avg_discounted_price)}</div>
                    <div class='metric-sub'>After discount</div>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.warning("This CSV is not recognized as a sales or product dataset.")

        st.markdown("---")

        # -------- CHARTS --------
        if is_sales_dataset and "Month" in df.columns:
            monthly = df.groupby("Month")[sales_col].sum().reset_index()
            monthly = monthly.rename(columns={sales_col: "Sales"})
            monthly = monthly.sort_values("Month")

            fig = px.line(
                monthly,
                x="Month",
                y="Sales",
                markers=True,
                title="📈 Monthly Sales Trend",
                template="plotly_white"
            )
            fig.update_xaxes(rangeslider_visible=True)
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)

        elif is_product_dataset:
            chart1, chart2 = st.columns(2)

            with chart1:
                if category_col and product_col:
                    cat_counts = df.groupby(category_col)[product_col].count().reset_index()
                    cat_counts = cat_counts.rename(columns={product_col: "Count"})
                    fig = px.bar(
                        cat_counts.sort_values("Count", ascending=False).head(10),
                        x=category_col,
                        y="Count",
                        title="📦 Top Categories by Product Count",
                        template="plotly_white"
                    )
                    fig.update_layout(height=420)
                    st.plotly_chart(fig, use_container_width=True)

            with chart2:
                if rating_col:
                    fig2 = px.histogram(
                        df,
                        x=rating_col,
                        nbins=20,
                        title="⭐ Rating Distribution",
                        template="plotly_white"
                    )
                    fig2.update_layout(height=420)
                    st.plotly_chart(fig2, use_container_width=True)

    # =====================================================
    # ANALYSIS
    # =====================================================
    elif menu == "Analysis":
        tab1, tab2, tab3 = st.tabs(["📊 Main Analysis", "📌 Category View", "🧾 Detailed Summary"])

        with tab1:
            left, right = st.columns(2)

            with left:
                if is_sales_dataset and product_col:
                    top = df.groupby(product_col)[sales_col].sum().nlargest(10).reset_index()
                    top = top.rename(columns={sales_col: "Sales"})
                    fig = px.bar(
                        top,
                        x="Sales",
                        y=product_col,
                        orientation="h",
                        title="Top Products by Sales",
                        template="plotly_white"
                    )
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)

                elif is_product_dataset and actual_price_col and product_col:
                    top_price = df[[product_col, actual_price_col]].dropna().sort_values(actual_price_col, ascending=False).head(10)
                    fig = px.bar(
                        top_price,
                        x=actual_price_col,
                        y=product_col,
                        orientation="h",
                        title="Top Expensive Products",
                        template="plotly_white"
                    )
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)

            with right:
                if category_col:
                    if is_sales_dataset:
                        cat = df.groupby(category_col)[sales_col].sum().reset_index()
                        cat = cat.rename(columns={sales_col: "Sales"})
                        fig2 = px.pie(
                            cat,
                            names=category_col,
                            values="Sales",
                            title="Category-wise Sales Share",
                            template="plotly_white"
                        )
                        fig2.update_layout(height=500)
                        st.plotly_chart(fig2, use_container_width=True)
                    elif is_product_dataset and product_col:
                        cat = df.groupby(category_col)[product_col].count().reset_index()
                        cat = cat.rename(columns={product_col: "Count"})
                        fig2 = px.pie(
                            cat,
                            names=category_col,
                            values="Count",
                            title="Category-wise Product Share",
                            template="plotly_white"
                        )
                        fig2.update_layout(height=500)
                        st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            if category_col:
                group_cols = [category_col]
                metric_col = sales_col if is_sales_dataset else rating_col if rating_col else actual_price_col

                if metric_col:
                    grouped = df.groupby(category_col)[metric_col].mean().reset_index()
                    grouped = grouped.sort_values(metric_col, ascending=False)

                    fig3 = px.bar(
                        grouped.head(15),
                        x=category_col,
                        y=metric_col,
                        title=f"Category-wise Average {metric_col}",
                        template="plotly_white"
                    )
                    fig3.update_layout(height=450)
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.info("No numeric metric found for category view.")
            else:
                st.info("No category column found.")

        with tab3:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Dataset Summary")
            st.dataframe(df.describe(include="all").T, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================
    # INSIGHTS
    # =====================================================
    elif menu == "Insights":
        st.subheader("💡 Smart Insights")

        insight_box1, insight_box2 = st.columns(2)

        with insight_box1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Key Findings")

            if is_sales_dataset:
                if profit_col:
                    if df[profit_col].mean() > 0:
                        st.success("Business is profitable overall.")
                    else:
                        st.error("Business is currently running at loss.")

                if product_col:
                    best = df.groupby(product_col)[sales_col].sum().idxmax()
                    st.info(f"Best selling product: **{best}**")

                if category_col:
                    best_cat = df.groupby(category_col)[sales_col].sum().idxmax()
                    st.info(f"Top category by sales: **{best_cat}**")

            elif is_product_dataset:
                if product_col and rating_col:
                    best_rated = df.groupby(product_col)[rating_col].mean().idxmax()
                    st.info(f"Top rated product: **{best_rated}**")

                if category_col and rating_col:
                    best_cat = df.groupby(category_col)[rating_col].mean().idxmax()
                    st.info(f"Best rated category: **{best_cat}**")

                if discount_col:
                    st.info(f"Average discount: **{df[discount_col].mean():.2f}%**")

            st.markdown("</div>", unsafe_allow_html=True)

        with insight_box2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Recommendation")

            if is_sales_dataset:
                st.write("- Focus on top-performing categories and products.")
                st.write("- Monitor monthly trend for demand changes.")
                st.write("- Improve low-performing locations or products.")

            elif is_product_dataset:
                st.write("- Promote high-rated products more aggressively.")
                st.write("- Optimize pricing using actual vs discounted price.")
                st.write("- Improve product quality in low-rated categories.")

            else:
                st.write("- Clean and structure your dataset for better analysis.")
            st.markdown("</div>", unsafe_allow_html=True)

        # -------- FORECAST ONLY FOR SALES --------
        if is_sales_dataset and date_col and len(df) > 1 and "Month" in df.columns:
            monthly = df.groupby(df[date_col].dt.to_period("M"))[sales_col].sum().reset_index()
            monthly = monthly.rename(columns={sales_col: "Sales"})
            monthly[date_col] = monthly[date_col].astype(str)
            monthly = monthly.sort_values(date_col)

            if len(monthly) >= 2:
                monthly["Index"] = np.arange(len(monthly))
                model = LinearRegression()
                model.fit(monthly[["Index"]], monthly["Sales"])

                future_index = np.arange(len(monthly), len(monthly) + 6).reshape(-1, 1)
                future_sales = model.predict(future_index)
                future_months = [f"Future-{i+1}" for i in range(6)]

                pred_df = pd.DataFrame({
                    "Month": list(monthly[date_col]) + future_months,
                    "Sales": list(monthly["Sales"]) + list(future_sales),
                    "Type": ["Actual"] * len(monthly) + ["Predicted"] * 6
                })

                st.subheader("📈 Sales Forecast")
                fig = px.line(
                    pred_df,
                    x="Month",
                    y="Sales",
                    color="Type",
                    markers=True,
                    template="plotly_white"
                )
                fig.update_xaxes(rangeslider_visible=True)
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

                st.success(f"Predicted next month sales: {format_inr(future_sales[0])}")

    # =====================================================
    # DATA PREVIEW
    # =====================================================
    elif menu == "Data Preview":
        st.subheader("🧾 Uploaded Data Preview")

        preview_tab1, preview_tab2 = st.tabs(["First 20 Rows", "Column Info"])

        with preview_tab1:
            st.dataframe(df.head(20), use_container_width=True)

        with preview_tab2:
            info_df = pd.DataFrame({
                "Column Name": df.columns,
                "Data Type": [str(dtype) for dtype in df.dtypes],
                "Missing Values": [df[col].isna().sum() for col in df.columns]
            })
            st.dataframe(info_df, use_container_width=True)

else:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.info("👆 Upload a CSV file to start exploring your dashboard.")
    st.markdown("</div>", unsafe_allow_html=True)