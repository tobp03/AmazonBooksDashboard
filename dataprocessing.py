import os
import shutil
import pandas as pd
import duckdb
import kagglehub
from kagglehub import KaggleDatasetAdapter

# ------------------------------------------------------------
# DuckDB helper
# ------------------------------------------------------------
def query(sql: str) -> pd.DataFrame:
    return duckdb.sql(sql).df()

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
OUTDIR = "./dataset"
os.makedirs(OUTDIR, exist_ok=True)

metadata_path = f"{OUTDIR}/metadata.csv"
reviews_path = f"{OUTDIR}/reviews.csv"
clean_reviews_path = f"{OUTDIR}/books_reviews_clean.csv"

# ------------------------------------------------------------
# Download Kaggle datasets (CORRECT for this KaggleHub version)
# ------------------------------------------------------------
if not os.path.exists(metadata_path) or not os.path.exists(reviews_path):

    books_metadata = kagglehub.dataset_load(
        "hadifariborzi/amazon-books-dataset-20k-books-727k-reviews",
        "amazon_books_metadata_sample_20k.csv",
        KaggleDatasetAdapter.PANDAS,
    )

    books_reviews = kagglehub.dataset_load(
        "hadifariborzi/amazon-books-dataset-20k-books-727k-reviews",
        "amazon_books_reviews_sample_20k.csv",
        KaggleDatasetAdapter.PANDAS,
    )

    books_metadata.to_csv(metadata_path, index=False)
    books_reviews.to_csv(reviews_path, index=False)

# ------------------------------------------------------------
# Download cleaned reviews dataset
# ------------------------------------------------------------
if not os.path.exists(clean_reviews_path):
    clean_reviews_dir = kagglehub.dataset_download("tobypu/book-reviews-clean")
    shutil.copy(
        os.path.join(clean_reviews_dir, "books_reviews_clean.csv"),
        clean_reviews_path,
    )

# ------------------------------------------------------------
# Load CSVs
# ------------------------------------------------------------
books_metadata = pd.read_csv(metadata_path)
books_reviews = pd.read_csv(reviews_path)
books_reviews_clean = pd.read_csv(clean_reviews_path)

# Register DataFrames with DuckDB
duckdb.register("books_metadata", books_metadata)
duckdb.register("books_reviews", books_reviews)

# ------------------------------------------------------------
# Process metadata
# ------------------------------------------------------------
processed_metadata = query("""
    WITH p1 AS (
        SELECT
            * EXCLUDE (publisher_date),
            CASE
                WHEN publisher_date IS NOT NULL
                     AND strpos(publisher_date, '(') > 0
                THEN trim(both ')' FROM split(publisher_date, '(')[-1])
                ELSE NULL
            END AS date_str
        FROM books_metadata
    )
    SELECT
        *,
        try_strptime(date_str, '%B %d, %Y') AS published_date
    FROM p1
""")

processed_metadata.to_csv(f"{OUTDIR}/processed_metadata.csv", index=False)
duckdb.register("processed_metadata", processed_metadata)

# ------------------------------------------------------------
# Scorecard data
# ------------------------------------------------------------
scorecard_data = query("""
    SELECT
        year(m.published_date) AS year,
        count(DISTINCT m.parent_asin) AS total_books,
        count(r.asin) AS total_reviews,
        sum(r.rating * m.price_numeric) AS total_sales
    FROM processed_metadata m
    LEFT JOIN books_reviews r USING (parent_asin)
    WHERE m.published_date IS NOT NULL
    GROUP BY year
    ORDER BY year
""")

scorecard_data.to_csv(f"{OUTDIR}/scorecard_data.csv", index=False)

# ------------------------------------------------------------
# Genre data
# ------------------------------------------------------------
genre_data = query("""
    SELECT
        year(m.published_date) AS year,
        m.category_level_3_detail AS genre,
        count(DISTINCT m.parent_asin) AS book_count,
        count(r.asin) AS review_count,
        sum(r.rating * m.price_numeric) AS total_sales
    FROM processed_metadata m
    LEFT JOIN books_reviews r USING (parent_asin)
    WHERE m.published_date IS NOT NULL
      AND m.category_level_3_detail IS NOT NULL
    GROUP BY year, genre
    ORDER BY year, book_count DESC
""")

genre_data.to_csv(f"{OUTDIR}/genre_data.csv", index=False)

# ------------------------------------------------------------
# Done
# ------------------------------------------------------------
print("Data processing complete!")
print(f"Processed metadata rows: {len(processed_metadata)}")
print(scorecard_data)
