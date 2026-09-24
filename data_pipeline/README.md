# Module 1 — Data Pipeline

## Design decisions

- Scraping uses `requests` + `BeautifulSoup` directly against Books to Scrape.
- The script completes whole book categories, continuing until the dataset contains at least 60 unique books across at least 3 categories. It does not stop halfway through a category once the threshold is reached.
- `price_gbp` is parsed as `float`; `rating` maps One–Five to 1–5; `in_stock` parses the listed availability text into a boolean. Unexpected availability text is treated as a parse failure and that row is dropped, as required.
- The scraper parses raw HTML bytes to avoid a common currency-encoding issue where the pound sign can appear as `Â£`; the price parser normalizes that representation before numeric conversion.
- Numeric parsing failures in `price_gbp` and `rating` are median-imputed. Empty/unrecoverable identity fields (`title` or `category`) are dropped. The script reports any such cleaning actions when it runs rather than allowing the pipeline to crash on an isolated messy row.
- `price_inr = price_gbp * 105.50` exactly follows the assignment's fixed baseline: **1 GBP = 105.50 INR**. No live currency API is used.
- SQLite is normalized into `categories` and `books`, with `categories.category_id` referenced by `books.category_id` and foreign-key enforcement enabled.
- Six SQL queries are executed and saved with their outputs in `outputs/sql_outputs.md`; the evidence also includes two `pd.read_sql(...)` results and an equivalent JOIN reproduced through `pd.merge(...)` without SQL.

## Run

```bash
python pipeline.py
```

The run must complete from the public Books to Scrape site in a network-enabled environment. It generates `outputs/cleaned_books.csv`, `zepto_catalog.db`, and `outputs/sql_outputs.md` from scratch.
