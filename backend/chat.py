import anthropic
import os
from pathlib import Path
from dotenv import dotenv_values
from typing import AsyncIterator

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You are a helpful assistant that answers questions strictly based on the provided document context.

Rules:
- Only use information from the context below to answer.
- If the answer is not in the context, say: "I couldn't find that information in the uploaded document."
- Be concise and accurate.
- When quoting the document, use quotation marks.
- Do not make up information or use outside knowledge."""


def build_context_block(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Source {i} — {chunk['filename']}, chunk #{chunk['chunk_index']}]\n{chunk['text']}")
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
    user_message = f"Context from document:\n\n{context}\n\n---\n\nQuestion: {question}"

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
