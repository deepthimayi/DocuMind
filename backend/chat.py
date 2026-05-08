import anthropic
import os
from pathlib import Path
from dotenv import dotenv_values
from typing import AsyncIterator

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You are a document Q&A assistant. You answer questions using ONLY the retrieved context passages provided — never your training knowledge.

Rules (follow strictly):
- Base every answer solely on the context passages below.
- If the context does not contain enough information to answer, respond with exactly: "I couldn't find that in the document." Do not guess, infer, or use outside knowledge to fill gaps.
- Each passage has a relevance score (0–100%). A low score means the retrieval system was not confident this passage is related to the question — treat low-scored passages with extra skepticism.
- If all passage scores are low and none clearly address the question, say: "I couldn't find that in the document."
- Be concise and precise. Quote the document directly when it helps.
- Never fabricate facts, names, dates, numbers, or figures."""


def build_context_block(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        score = chunk.get("relevance_score")
        score_str = f", relevance: {score:.0%}" if score is not None else ""
        parts.append(f"[Source {i} — {chunk['filename']}, chunk #{chunk['chunk_index']}{score_str}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


async def stream_answer(
    question: str,
    chunks: list[dict],
    history: list[dict],
) -> AsyncIterator[str]:
    secrets = dotenv_values(Path(__file__).parent / ".env")
    api_key = secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    context = build_context_block(chunks)
    max_score = max((c.get("relevance_score", 0) for c in chunks), default=0)
    low_score_note = (
        "\n\n⚠ All retrieved passages have low relevance scores — the document may not contain an answer to this question."
        if max_score < 0.15 else ""
    )
    user_message = f"Context from document:{low_score_note}\n\n{context}\n\n---\n\nQuestion: {question}"

    messages = []
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    async with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def generate_questions(chunks: list[dict]) -> list[str]:
    secrets = dotenv_values(Path(__file__).parent / ".env")
    api_key = secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    sample = "\n\n---\n\n".join(c["text"] for c in chunks[:3])

    msg = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=200,
        system="You generate concise, specific questions a reader might ask about a document. Return only the questions, one per line, no numbering, bullets, or extra text.",
        messages=[{
            "role": "user",
            "content": f"Based on this document sample, generate exactly 3 specific questions a user might want to ask:\n\n{sample}",
        }],
    )

    text = msg.content[0].text.strip()
    return [q.strip() for q in text.split("\n") if q.strip()][:3]
