# Submission note: ProjectLens

**AI coding agent:** Claude Code. I planned the architecture, the tools and the edge cases myself (see [PLAN.md](PLAN.md)) and wrote the rules in `CLAUDE.md`: folder structure, commit format, no hard-coded screen text, the key only in `.env`. Claude Code built the project one phase at a time, and I reviewed each phase before the next one started. Every phase was tested against the real models. Each problem this found got a fix and a test: the model guessing totals, unusable tool calls, follow-ups it did not understand, free-tier rate limits.

**Time:** about 9.5 hours on 19 October 2026, plus the time spent writing the plan. The core agent (reading files, tools, sources, edge cases, web UI) was working after about 3.5 hours. The rest went into Arabic support, chat memory, the scope guard and the model picker. 273 small commits, one branch per group of changes, merged into `main` through pull requests.

**Key design decisions**

- **Hybrid agent, not only RAG.** Search finds clauses and facts in text. Numbers come from `query_table`, which checks every row: RAG returns the top few passages and would silently miss items in a "> SAR 1 million" filter.
- **The model never retypes numbers.** `query_table` saves its rows under an id, and `submit_answer` attaches them by that id. The table in the answer is exactly what the code computed. Totals are per currency, and "Total" rows are left out so nothing is counted twice.
- **One `Table` model** for Excel sheets and PDF tables (including BOQs that run over several pages), so one tool filters both.
- **A router before the agent.** A small model detects the writing style (English, Arabic, Lebanese, Arabizi) and the intent. Greetings, off-topic questions and prompt injections get fixed replies without spending tokens; follow-ups reuse the previous answer's sources.
- **Every fact cites its source** (file + page, or file + sheet + row). An answer that comes back without sources gets the locations the tools actually read, or becomes "not found".
- **Built for free tiers.** Groq for fast tool calling, backup models, waits that follow `retry-after`, a token budget per request, and a model picker that shows how much of each model's free limit is left. Gemini is an optional extra choice.
- **No Docker or database**, so reviewers can set it up with one script.

**Testing:** 198 pytest tests with no API cost (a fake LLM drives the agent), plus `scripts/evaluate.py`, which runs 20 real questions and checks the facts in each answer.

**With more time:** OCR for scanned PDFs, streaming answers, clicking a source to open the PDF at that page, reranking for search, Docker, and a larger evaluation set run in CI.
