"""
Streamlit interface for the scraped books.

Run (in this folder, after scrape_books.py has created books.db):
    streamlit run app.py
The app opens in the browser at http://localhost:8501
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).with_name("books.db")

st.set_page_config(page_title="Books to Scrape", page_icon="📚", layout="wide")
st.title("📚 Books to Scrape")
st.caption("Books collected from books.toscrape.com and stored in a local SQLite database.")


@st.cache_data
def load_books(db_modified_time):
    """Read the books table. Cached until books.db changes (new scrape)."""
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM books ORDER BY title", conn)


if not DB_PATH.exists():
    st.warning("No database yet. Run `python scrape_books.py` in this folder first, then reload this page.")
    st.stop()

books = load_books(DB_PATH.stat().st_mtime)
if books.empty:
    st.warning("The database is empty. Run `python scrape_books.py` first.")
    st.stop()

# ---------------------------------------------------------------- filters (sidebar)
with st.sidebar:
    st.header("Filter")
    search = st.text_input("Search in title", placeholder="e.g. light")
    categories = st.multiselect("Category", sorted(books["category"].dropna().unique()))
    min_rating = st.slider("Minimum rating (stars)", 1, 5, 1)
    low, high = float(books["price_incl_tax"].min()), float(books["price_incl_tax"].max())
    price_range = st.slider("Price (£)", low, high, (low, high)) if low < high else (low, high)
    in_stock_only = st.checkbox("Only books in stock")
    sort_by = st.selectbox("Sort by", ["Title", "Price ↑", "Price ↓", "Rating ↓"])

filtered = books[
    books["title"].str.contains(search, case=False, regex=False)
    & (books["rating"] >= min_rating)
    & books["price_incl_tax"].between(*price_range)
]
if categories:
    filtered = filtered[filtered["category"].isin(categories)]
if in_stock_only:
    filtered = filtered[filtered["availability"] > 0]

sort_options = {
    "Title": ("title", True),
    "Price ↑": ("price_incl_tax", True),
    "Price ↓": ("price_incl_tax", False),
    "Rating ↓": ("rating", False),
}
column, ascending = sort_options[sort_by]
filtered = filtered.sort_values(column, ascending=ascending)

# ---------------------------------------------------------------- key figures
c1, c2, c3, c4 = st.columns(4)
c1.metric("Books shown", f"{len(filtered)} / {len(books)}")
c2.metric("Average price", f"£{filtered['price_incl_tax'].mean():.2f}" if len(filtered) else "–")
c3.metric("Average rating", f"{filtered['rating'].mean():.1f} ★" if len(filtered) else "–")
c4.metric("Categories", filtered["category"].nunique())

# ---------------------------------------------------------------- tabs
tab_table, tab_details, tab_charts = st.tabs(["📋 Table", "🔎 Book details", "📊 Charts"])

with tab_table:
    st.dataframe(
        filtered[["image_url", "title", "category", "price_incl_tax", "rating", "availability", "product_url"]],
        column_config={
            "image_url": st.column_config.ImageColumn("Cover", width="small"),
            "title": st.column_config.TextColumn("Title", width="large"),
            "category": "Category",
            "price_incl_tax": st.column_config.NumberColumn("Price", format="£%.2f"),
            "rating": st.column_config.NumberColumn("Rating", format="%d ★"),
            "availability": st.column_config.NumberColumn("In stock"),
            "product_url": st.column_config.LinkColumn("Link", display_text="open ↗"),
        },
        hide_index=True,
        use_container_width=True,
        height=560,
    )
    st.download_button(
        "Download as CSV", filtered.to_csv(index=False).encode("utf-8"), "books.csv", "text/csv"
    )

with tab_details:
    if filtered.empty:
        st.info("No book matches the filters.")
    else:
        title = st.selectbox("Choose a book", filtered["title"])
        book = filtered[filtered["title"] == title].iloc[0]
        left, right = st.columns([1, 3])
        with left:
            if book["image_url"]:
                st.image(book["image_url"], use_container_width=True)
        with right:
            st.subheader(book["title"])
            st.write(f"**Category:** {book['category']}  ·  **Rating:** {'★' * int(book['rating'] or 0)}")
            st.write(
                f"**Price:** £{book['price_incl_tax']:.2f} (excl. tax £{book['price_excl_tax']:.2f})  ·  "
                f"**In stock:** {book['availability']}  ·  **UPC:** `{book['upc']}`"
            )
            st.write(book["description"] or "_No description._")
            st.link_button("Open on books.toscrape.com", book["product_url"])

with tab_charts:
    if filtered.empty:
        st.info("No book matches the filters.")
    else:
        left, right = st.columns(2)
        with left:
            st.markdown("**Books per category**")
            st.bar_chart(filtered["category"].value_counts().head(15), horizontal=True)
        with right:
            st.markdown("**Books per star rating**")
            st.bar_chart(filtered["rating"].value_counts().sort_index())
        st.markdown("**Average price per category (£)**")
        st.bar_chart(filtered.groupby("category")["price_incl_tax"].mean().sort_values(ascending=False).head(15))

st.caption(f"Data last scraped: {books['scraped_at'].max()} (UTC)")
