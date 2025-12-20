import os
import shutil
import duckdb
import kagglehub

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
OUTDIR = "./dataset"
os.makedirs(OUTDIR, exist_ok=True)

metadata_path = f"{OUTDIR}/metadata.csv"
reviews_path = f"{OUTDIR}/reviews.csv"
clean_reviews_path = f"{OUTDIR}/books_reviews_clean.csv"
top_authors_path = f"{OUTDIR}/top_authors_data.csv"
top_books_path = f"{OUTDIR}/top_books_data.csv"
top_publishers_path = f"{OUTDIR}/top_publishers_data.csv"

# ------------------------------------------------------------
# Download Kaggle datasets (SAFE & VERSION-PROOF)
# ------------------------------------------------------------
if not os.path.exists(metadata_path) or not os.path.exists(reviews_path):
    dataset_dir = kagglehub.dataset_download(
        "hadifariborzi/amazon-books-dataset-20k-books-727k-reviews"
    )

    shutil.copy(
        os.path.join(dataset_dir, "amazon_books_metadata_sample_20k.csv"),
        metadata_path,
    )
    shutil.copy(
        os.path.join(dataset_dir, "amazon_books_reviews_sample_20k.csv"),
        reviews_path,
    )

if (
    not os.path.exists(clean_reviews_path)
    or not os.path.exists(top_authors_path)
    or not os.path.exists(top_books_path)
    or not os.path.exists(top_publishers_path)
):
    clean_reviews_dir = kagglehub.dataset_download("tobypu/book-reviews-clean")
    shutil.copy(
        os.path.join(clean_reviews_dir, "books_reviews_clean.csv"),
        clean_reviews_path,
    )
    shutil.copy(
        os.path.join(clean_reviews_dir, "top_authors_data.csv"),
        top_authors_path,
    )
    shutil.copy(
        os.path.join(clean_reviews_dir, "top_books_data.csv"),
        top_books_path,
    )
    shutil.copy(
        os.path.join(clean_reviews_dir, "top_publishers_data.csv"),
        top_publishers_path,
    )

# ------------------------------------------------------------
# DuckDB connection (LOW MEMORY SETTINGS)
# ------------------------------------------------------------
con = duckdb.connect()
con.execute("PRAGMA threads=2")
con.execute("PRAGMA memory_limit='1GB'")

# ------------------------------------------------------------
# Load CSVs DIRECTLY into DuckDB (NO PANDAS)
# ------------------------------------------------------------
con.execute(f"""
    CREATE OR REPLACE TABLE books_metadata AS
    SELECT * FROM read_csv_auto('{metadata_path}')
""")

con.execute(f"""
    CREATE OR REPLACE TABLE books_reviews AS
    SELECT * FROM read_csv_auto('{reviews_path}')
""")

# ------------------------------------------------------------
# Process metadata
# ------------------------------------------------------------
con.execute("""
    CREATE OR REPLACE TABLE processed_metadata AS
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

con.execute(f"""
    COPY processed_metadata
    TO '{OUTDIR}/processed_metadata.csv'
    (HEADER, DELIMITER ',')
""")

# ------------------------------------------------------------
# Scorecard data
# ------------------------------------------------------------
con.execute("""
    CREATE OR REPLACE TABLE scorecard_data AS
    WITH base AS (
        SELECT
            year(m.published_date) AS year,
            m.parent_asin,
            m.price_numeric,
            r.asin,
            r.rating
        FROM processed_metadata m
        LEFT JOIN books_reviews r USING (parent_asin)
        WHERE m.published_date IS NOT NULL
    )
    SELECT
        year,
        count(DISTINCT parent_asin) AS total_books,
        count(asin) AS total_reviews,
        sum(rating * price_numeric) AS total_sales
    FROM base
    GROUP BY year
    ORDER BY year
""")

con.execute(f"""
    COPY scorecard_data
    TO '{OUTDIR}/scorecard_data.csv'
    (HEADER, DELIMITER ',')
""")

# ------------------------------------------------------------
# Genre data
# ------------------------------------------------------------
con.execute("""
    CREATE OR REPLACE TABLE genre_data AS
    WITH base AS (
        SELECT
            year(m.published_date) AS year,
            m.category_level_3_detail AS genre,
            m.parent_asin,
            m.price_numeric,
            r.asin,
            r.rating
        FROM processed_metadata m
        LEFT JOIN books_reviews r USING (parent_asin)
        WHERE m.published_date IS NOT NULL
          AND m.category_level_3_detail IS NOT NULL
    )
    SELECT
        year,
        genre,
        count(DISTINCT parent_asin) AS book_count,
        count(asin) AS review_count,
        sum(rating * price_numeric) AS total_sales
    FROM base
    GROUP BY year, genre
    ORDER BY year, book_count DESC
""")

con.execute(f"""
    COPY genre_data
    TO '{OUTDIR}/genre_data.csv'
    (HEADER, DELIMITER ',')
""")

# ------------------------------------------------------------
# Done
# ------------------------------------------------------------
rows = con.execute("SELECT COUNT(*) FROM processed_metadata").fetchone()[0]

print("Data processing complete!")
print(f"Processed metadata rows: {rows}")

con.close()
