from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://books.toscrape.com/"
TARGET_BOOKS = 60
MIN_CATEGORIES = 3
GBP_TO_INR = 105.50
ROOT = Path(__file__).parent
OUT_DIR = ROOT / "outputs"
DB_PATH = ROOT / "zepto_catalog.db"

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
HEADERS = {"User-Agent": "Mozilla/5.0 Zepto-Capstone/1.0"}


def build_http_session() -> requests.Session:
    """Create a small retrying HTTP session for transient public-site failures."""
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


SESSION = build_http_session()


def get_soup(url: str) -> BeautifulSoup:
    """Fetch and parse one public Books to Scrape page with bounded retries."""
    try:
        response = SESSION.get(url, timeout=(10, 45))
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Unable to fetch {url!r} after bounded retries: {exc}") from exc
    # Parse raw bytes so BeautifulSoup/UnicodeDammit can detect the page encoding
    # instead of inheriting a misleading response encoding that can turn ``£``
    # into ``Â£``. The downstream price parser also tolerates that legacy variant.
    return BeautifulSoup(response.content, "html.parser")


def parse_category_links() -> list[tuple[str, str]]:
    """Return unique book-category listing links from the catalogue page."""
    soup = get_soup(BASE_URL)
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.select("ul.nav-list ul li a"):
        name = anchor.get_text(strip=True)
        href = anchor.get("href")
        if not name or not href:
            continue
        url = urljoin(BASE_URL, href)
        if url not in seen:
            seen.add(url)
            links.append((name, url))
    return links


def parse_book_page(article, category: str) -> dict:
    """Extract the raw fields required by the assignment from one product card."""
    title_node = article.select_one("h3 a")
    price_node = article.select_one(".price_color")
    rating_node = article.select_one(".star-rating")
    availability_node = article.select_one(".availability")

    if not all((title_node, price_node, rating_node, availability_node)):
        raise ValueError("Book card is missing one or more required fields.")

    rating_classes = rating_node.get("class", [])
    rating_text = next((value for value in rating_classes if value in RATING_MAP), "")

    return {
        "title": title_node.get("title", "").strip(),
        "price": price_node.get_text(strip=True),
        "star_rating": rating_text,
        "availability": availability_node.get_text(" ", strip=True),
        "category": category,
    }


def scrape_category(category: str, url: str, rows: list[dict]) -> int:
    """Scrape every listing page in one category; return rows added."""
    next_url = url
    visited: set[str] = set()
    added = 0

    while next_url and next_url not in visited:
        visited.add(next_url)
        soup = get_soup(next_url)
        for article in soup.select("article.product_pod"):
            try:
                rows.append(parse_book_page(article, category))
                added += 1
            except (AttributeError, TypeError, ValueError) as exc:
                # A malformed product card is skipped rather than crashing the full scrape.
                print(f"Skipping malformed book card in {category!r}: {exc}")

        next_link = soup.select_one("li.next a")
        next_url = urljoin(next_url, next_link["href"]) if next_link and next_link.get("href") else None

    return added


