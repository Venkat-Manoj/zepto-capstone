from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, TypedDict

import chromadb
import requests
from fastapi import FastAPI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sentence_transformers import SentenceTransformer

from prompt import INTENT_PROMPT, STRUCTURED_PROMPT

ROOT = Path(__file__).parent
DB = ROOT / "chroma_db"
COLLECTION_NAME = "zepto_policy"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
KEYWORDS = (
    "delivery",
    "return",
    "refund",
    "membership",
    "tracking",
    "cancel",
    "gift card",
    "support hours",
)

app = FastAPI(title="Zepto Policy Support Assistant")
model = SentenceTransformer(MODEL_NAME)
client = chromadb.PersistentClient(path=str(DB))
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1)


class AnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    sources: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class IntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Literal["policy_question", "general_question"]


class GraphState(TypedDict, total=False):
    query: str
    intent: Literal["policy_question", "general_question"]
    answer: str
    sources: list[str]
    confidence: float
    retrieved_texts: list[str]
    retrieved_ids: list[str]


def mock_mode() -> bool:
    """MOCK_LLM unset or 1 is the required graded baseline; only explicit 0 enables real LLM calls."""
    return os.getenv("MOCK_LLM", "1") != "0"


def call_groq_json(messages: list[dict[str, str]]) -> dict:
    """Optional real-LLM helper used only when MOCK_LLM=0."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required when MOCK_LLM=0")

    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON response must be an object.")
    return parsed


def classify_with_real_llm(query: str) -> Literal["policy_question", "general_question"]:
    """Optional MOCK_LLM=0 intent classifier, with up to 3 total attempts."""
    base_prompt = INTENT_PROMPT.format(query=query)
    messages = [{"role": "user", "content": base_prompt}]
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            payload = call_groq_json(messages)
            intent = IntentResponse.model_validate(payload).intent
            return intent
        except (requests.RequestException, KeyError, json.JSONDecodeError, ValidationError, ValueError, RuntimeError) as exc:
            last_error = exc
            messages = [
                {"role": "user", "content": base_prompt},
                {
                    "role": "user",
                    "content": f"Corrective instruction: the prior output was invalid ({exc}). Return only valid JSON {{\"intent\":\"policy_question\"}} or {{\"intent\":\"general_question\"}}.",
                },
            ]

    raise RuntimeError(f"Intent classification failed after 3 attempts: {last_error}")


def classify_intent(state: GraphState) -> GraphState:
    """Route policy-style queries using the exact required keyword heuristic in mock mode."""
    query = state["query"]
    if mock_mode():
        lowered = query.lower()
        intent: Literal["policy_question", "general_question"] = (
            "policy_question" if any(keyword in lowered for keyword in KEYWORDS) else "general_question"
        )
    else:
        intent = classify_with_real_llm(query)
    return {"intent": intent}


def retrieve_top3(query: str) -> tuple[list[str], list[str]]:
    """Embed the query and retrieve the top three Chroma chunks using cosine similarity."""
    count = collection.count()
    if count == 0:
        raise RuntimeError("ChromaDB collection is empty. Run `python ingest.py` before starting the API.")

    n_results = min(3, count)
    embedding = model.encode([query], normalize_embeddings=True).tolist()
    result = collection.query(
        query_embeddings=embedding,
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    documents = result.get("documents", [[]])[0]
    ids = result.get("ids", [[]])[0]
    return ids, documents


def call_real_llm(prompt: str, allowed_source_ids: set[str] | None = None) -> AnswerResponse:
    """Optional real-LLM answer generation with three total validation attempts."""
    messages = [{"role": "user", "content": prompt}]
    last_error: Exception | None = None

    for _ in range(3):
        try:
            payload = call_groq_json(messages)
            response = AnswerResponse.model_validate(payload)
            if allowed_source_ids is not None and not set(response.sources).issubset(allowed_source_ids):
                raise ValueError("LLM returned a source ID that was not among the retrieved chunks.")
            return response
        except (requests.RequestException, KeyError, json.JSONDecodeError, ValidationError, ValueError, RuntimeError) as exc:
            last_error = exc
            messages = [
                {"role": "user", "content": prompt},
                {
                    "role": "user",
                    "content": f"Corrective instruction: the previous response failed structured-output validation ({exc}). Return only a valid JSON object with answer (string), sources (list of chunk/document IDs), and confidence (number from 0 to 1).",
                },
            ]

    return AnswerResponse(
        answer=f"ERROR: Structured-output validation failed after 3 attempts: {last_error}",
        sources=[],
        confidence=0.0,
    )


def retrieve_and_answer(state: GraphState) -> GraphState:
    ids, documents = retrieve_top3(state["query"])
    top_chunk = documents[0] if documents else "No relevant policy chunk was retrieved."

    if mock_mode():
        # Required graded baseline: deterministic, no LLM/network call.
        return {
            "answer": f"Based on the retrieved context: {top_chunk[:200]}",
            "sources": ids,
            "confidence": 1.0,
            "retrieved_ids": ids,
            "retrieved_texts": documents,
        }

    context = "\n\n".join(f"[{chunk_id}] {text}" for chunk_id, text in zip(ids, documents))
    prompt = STRUCTURED_PROMPT.format(context=context, query=state["query"])
    response = call_real_llm(prompt, allowed_source_ids=set(ids))
    return {
        "answer": response.answer,
        "sources": response.sources,
        "confidence": response.confidence,
        "retrieved_ids": ids,
        "retrieved_texts": documents,
    }


def direct_answer(state: GraphState) -> GraphState:
    if mock_mode():
        # Required graded baseline: fixed canned string and no LLM/network call.
        return {
            "answer": "I can only answer questions about Zepto policies right now.",
            "sources": [],
            "confidence": 1.0,
        }

    prompt = STRUCTURED_PROMPT.format(
        context="No policy retrieval was requested for this general question.",
        query=state["query"],
    )
    response = call_real_llm(prompt)
    return {
        "answer": response.answer,
        "sources": [],
        "confidence": response.confidence,
    }


def route_after_classify(state: GraphState) -> Literal["policy_question", "general_question"]:
    return state["intent"]


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_and_answer", retrieve_and_answer)
    graph.add_node("direct_answer", direct_answer)
    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "policy_question": "retrieve_and_answer",
            "general_question": "direct_answer",
        },
    )
    graph.add_edge("retrieve_and_answer", END)
    graph.add_edge("direct_answer", END)
    return graph.compile()


graph = build_graph()


@app.post("/ask", response_model=AnswerResponse)
def ask(request: AskRequest) -> AnswerResponse:
    result = graph.invoke({"query": request.query})
    return AnswerResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        confidence=result.get("confidence", 0.0),
    )
