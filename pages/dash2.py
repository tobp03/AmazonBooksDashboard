import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import os
import numpy as np
import plotly.graph_objects as go

# ===========================================
# PAGE CONFIG
# ===========================================
st.set_page_config(page_title="Book Reviews Dashboard", layout="wide")

st.markdown("""
<style>
/* Hide the entire sidebar including Pages navigation */
section[data-testid="stSidebar"] {
    display: none !important;
}

/* Also hide the page navigation items */
section[data-testid="stSidebarNav"] {
    display: none !important;
}

/* Expand main content to full width */
div[data-testid="stAppViewContainer"] {
    margin-left: 0 !important;
}

div[data-testid="stToolbar"] {
    right: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ===========================================
# GLOBAL STYLES (DARK ROYAL BLUE THEME)
# ===========================================
st.markdown(
    """
<style>
/* Overall page background + app background */
.stApp {
    background-color: #0a1128;
}

/* Main app container */
section.main > div {
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
}

/* Use centered fixed width, reduce top padding */
.block-container {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-top: 0.5rem !important;
    max-width: 1400px !important;
}

/* Dashboard wrapper */
.dashboard-wrapper {
    background: #020617;
    border-radius: 18px;
    padding: 16px 20px 24px 20px;
    margin: 8px auto 30px auto;
    box-shadow: 0 18px 40px rgba(0,0,0,0.55);
    border: 1px solid #1e293b;
}

/* Titles */
h1, h2, h3, h4, h5 {
    color: #e5e7eb !important;
}

/* Generic text */
p, label, span, .stText, .stMarkdown {
    color: #e5e7eb !important;
}

/* Filter card */
.filter-card {
    background: #020617;
    border-radius: 12px;
    padding: 10px 12px 6px 12px;
    border: 1px solid #1e293b;
}

/* ================================
   FIXED HEIGHT REVIEW CARD
   Matched to Wordcloud height
   ================================ */
.review-card-tall {
    background: #020617;
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid #1e293b;

    height: 430px; /* <<< MATCHES WORDCLOUD HEIGHT */
    display: flex;
    flex-direction: column;
    font-size: 0.90rem;
}

.review-card-header {
    font-weight: 600;
    margin-bottom: 4px;
}

.review-card-meta {
    font-size: 0.80rem;
    margin-bottom: 4px;
    color: #cbd5f5;
}

.review-card-body {
    flex: 1;
    overflow-y: auto;
    padding-right: 6px;
    font-style: italic;
}

/* Slim scrollbars */
.review-card-body::-webkit-scrollbar {
    width: 6px;
}
.review-card-body::-webkit-scrollbar-track {
    background: #020617;
}
.review-card-body::-webkit-scrollbar-thumb {
    background: #1e293b;
    border-radius: 3px;
}

/* Section labels */
.section-label {
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 4px;
    color: #cbd5f5;
}
</style>
""",
    unsafe_allow_html=True,
)

# Wrap whole app
st.markdown('<div class="dashboard-wrapper">', unsafe_allow_html=True)

# ===========================================
# DIRECTORY
# ===========================================
# os.chdir("./dataset")

# ===========================================
# LOAD DATA
# ===========================================
@st.cache_data
def load_data():
    df = pd.read_csv("./dataset/books_reviews_clean.csv")
    df = df.copy()
    df = df.rename(columns={"category_level_3_detail": "category"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

books_reviews = load_data()

# ===========================================
# BANNED WORD LIST
# ===========================================
author_words = set(
    w.lower()
    for full_name in books_reviews["author_name"].dropna().unique()
    for w in full_name.split()
)
extra_banned = {"book", "one"}
BANNED_WORDS = author_words.union(extra_banned)

def filter_words(text):
    return " ".join([w for w in text.split() if w.lower() not in BANNED_WORDS])

# ===========================================
# TOP — CLEAN TITLE ONLY (NO BOXES)
# ===========================================
st.markdown("""
### Amazon Books Author Insights Dashboard
""")

# Remove subtitle completely (you asked for this)

st.markdown("<br>", unsafe_allow_html=True)


# ===========================================
# FILTERS IN ONE CLEAN ROW (NO DARK BOXES)
# ===========================================

# Prepare filtered base
base = books_reviews.copy()

# Define 3 columns for the filters
col_a, col_b, col_c = st.columns([1, 1, 2])

# --- Filter by Author ---
with col_a:
    authors_available = sorted(base["author_name"].dropna().unique().tolist())
    author_filter = st.multiselect("Filter by author", authors_available)
    df_after_author = base[base["author_name"].isin(author_filter)] if author_filter else base

# --- Filter by Category ---
with col_b:
    categories_available = sorted(df_after_author["category"].dropna().unique().tolist())
    category_filter = st.multiselect("Filter by category", categories_available)
    df_after_category = df_after_author[df_after_author["category"].isin(category_filter)] if category_filter else df_after_author

# --- Date Range Slider (FULL WIDTH of col_c) ---
with col_c:
    min_date = df_after_category["date"].min()
    max_date = df_after_category["date"].max()

    if pd.isna(min_date) or pd.isna(max_date):
        date_range = None
        st.warning("No valid dates available.")
    else:
        date_range = st.slider(
            "Date range",
            min_value=min_date.to_pydatetime(),
            max_value=max_date.to_pydatetime(),
            value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
            key="date_slider",
        )

# ===========================================
# APPLY FILTERS
# ===========================================
df_filtered = df_after_category.copy()

if date_range:
    df_filtered = df_filtered[
        (df_filtered["date"] >= date_range[0]) &
        (df_filtered["date"] <= date_range[1])
    ]

# Sampling info stays here, but now full-width
if len(df_filtered) > 10000:
    st.warning(f"Filtered dataset has {len(df_filtered)} rows — using 10,000-row sample.")
    df_filtered = df_filtered.sample(10000, random_state=42)

st.markdown("<br>", unsafe_allow_html=True)

# ===========================================
# WORDCLOUD FUNCTION
# ===========================================
def generate_wordcloud(text_data, colormap):
    text_data = [filter_words(str(t)) for t in text_data if pd.notna(t)]
    full_text = " ".join(text_data)
    if not full_text.strip():
        return None

    return WordCloud(
        width=1600, height=800,
        background_color="white",
        colormap=colormap,
        max_words=200,
        collocations=False,
        prefer_horizontal=1.0,
    ).generate(full_text)

# Sentiment subsets
negative_df = df_filtered[df_filtered["sentiment_rating"] == 0]
positive_df = df_filtered[df_filtered["sentiment_rating"] == 2]

# Most helpful reviews
most_helpful_neg = negative_df.sort_values("helpful_vote", ascending=False).head(1)
most_helpful_pos = positive_df.sort_values("helpful_vote", ascending=False).head(1)

neg_author = most_helpful_neg["author_name"].values[0] if not most_helpful_neg.empty else ""
neg_votes  = most_helpful_neg["helpful_vote"].values[0] if not most_helpful_neg.empty else ""
neg_text   = most_helpful_neg["text"].values[0] if not most_helpful_neg.empty else "No negative review available."

pos_author = most_helpful_pos["author_name"].values[0] if not most_helpful_pos.empty else ""
pos_votes  = most_helpful_pos["helpful_vote"].values[0] if not most_helpful_pos.empty else ""
pos_text   = most_helpful_pos["text"].values[0] if not most_helpful_pos.empty else "No positive review available."

# ===========================================
# FIXED-HEIGHT REVIEW CARD RENDER FUNCTION
# ===========================================
def render_review_card(title, author, votes, text, accent_color):
    st.markdown(
        f"""
        <div class="review-card-tall" style="border-left: 4px solid {accent_color};">
            <div class="review-card-header">{title}</div>
            <div class="review-card-meta"><strong>Author:</strong> {author}</div>
            <div class="review-card-meta"><strong>Helpful votes:</strong> {votes}</div>
            <div class="review-card-body">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ROW 2 — NETWORK GRAPH (UPDATED)
st.markdown('<div class="section-label">Author–Books Network Graph</div>', unsafe_allow_html=True)

try:
    with open("./dataset/Author_to_Books.html", "r", encoding="utf-8") as f:
        graph_html = f.read()
    st.components.v1.html(graph_html, height=600, scrolling=True)
except FileNotFoundError:
    st.error("❌ Author_to_Books.html not found.")



# ===========================================
# ROW 3 — POSITIVE CLOUD + CARD
# ===========================================
st.markdown("<br>", unsafe_allow_html=True)

pos_col_wc, pos_col_card = st.columns([1.6, 1.0])

with pos_col_wc:
    st.markdown('<div class="section-label">Positive Sentiment Word Cloud</div>', unsafe_allow_html=True)
    pos_wc = generate_wordcloud(positive_df["clean_text"].tolist(), "Greens")
    if pos_wc:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.imshow(pos_wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("No positive reviews found.")

with pos_col_card:
    st.markdown('<div class="section-label">Most Praised Review</div>', unsafe_allow_html=True)
    render_review_card("Most Praised Review", pos_author, pos_votes, pos_text, "#22c55e")

st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

# ===========================================
# ROW 4 — NEGATIVE CLOUD + CARD
# ===========================================
neg_col_wc, neg_col_card = st.columns([1.6, 1.0])

with neg_col_wc:
    st.markdown('<div class="section-label">Negative Sentiment Word Cloud</div>', unsafe_allow_html=True)
    neg_wc = generate_wordcloud(negative_df["clean_text"].tolist(), "Reds")
    if neg_wc:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.imshow(neg_wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("No negative reviews found.")

with neg_col_card:
    st.markdown('<div class="section-label">Most Critical Review</div>', unsafe_allow_html=True)
    render_review_card("Most Critical Review", neg_author, neg_votes, neg_text, "#ef4444")

# ===========================================
# ROW 5 — PIE + TREND
# ===========================================
bottom_col1, bottom_col2 = st.columns(2)

with bottom_col1:
    st.markdown('<div class="section-label">Sentiment Distribution</div>', unsafe_allow_html=True)
    sentiment_counts = df_filtered["sentiment_rating"].value_counts().reindex([0,1,2], fill_value=0)
    labels = ["Negative", "Neutral", "Positive"]
    values = sentiment_counts.values
    colors = ["#ef4444", "#6b7280", "#22c55e"]

    fig_pie = go.Figure(
        data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.58,
            marker=dict(colors=colors),
            textinfo="label+percent",
        )]
    )
    fig_pie.update_layout(
        showlegend=False,
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#020617",
        plot_bgcolor="#020617",
        font=dict(color="#e5e7eb"),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with bottom_col2:
    st.markdown('<div class="section-label">Sentiment Trend Over Time</div>', unsafe_allow_html=True)

    df_time = df_filtered.dropna(subset=["date"]).copy()
    if df_time.empty:
        st.info("No data with valid dates.")
    else:
        df_time["is_positive"] = (df_time["sentiment_rating"] == 2).astype(int)
        df_time["is_negative"] = (df_time["sentiment_rating"] == 0).astype(int)
        monthly = df_time.set_index("date").resample("M").sum()

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=monthly.index, y=monthly["is_positive"],
            mode="lines", name="Positive",
            line=dict(color="#22c55e", width=2.5),
        ))
        fig_trend.add_trace(go.Scatter(
            x=monthly.index, y=monthly["is_negative"],
            mode="lines", name="Negative",
            line=dict(color="#ef4444", width=2.5),
        ))
        fig_trend.update_layout(
            template="plotly_dark",
            height=260,
            hovermode="x unified",
            xaxis_title="Date", yaxis_title="Number of Reviews",
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="#020617",
            plot_bgcolor="#020617",
            font=dict(color="#e5e7eb"),
            legend=dict(orientation="h", y=1.02, x=1),
        )
        st.plotly_chart(fig_trend, use_container_width=True)



if st.button("Back to Main Dashboard"):
    st.switch_page("dash1.py")


# Close wrapper
st.markdown("</div>", unsafe_allow_html=True)