def parse_in_stock(value: object) -> object:
    """Parse the site's stock text into True/False; return pd.NA for an unexpected value."""
    text = re.sub(r"\s+", " ", str(value)).strip().lower()
    if text == "":
        return pd.NA
    if "out of stock" in text:
        return False
    if "in stock" in text:
        return True
    return pd.NA


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Clean raw scrape fields; median-impute numeric parse failures and drop invalid rows."""
    df = raw.copy()
    dropped: dict[str, int] = {}

    # Numeric fields: parse failures become NaN, then use the column median as required.
    # Books to Scrape can be served with an encoding that renders the pound sign as
    # "Â£" in the decoded text. Extract the numeric GBP value explicitly so that
    # either representation (or ordinary currency whitespace) parses correctly.
    def parse_price_gbp(value: object) -> float | None:
        text = str(value).replace("\xa0", " ").strip()
        # Normalize the common UTF-8/Latin-1 display variant ``Â£`` to ``£``.
        text = re.sub(r"\s+", " ", text).replace("Â£", "£")
        match = re.fullmatch(r"£\s*(\d+(?:\.\d+)?)", text)
        return float(match.group(1)) if match else None

    df["price_gbp"] = df["price"].map(parse_price_gbp).astype("float64")
    df["rating"] = df["star_rating"].map(RATING_MAP).astype("float64")
    for col in ["price_gbp", "rating"]:
        missing = int(df[col].isna().sum())
        if missing:
            median = df[col].median()
            if pd.isna(median):
                raise ValueError(f"Cannot median-impute {col!r}: every value failed to parse.")
            df[col] = df[col].fillna(median)
            dropped[f"{col}_median_imputed"] = missing

    # Availability: an unrecognized status is a parsing failure, so drop that row.
    df["in_stock"] = df["availability"].map(parse_in_stock)
    invalid_stock = int(df["in_stock"].isna().sum())
    if invalid_stock:
        df = df.dropna(subset=["in_stock"])
        dropped["invalid_availability_rows_dropped"] = invalid_stock

    # Identity fields cannot be safely imputed.
    invalid_identity = int(df[["title", "category"]].isna().any(axis=1).sum())
    if invalid_identity:
        df = df.dropna(subset=["title", "category"])
        dropped["invalid_identity_rows_dropped"] = invalid_identity

    # Enforce the required final dtypes.
    df["rating"] = df["rating"].round().astype(int)
    df["in_stock"] = df["in_stock"].astype(bool)
    df["price_inr"] = (df["price_gbp"] * GBP_TO_INR).round(2)

    return df[["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]], dropped


def load_sqlite(df: pd.DataFrame) -> None:
    """Recreate the normalized SQLite schema and load the cleaned records."""
    with sqlite3.connect(DB_PATH) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(
            """
            DROP TABLE IF EXISTS books;
            DROP TABLE IF EXISTS categories;
            CREATE TABLE categories (
                category_id INTEGER PRIMARY KEY,
                category_name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE books (
                book_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                price_gbp REAL NOT NULL,
                price_inr REAL NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                in_stock INTEGER NOT NULL CHECK (in_stock IN (0, 1)),
                category_id INTEGER NOT NULL REFERENCES categories(category_id)
            );
            """
        )

        categories = pd.DataFrame({"category_name": sorted(df["category"].unique())})
        categories.to_sql("categories", con, if_exists="append", index=False)

        mapping = pd.read_sql("SELECT category_id, category_name FROM categories", con)
        books = df.merge(mapping, left_on="category", right_on="category_name", how="left", validate="many_to_one")
        books = books[["title", "price_gbp", "price_inr", "rating", "in_stock", "category_id"]].copy()
        if books["category_id"].isna().any():
            raise RuntimeError("Category foreign-key mapping failed during SQLite load.")
        books["in_stock"] = books["in_stock"].astype(int)
        books["category_id"] = books["category_id"].astype(int)
        books.to_sql("books", con, if_exists="append", index=False)


def run_queries() -> None:
    """Execute and save all required SQL and pandas evidence."""
    queries = [
        ("1. SELECT/WHERE", "SELECT title, price_gbp, rating FROM books WHERE rating >= 4 ORDER BY rating DESC;"),
        ("2. ORDER BY", "SELECT title, price_inr FROM books ORDER BY price_inr DESC LIMIT 10;"),
        ("3. LIMIT", "SELECT title, rating FROM books LIMIT 5;"),
        ("4. DISTINCT", "SELECT DISTINCT category_name FROM categories ORDER BY category_name;"),
        ("5. IN", "SELECT title, category_id FROM books WHERE category_id IN (1, 2, 3) ORDER BY category_id, title LIMIT 15;"),
        ("6. JOIN", "SELECT c.category_name, b.title, b.rating, b.price_inr FROM books b JOIN categories c ON b.category_id = c.category_id ORDER BY b.rating DESC, c.category_name, b.title LIMIT 10;"),
    ]

    OUT_DIR.mkdir(exist_ok=True)
    lines = [
        "# SQL Query Evidence",
        "",
        f"Fixed conversion rate: **1 GBP = {GBP_TO_INR:.2f} INR**",
        "",
    ]

    with sqlite3.connect(DB_PATH) as con:
        for label, query in queries:
            result = pd.read_sql(query, con)
            lines += [f"## {label}", "", "```sql", query, "```", "", result.to_markdown(index=False), ""]

        # At least two SQL results are read through pandas, and the JOIN is reproduced without SQL.
        sql_read_a = pd.read_sql(queries[0][1], con)
        sql_join = pd.read_sql(queries[-1][1], con)
        books_df = pd.read_sql("SELECT * FROM books", con)
        categories_df = pd.read_sql("SELECT * FROM categories", con)
        merge_join = books_df.merge(categories_df, on="category_id", how="inner")
        merge_join = (
            merge_join[["category_name", "title", "rating", "price_inr"]]
            .sort_values(["rating", "category_name", "title"], ascending=[False, True, True])
            .head(10)
            .reset_index(drop=True)
        )
        sql_join_norm = sql_join.reset_index(drop=True)

        lines += [
            "## pandas equivalence check",
            "",
            "### `pd.read_sql(...)` JOIN result",
            sql_join_norm.to_markdown(index=False),
            "",
            "### `pd.merge(...)` JOIN result",
            merge_join.to_markdown(index=False),
            "",
            f"**Equivalent:** `{sql_join_norm.equals(merge_join)}`",
            "",
            "### Second `pd.read_sql(...)` result",
            sql_read_a.head(10).to_markdown(index=False),
            "",
        ]

    (OUT_DIR / "sql_outputs.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    category_links = parse_category_links()
    if not category_links:
        raise RuntimeError("No book categories were found on Books to Scrape.")

    rows: list[dict] = []
    categories_scraped = 0
    for category, url in category_links:
        scrape_category(category, url, rows)
        categories_scraped += 1
        unique_rows = pd.DataFrame(rows).drop_duplicates(subset=["title", "category"]) if rows else pd.DataFrame()
        if categories_scraped >= MIN_CATEGORIES and len(unique_rows) >= TARGET_BOOKS:
            break

    raw = pd.DataFrame(rows).drop_duplicates(subset=["title", "category"]).reset_index(drop=True)
    category_count = int(raw["category"].nunique()) if not raw.empty else 0
    if len(raw) < TARGET_BOOKS or category_count < MIN_CATEGORIES:
        raise RuntimeError(
            f"Scrape completed with {len(raw)} rows across {category_count} categories; "
            f"need >= {TARGET_BOOKS} rows and >= {MIN_CATEGORIES} categories."
        )

    cleaned, cleaning_stats = clean_data(raw)
    if len(cleaned) < TARGET_BOOKS or cleaned["category"].nunique() < MIN_CATEGORIES:
        raise RuntimeError("Cleaning reduced the dataset below the required 60 rows / 3 categories threshold.")

    OUT_DIR.mkdir(exist_ok=True)
    cleaned.to_csv(OUT_DIR / "cleaned_books.csv", index=False)
    load_sqlite(cleaned)
    run_queries()

    print(f"Scraped {len(raw)} raw books across {category_count} categories.")
    print(f"Cleaned dataset: {len(cleaned)} rows across {cleaned['category'].nunique()} categories.")
    print(f"Cleaning actions: {cleaning_stats or 'none'}")
    print(f"SQLite database: {DB_PATH}")
    print(f"SQL evidence: {OUT_DIR / 'sql_outputs.md'}")


if __name__ == "__main__":
    main()
