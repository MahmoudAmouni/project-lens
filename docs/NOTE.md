# Submission note: ProjectLens

**AI coding agent:** Claude Code. I planned the architecture, the tools and the edge cases myself (see [PLAN.md](PLAN.md)) and wrote the rules in `CLAUDE.md`. Claude Code then built the project one phase at a time: ingestion, the agent and its tools, the API, the UI, then edge cases. I reviewed and approved each phase before the next one started. Every phase was tested against the real Groq models, and the problems this found were fixed with a test added for each: the model guessing totals, missing tables, unusable tool calls, free-tier rate limits.

**Time:** about 3.5 hours of building on 19 October 2026 (first commit 13:33, last 17:10; 61 small commits), plus the time spent writing the plan.

**Key design decisions**

- **Hybrid agent, not only RAG.** Search finds clauses and facts in text. Numbers come from `query_table`, which checks every row: RAG returns the top few passages and would silently miss items in a "> SAR 1 million" filter.
- **One `Table` model** for Excel sheets and tables inside PDFs (including a BOQ that runs over several pages), so the same tool filters both.
- **The model never retypes numbers.** `query_table` saves its rows under an id, and `submit_answer` attaches them by id, so the table in the answer is exactly what the code computed. Totals are per currency, and "Total" rows and summary sheets are left out so nothing is counted twice.
- **Structured final answer** (`submit_answer`): text, table, sources. Every fact cites file + page or sheet + row.
- **Local multilingual embeddings** (Groq has no embeddings API), plus a keyword bonus. This handles Arabic and near-identical specification pages.
- **Groq free tier** for fast tool calling. Backup models, waits that follow Groq's `retry-after`, a token budget per request and a short file list in the system prompt keep it within 8,000 tokens per minute.
- **No Docker or database**, so reviewers can set it up with one script.

**Testing:** 103 pytest tests, with no API cost because a fake LLM drives the agent. `scripts/evaluate.py` runs 20 real questions through Groq and checks the facts in each answer.

**With more time:** OCR for scanned PDFs, streaming answers, clicking a source to open the PDF at that page, reranking for search, Docker, and a larger evaluation set run in CI.
