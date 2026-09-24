# Zepto Data & AI Platform — Capstone

This repository implements the three connected modules required by the Masai Certificate Program in Artificial Intelligence and Machine Learning capstone:

- `data_pipeline/` — scrape Books to Scrape, clean/convert data, load a normalized SQLite database, and demonstrate SQL + pandas.
- `analytics/` — load Titanic once through Seaborn (with the committed CSV fallback), profile/clean it, build the required EDA story, train/evaluate classifiers, compare imbalance handling, tune Random Forest, and run the fare-regression side task.
- `support_assistant/` — embed the eight supplied policy documents locally, retrieve with ChromaDB, route with LangGraph, return deterministic mock-mode responses, validate with Pydantic, and serve through FastAPI/Docker.

All required written interpretations live in Markdown in the repository. No paid service is required for the graded paths.

## Requirements

This repository uses one consolidated `requirements.txt` for the three modules.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Module 1 — Data pipeline

The required conversion rate is the fixed project baseline **1 GBP = 105.50 INR**. It is not a live FX rate and the implementation does not call a currency API.

Run:

```bash
cd data_pipeline
python pipeline.py
```

The script scrapes complete categories until it has at least 60 unique books across at least three categories, cleans the required fields, writes `zepto_catalog.db`, executes the required SQL queries, reads SQL results with `pd.read_sql`, reproduces the JOIN with `pd.merge`, and writes the executed query/output evidence to `outputs/sql_outputs.md`.

## Module 2 — Analytics

Run the two scripts in this order:

```bash
cd analytics
python 01_eda.py
python 02_modeling.py
```

`01_eda.py` makes the module's single `sns.load_dataset("titanic")` call when possible and immediately writes the resulting DataFrame to `analytics/titanic.csv`. If the network/cache load fails and the committed fallback exists, it reads that same fallback instead. `02_modeling.py` reads only `titanic.csv` and never calls Seaborn again.

The EDA stage reports `df.info()`, `df.describe()`, `df.shape`, missingness percentages for affected columns, threshold-based cleaning decisions, IQR outlier counts, fare mean/median/mode skewness evidence, all three required survival breakdowns, the exact six-column correlation matrix, the two strongest absolute off-diagonal correlations, four interpreted multivariate charts, and the age/fare standardization sanity check.

The modeling stage performs the stratified split before preprocessing, uses a train-fit-only `ColumnTransformer`/`Pipeline`, evaluates Logistic Regression, Decision Tree, and Random Forest on the same split, compares baseline/class-weight/SMOTE imbalance handling, tunes Random Forest with `GridSearchCV` while keeping `oob_score=True`, completes the fare regression task, writes the separate classification/regression metric groups, and saves the complete fitted classifier pipeline with `joblib.dump`.

## Module 3 — Support assistant

Build the local vector store and generate the required example transcript:

```bash
cd support_assistant
python ingest.py
python example_calls.py
```

`ingest.py` reads exactly the eight required policy files, creates one chunk per document, embeds them with `all-MiniLM-L6-v2`, and stores them in ChromaDB collection `zepto_policy` using cosine distance.

The graph in `main.py` contains `classify_intent`, `retrieve_and_answer`, and `direct_answer` with the required conditional edge. With `MOCK_LLM` unset/default, intent classification uses the specified keyword heuristic; policy queries still perform real local embedding + Chroma retrieval and return the required `Based on the retrieved context: ...` mock answer, while general questions return the required fixed canned response. The optional `MOCK_LLM=0` branch calls a real LLM and includes corrective retries for invalid structured output, but it is not required for grading.

Run the API with the graded default state:

```bash
uvicorn main:app --reload --port 7860
```

The exact raw JSON from the two required example calls is generated into `support_assistant/example_responses.json` and inserted into `support_assistant/README.md` by `example_calls.py`; this prevents hand-written or fabricated transcripts.

Build/run the required local Docker image from the repository root:

```bash
docker build -t zepto-support-assistant ./support_assistant
docker run --rm -p 7860:7860 zepto-support-assistant
```

## Architecture

```text
DATA PIPELINE
books.toscrape.com
      |
      v
requests + BeautifulSoup
      |
      v
clean/validate + GBP->INR (1 GBP = 105.50 INR)
      |
      v
SQLite categories <---- FK ---- books
      |
      +--> SQL queries --> pd.read_sql / pd.merge

ANALYTICS
sns.load_dataset('titanic') [single raw load when available]
      |
      v
analytics/titanic.csv [one committed fallback]
      |
      +--> EDA / cleaning / charts / correlations / standardization
      |
      v
stratified train/test split
      |
      v
ColumnTransformer (fit on train only)
      |
      +--> Logistic Regression
      +--> Decision Tree
      +--> Random Forest --> GridSearchCV + OOB
      |
      +--> SMOTE comparison on training data only
      +--> Linear Regression for fare

SUPPORT ASSISTANT
8 policy documents
      |
      v
chunking -> all-MiniLM-L6-v2 embeddings -> ChromaDB `zepto_policy`
                                                ^
                                                |
query -> LangGraph `classify_intent` ---- policy -+
                    |                               |
                    +---- general -> `direct_answer` 
                                                    v
                                      `retrieve_and_answer`
                                                    |
                                      Pydantic AnswerResponse
                                                    |
                                               FastAPI /ask
```

### `MOCK_LLM` boundary

The required mock path is the default (`MOCK_LLM` unset or `1`). In that state, classification is the exact keyword heuristic and final generation is deterministic; policy retrieval is still performed locally in ChromaDB. Only when `MOCK_LLM=0` are the optional real-LLM classification and answer-generation steps used. No API key or network service is required for the graded path.

## Git workflow requirement

Before the final push, the repository history must visibly show a feature branch that was created, received at least two commits, and was merged back into `main`. Verify locally with:

```bash
git log --graph --all --decorate --oneline
```

Then push the single repository to GitHub and submit exactly that one public repository link.

## Verification

Run the static check from the repository root:

```bash
python verify_project.py
```

The static check confirms the required source files, eight exact policy-document files, Dockerfile, requirements files, and committed Titanic fallback are present. The live-scrape, local embedding/Chroma, API, and Docker requirements are verified by running the module commands above in the submission environment.

## Final Verification

The required runtime checks were completed locally before submission. The Data Pipeline generated the required cleaned dataset, SQLite database, and SQL query/output evidence. The Support Assistant embedded all 8 policy documents and the required mock-mode examples returned HTTP 200 responses with the expected structured fields.
