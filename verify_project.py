from pathlib import Path

ROOT = Path(__file__).parent
required = [
    "README.md", "requirements.txt",
    "data_pipeline/pipeline.py", "data_pipeline/README.md",
    "analytics/01_eda.py", "analytics/02_modeling.py", "analytics/titanic.csv",
    "support_assistant/ingest.py", "support_assistant/main.py", "support_assistant/prompt.py",
    "support_assistant/example_calls.py", "support_assistant/Dockerfile", "support_assistant/requirements.txt",
    *[f"support_assistant/docs/doc_{i:02d}.txt" for i in range(1, 9)],
]
missing = [p for p in required if not (ROOT / p).exists()]
if missing:
    raise SystemExit("Missing required files:\n" + "\n".join(missing))

print(f"Static project verification passed: {len(required)} required files found.")

# Runtime evidence is deliberately checked separately because the live scrape and local
# embedding steps require the user's network/model environment. No fake evidence is accepted.
runtime_files = [
    "data_pipeline/outputs/cleaned_books.csv",
    "data_pipeline/outputs/sql_outputs.md",
    "support_assistant/example_responses.json",
]
missing_runtime = [p for p in runtime_files if not (ROOT / p).exists()]
if missing_runtime:
    print("Runtime evidence still to generate:")
    for p in missing_runtime:
        print(f"  - {p}")
else:
    sql_text = (ROOT / "data_pipeline/outputs/sql_outputs.md").read_text(encoding="utf-8")
    readme_text = (ROOT / "support_assistant/README.md").read_text(encoding="utf-8")
    sql_ok = "**Equivalent:** `True`" in sql_text
    examples_ok = "Not generated yet." not in readme_text and "BEGIN GENERATED EXAMPLE RESPONSES" in readme_text
    if not sql_ok:
        raise SystemExit("SQL evidence exists but the pd.read_sql/pd.merge equivalence check is not True.")
    if not examples_ok:
        raise SystemExit("Support Assistant README does not contain generated example responses.")
    print("Runtime evidence verification passed: SQL equivalence and Support Assistant examples are present.")

print("Git workflow must still be verified on the real repository with:")
print("git log --graph --all --decorate --oneline")
