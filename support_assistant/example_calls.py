from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

ROOT = Path(__file__).parent
OUT = ROOT / "example_responses.json"
README = ROOT / "README.md"
BEGIN = "<!-- BEGIN GENERATED EXAMPLE RESPONSES -->"
END = "<!-- END GENERATED EXAMPLE RESPONSES -->"


def update_readme(results: list[dict]) -> None:
    """Record the actual local /ask JSON responses inside the module README."""
    transcript_parts = [BEGIN, "", "These responses were generated locally with `MOCK_LLM` left at its default value.", ""]
    for item in results:
        transcript_parts.extend(
            [
                f"### `{item['name']}` — `{item['query']}`",
                "",
                f"HTTP status: `{item['status_code']}`",
                "",
                "```json",
                json.dumps(item["response"], indent=2),
                "```",
                "",
            ]
        )
    transcript_parts.append(END)
    generated = "\n".join(transcript_parts)

    current = README.read_text(encoding="utf-8")
    if BEGIN in current and END in current:
        before = current.split(BEGIN, 1)[0]
        after = current.split(END, 1)[1]
        updated = before + generated + after
    else:
        updated = current.rstrip() + "\n\n" + generated + "\n"
    README.write_text(updated, encoding="utf-8")


def main() -> None:
    client = TestClient(app)
    requests = [
        {"name": "policy_question", "query": "What is the delivery policy?"},
        {"name": "general_question", "query": "What is the capital of India?"},
    ]

    results = []
    for item in requests:
        response = client.post("/ask", json={"query": item["query"]})
        response.raise_for_status()
        results.append(
            {
                **item,
                "status_code": response.status_code,
                "response": response.json(),
            }
        )

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    update_readme(results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
