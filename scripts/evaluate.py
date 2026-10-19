"""Accuracy evaluation: ask every question in eval_questions.py through the real agent and check the facts.

Run: python -m scripts.evaluate              (all questions)
     python -m scripts.evaluate 0 5 9        (only these question numbers)
It uses the Groq key in .env (free tier: about 20 questions fit in the daily limit of one model) and
writes a report to docs/accuracy_report.md.
"""

import json
import re
import sys
import time

from AI.agent import Agent
from AI.errors import AIRateLimitedError, AIUnavailableError
from AI.llm_client import LLMClient
from AI.rag.vector_store import VectorStore
from scripts.eval_questions import QUESTIONS
from Server.config import PROJECT_ROOT, load_settings
from Server.ingestion.folder_loader import load_folder

PAUSE_SECONDS = 20  # between questions, to stay inside Groq's tokens-per-minute limit
LIMIT_WAIT_SECONDS = 120  # when the daily limit is used up, wait and try the question again
LIMIT_RETRIES = 20
REPORT = PROJECT_ROOT / "docs" / "accuracy_report.md"


def normalize(text: str) -> str:
    """Lower case, no commas or spaces: "SAR 41,527,500" -> "sar41527500"."""
    return re.sub(r"[,\s]", "", text.lower())


def answer_text(answer) -> str:
    return " ".join([answer.answer, json.dumps(answer.table or {}, ensure_ascii=False)])


def matches(expected: str, raw: str) -> bool:
    """ "re:..." is a regular expression on the lower-case text; anything else is a normalized substring."""
    if expected.startswith("re:"):
        return re.search(expected[3:], raw.lower()) is not None
    return normalize(expected) in normalize(raw)


def check(item: dict, answer) -> list[str]:
    """The problems with one answer (empty list = pass)."""
    raw = answer_text(answer)
    problems = [f"missing one of {group}" for group in item["must"] if not any(matches(t, raw) for t in group)]
    source = item.get("source")
    if source:
        cited = json.dumps(answer.sources, ensure_ascii=False) + json.dumps(answer.table or {}, ensure_ascii=False)
        if source not in cited:
            problems.append(f"no source from {source}")
    return problems


def ask_patiently(agent: Agent, item: dict) -> dict:
    """Ask one question; when Groq's limit is used up, wait for it to free up and ask again."""
    for attempt in range(1, LIMIT_RETRIES + 1):
        start = time.time()
        try:
            answer = agent.ask(item["q"])
            problems = check(item, answer)
            return {"answer": answer.answer, "steps": answer.steps, "model": answer.model, "problems": problems,
                    "seconds": round(time.time() - start, 1)}  # fmt: skip
        except AIRateLimitedError as error:
            if attempt == LIMIT_RETRIES:
                return {"answer": "", "steps": [], "model": "", "problems": [f"AI error: {error}"], "seconds": 0}
            print(f"     rate limit, waiting {LIMIT_WAIT_SECONDS}s ({error})", flush=True)
            time.sleep(LIMIT_WAIT_SECONDS)
        except AIUnavailableError as error:
            return {"answer": "", "steps": [], "model": "", "problems": [f"AI error: {error}"], "seconds": 0}
    raise AssertionError("unreachable")


def run(indexes: list[int]) -> list[dict]:
    settings = load_settings()
    folder = load_folder(PROJECT_ROOT / "sample_docs", settings.max_file_mb)
    store = VectorStore(settings.chroma_dir)
    store.index(folder.folder, folder.documents)
    agent = Agent(LLMClient(settings.groq_api_key, settings.model, settings.fallback_model), folder.documents, store)
    results = []
    for number in indexes:
        item = QUESTIONS[number]
        result = ask_patiently(agent, item)
        result.update(number=number, question=item["q"])
        results.append(result)
        status = "PASS" if not result["problems"] else "FAIL " + "; ".join(result["problems"])
        print(f"[{number:2}] {status}  ({result['seconds']}s, {result['model']})  {item['q']}", flush=True)
        if number != indexes[-1]:
            time.sleep(PAUSE_SECONDS)
    return results


def write_report(results: list[dict]) -> None:
    passed = sum(not r["problems"] for r in results)
    lines = [
        "# Accuracy report",
        "",
        f"{passed} of {len(results)} questions passed ({time.strftime('%Y-%m-%d %H:%M')}).",
        "",
        "| # | Question | Result | Time | Model |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in results:
        verdict = "pass" if not r["problems"] else "FAIL: " + "; ".join(r["problems"])
        lines.append(f"| {r['number']} | {r['question']} | {verdict} | {r['seconds']}s | {r['model']} |")
    lines += ["", "## Answers", ""]
    for r in results:
        lines += [
            f"### {r['number']}. {r['question']}",
            "",
            r["answer"] or "(no answer)",
            "",
            f"Steps: {r['steps']}",
            "",
        ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{passed}/{len(results)} passed. Report: {REPORT}")


if __name__ == "__main__":
    chosen = [int(arg) for arg in sys.argv[1:]] or list(range(len(QUESTIONS)))
    write_report(run(chosen))
