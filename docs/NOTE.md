# Note

| | |
| --- | --- |
| **Built with** | Claude Code using **Claude Opus 5.5** |
| **Time** | about **2 days** (19 to 21 October 2026) |
| **My part** | the plan, the rules (`CLAUDE.md`), reviewing every step, live testing |
| **Result** | 470 small commits · 492 automated tests · tested live in 4 languages |

## Key design decisions

| Decision | Why |
| --- | --- |
| **Code computes the numbers, not the AI** | search only returns a few passages, so it would miss rows in "items above 1 million"; `query_table` checks every row |
| **The AI never retypes a table** | rows are saved by the tool and attached by id, so the table is exactly what the code found |
| **Every answer is checked** | numbers, currency and sources must come from a tool; if not, they are removed or corrected |
| **A router before the agent** | greetings, off-topic and "ignore your rules" get an instant fixed reply without using the AI |
| **Reply in the user's style** | English, Arabic, Lebanese or Arabizi; file names and numbers are never translated |
| **Built for free AI keys** | Groq first, Gemini and OpenRouter as backups, limits shown in the app |
| **No Docker, no database** | one setup script, so anyone can run it |

## With more time I would add

| Improvement | Why |
| --- | --- |
| OCR for scanned PDFs | scanned files are detected but not read yet |
| Click a source to open the PDF at that page | faster checking of answers |
| Streaming answers | text appears while it is written |
| Better search ranking | more accurate on long specifications |
| A paid model by default | no waiting on free-tier limits |
| Docker + a bigger test set in CI | easier deployment, safer changes |
