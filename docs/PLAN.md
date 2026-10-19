# ProjectLens — Full Build Plan

Oct 19, 2026 · @ahmad abou amoun

## 1. Overview

ProjectLens is a web app that reads a folder of project documents (PDFs and Excel files) and answers questions about them, with the source file and page for every answer. You type a question in plain language; an AI agent (an open model running on Groq) uses small tools we write to search the files, read the right parts, filter tables, and then return a clear, structured answer.

**Target: submit a working version within 2 days.** Speed is scored, so we build the core first and polish second.

### How this plan wins each evaluation point

| They judge | What we do |
| --- | --- |
| Delivery time | Build in 7 small phases. A working terminal version exists by the end of day 1. |
| Clean code and docs | Three clear folders (Client, Server, AI), one job per file, short commits, a README anyone can follow in 5 minutes. |
| Accuracy on new documents | Exact tools for numbers and tables (never guessing), RAG for text, every answer cites file + page or sheet + row. |
| Edge cases | Every file gets a status (ok, empty, corrupt, scanned, too big). Bad files are skipped and shown, never crash the app. |
| Live feature in the interview | Adding a tool or a file type takes 3 small steps (see section 10). You will practise one before the call. |

### Golden rules for the whole project

1. **The AI never guesses numbers.** Any question about amounts, totals or filters goes through a code tool that checks every row.
2. **Every answer has a source.** File name plus page (PDF) or sheet and row (Excel).
3. **One file = one job.** If a file passes \~200 lines, split it.
4. **Nothing crashes.** Every error becomes a clear message to the user.
5. **You understand every line.** If Claude Code writes something you can't explain, ask it to explain or simplify before you commit.

### Project info

- **Author:** Mahmoud Abou Amoun
- **Repository:** [github.com/MahmoudAmouni/project-lens](https://github.com/MahmoudAmouni/project-lens)
- **LLM provider:** Groq (free tier)
- **Setup rule:** the AI coding agent installs and downloads everything (Python packages, Node packages, the embedding model, even Python or Node if missing). Mahmoud installs nothing by hand.
- **Secrets rule:** the Groq key lives only in a local `.env` file. It never appears in code, docs, commits or chats.

## 2. Tech stack

We use React for the screen, Python for everything that touches files and the AI. Python has the strongest PDF, Excel and vector-database libraries, so this split gives the best accuracy for the least code.

### Client (frontend)

| Tool | Job | Why this one |
| --- | --- | --- |
| React 18 + Vite | The web app | Fast to start, the standard for modern React |
| JavaScript (JSX) | Language | Simple to read and change live in the interview |
| Tailwind CSS | Styling | Clean, consistent design without writing big CSS files |
| lucide-react | Icons | Light, clean icon set |
| react-markdown + remark-gfm | Show AI answers | Answers come as markdown (bold, lists, tables) |

### Server (backend)

| Tool | Job | Why this one |
| --- | --- | --- |
| Python 3.11+ | Language | Best libraries for documents |
| FastAPI + Uvicorn | Web API | Simple, fast, gives free API docs at /docs |
| Pydantic | Request and response shapes | Checks data automatically, clear errors |
| PyMuPDF (fitz) | Read PDF text page by page | Very fast, handles big files, detects password-protected files |
| pdfplumber | Read tables inside PDFs | Best for BOQ tables in PDFs |
| pandas + openpyxl | Read and filter Excel | Exact filtering like cost > 1,000,000 |
| python-dotenv | Load the API key from .env | Keeps secrets out of the code |

### AI

| Tool | Job | Why this one |
| --- | --- | --- |
| Groq Python SDK (`groq`) | Call the LLM with tool calling | OpenAI-style tool calling, very fast answers, free tier |
| Main model: `openai/gpt-oss-120b` | Agent brain | Strong reasoning and tool use on Groq. Set in .env so it can be swapped |
| Backup model: `llama-3.3-70b-versatile` | Fallback | Used automatically if the main model hits a rate limit |
| ChromaDB (embedded) | Vector database for RAG | Runs inside Python, no Docker, saves to a local folder |
| sentence-transformers, model paraphrase-multilingual-MiniLM-L12-v2 | Turn text into vectors | Free, runs locally, supports **Arabic + English**. Groq has no embeddings API, so this is needed. Downloaded automatically on first run |

**Groq free tier note:** it has per-minute token limits. That is why every tool result is capped in size, and why the client retries and falls back to the backup model on a 429 error.

### Dev tools

- **Claude Code** as the AI coding agent (required by the brief)
- **Git + GitHub** for the repo
- **pytest** for tests, **ruff** to format and lint Python, **Prettier** for the Client

**Not used, on purpose:** no database server, no login, no Docker. They add setup time for the reviewers and are not needed. We list them as future improvements in the note.

## 3. Architecture

The browser only talks to the Server; the Server reads the files and hands the question to the AI; the AI talks to Groq and ChromaDB. Each part has one job, so you can explain and change each part alone.

&#91;embedded content: ProjectLens architecture · Client, Server, AI\]

The AI box is the brain: it holds the agent loop and the tools, and it is the only part that calls the LLM.

### One question, step by step

1. The user types "List all cost items above SAR 1 million" in the Client.
2. The Client sends `POST /api/chat` with the question and recent chat history.
3. The Server checks documents are loaded, then calls the AI agent with the question and the documents.
4. The agent sends the question + tool list to the model on Groq.
5. The model asks for `list_documents`, then `describe_table`, then `query_table` with `amount > 1000000`.
6. Our code runs each tool on the real data and sends the results back.
7. The model calls `submit_answer` with the text, a table of the rows, and the sources.
8. The Server returns that JSON; the Client shows the answer card.

### Dependency rule (say this in the interview)

**Client → Server → AI, never backwards.** The AI folder never imports from Server; the Server passes the documents in. This keeps the AI testable on its own (we test it with a fake LLM) and lets us swap the web layer, for example to the CLI, without touching the brain.

## 4. Folder structure

The repo has three main folders: **Client** (what you see), **Server** (web API + reading files), **AI** (the agent brain). Each file has one job, and the name says the job.

```text
project-lens/
├── Client/                          # React web app
│   ├── public/
│   │   ├── logo.png                 # full logo
│   │   └── favicon.png              # icon only, for the browser tab
│   ├── src/
│   │   ├── api/
│   │   │   └── serverApi.js         # all calls to the Server live here
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.jsx      # logo, folder loader, document list
│   │   │   │   └── TopBar.jsx       # page title, model name, clear chat
│   │   │   ├── documents/
│   │   │   │   ├── FolderLoader.jsx # input for folder path + Load button
│   │   │   │   ├── DocumentList.jsx # list of loaded files
│   │   │   │   └── DocumentItem.jsx # one file: icon, name, pages, status badge
│   │   │   ├── chat/
│   │   │   │   ├── ChatWindow.jsx   # scroll area with all messages
│   │   │   │   ├── ChatInput.jsx    # text box + send button
│   │   │   │   ├── UserMessage.jsx  # the question bubble
│   │   │   │   ├── AgentMessage.jsx # the answer card
│   │   │   │   ├── EmptyState.jsx   # welcome screen + suggested questions
│   │   │   │   └── ThinkingIndicator.jsx # animated steps while waiting
│   │   │   └── answer/
│   │   │       ├── ResultTable.jsx  # table of rows (e.g. BOQ items), CSV export
│   │   │       ├── SourceList.jsx   # source chips under each answer
│   │   │       └── ToolSteps.jsx    # "How I found this" (collapsible)
│   │   ├── hooks/
│   │   │   ├── useChat.js           # chat state: messages, loading, send
│   │   │   └── useDocuments.js      # documents state: load folder, list
│   │   ├── utils/
│   │   │   └── formatters.js        # numbers (SAR 1,250,000), file sizes
│   │   ├── App.jsx                  # puts Sidebar + chat together
│   │   ├── main.jsx                 # React entry point
│   │   └── index.css                # Tailwind + brand colors
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js               # dev proxy: /api -> Server
│
├── Server/                          # FastAPI web API + file reading
│   ├── main.py                      # creates the app, CORS, adds routes
│   ├── config.py                    # reads .env settings in one place
│   ├── state.py                     # holds the loaded documents in memory
│   ├── routes/
│   │   ├── health_routes.py         # GET /api/health
│   │   ├── document_routes.py       # load folder, list documents
│   │   └── chat_routes.py           # POST /api/chat
│   ├── schemas/
│   │   ├── document_schemas.py      # shapes of document requests/responses
│   │   └── chat_schemas.py          # shapes of chat requests/responses
│   ├── ingestion/
│   │   ├── models.py                # Document, Page, Table classes
│   │   ├── folder_scanner.py        # finds files, skips unsupported ones
│   │   ├── pdf_reader.py            # PDF -> pages + tables
│   │   ├── excel_reader.py          # Excel -> sheets as tables
│   │   └── table_cleaner.py         # find header row, fix "SAR 1,200,000" -> number
│   └── cli.py                       # terminal version (backup for the demo)
│
├── AI/                              # the agent brain
│   ├── agent.py                     # the agent loop (question -> tools -> answer)
│   ├── llm_client.py                # one place that talks to the Groq API (+ backup model)
│   ├── prompts.py                   # the system prompt (rules for the AI)
│   ├── tools/
│   │   ├── registry.py              # list of all tools + their JSON schemas
│   │   ├── list_documents.py
│   │   ├── search_documents.py      # RAG search
│   │   ├── read_document.py
│   │   ├── describe_table.py
│   │   ├── query_table.py           # exact filtering (cost > 1M)
│   │   ├── find_dates.py
│   │   └── submit_answer.py         # final structured answer
│   └── rag/
│       ├── chunker.py               # splits text into small pieces
│       └── vector_store.py          # ChromaDB: add pieces, search
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_tools.py
│   └── test_agent.py                # uses a fake LLM, no API cost
├── sample_docs/                     # test files, including broken ones
├── docs/
│   ├── PLAN.md                      # this plan
│   ├── NOTE.md                      # the half-page submission note
│   └── screenshots/
├── scripts/
│   ├── setup.ps1 / setup.sh         # installs EVERYTHING with one command
│   └── start.ps1 / start.sh         # starts Server + Client together
├── .env.example                     # GROQ_API_KEY=, MODEL=, DOCS_FOLDER=
├── .gitignore                       # .env, node_modules, .chroma, __pycache__
├── requirements.txt
├── CLAUDE.md                        # rules for Claude Code (section 10)
└── README.md
```

### Naming rules

| What | Style | Example |
| --- | --- | --- |
| Python files and functions | snake\_case | `pdf_reader.py`, `read_pdf()` |
| Python classes | PascalCase | `Document`, `VectorStore` |
| React components (file + name) | PascalCase | `AgentMessage.jsx` |
| React hooks | camelCase starting with use | `useChat.js` |
| JS helpers and variables | camelCase | `formatCurrency()` |
| Constants | UPPER\_SNAKE\_CASE | `MAX_TOOL_ROUNDS = 10` |
| AI tool names | snake\_case verbs | `query_table`, `find_dates` |

## 5. Server (backend)

The Server has two jobs: turn every file in the folder into clean, structured data, and expose a small API that the Client calls. It never talks to the LLM directly; it hands the question to the AI folder.

### 5.1 Data models (Server/ingestion/models.py)

Every file becomes one `Document`. Simple Python dataclasses, easy to read:

```python
@dataclass
class Page:
    number: int          # 1-based, matches what people see in a PDF viewer
    text: str

@dataclass
class Table:
    id: str              # "Sheet1" for Excel, "page_5_table_1" for a PDF table
    data: pd.DataFrame   # cleaned: real header row, numbers as numbers
    location: str        # human text: "Sheet 'BOQ', rows 2-340" or "page 5"

@dataclass
class Document:
    name: str            # "Contract_A.pdf"
    path: str
    file_type: str       # "pdf" or "excel"
    status: str          # "ok" | "empty" | "corrupt" | "encrypted" | "scanned" | "too_large"
    message: str         # human explanation when status is not ok
    pages: list[Page]    # empty for Excel
    tables: list[Table]  # Excel sheets AND tables found in PDFs
    size_mb: float
```

**Key idea:** tables from PDFs and sheets from Excel become the same `Table` type. So one tool (`query_table`) can filter a BOQ whether it came as an Excel file or a PDF.

### 5.2 How a folder is loaded (ingestion)

1. `folder_scanner.py` lists the folder. Keeps `.pdf`, `.xlsx`, `.xls`, `.xlsm`. Other files are reported as "skipped", not errors.
2. Each file is read inside its own `try/except`. One bad file never stops the others.
3. `pdf_reader.py` opens with PyMuPDF and reads text page by page. If a page has almost no text, it is likely scanned. pdfplumber then pulls tables from pages that have them.
4. `excel_reader.py` reads every sheet with pandas (all as text first), then `table_cleaner.py` finds the real header row (the first row that is mostly words), drops empty rows and columns, and converts money text like `SAR 1,250,000.00` or `1.25M` into numbers.
5. The AI folder's `vector_store.py` splits all text into chunks and stores them in ChromaDB. A file hash is saved, so reloading the same folder is instant.
6. The result is kept in `state.py` (in memory) and returned to the Client with each file's status.

### 5.3 API endpoints

All endpoints start with `/api`. FastAPI shows interactive docs at `http://localhost:8000/docs`, a nice thing to show in the interview.

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | /api/health | none | `{status, model, documents_loaded}` |
| POST | /api/documents/load | `{folder_path}` | list of documents with status, pages, tables, plus skipped files |
| GET | /api/documents | none | the currently loaded documents |
| POST | /api/documents/upload | files (multipart) | same as load. Lets the user drag files in the browser |
| POST | /api/chat | `{question, history}` | `{answer, table, sources, steps}` (see 6.4) |

### 5.4 Errors

Every error returns the same JSON shape, so the Client shows it nicely:

```json
{ "error": { "code": "FOLDER_NOT_FOUND", "message": "The folder C:/docs does not exist." } }
```

Codes we use: `FOLDER_NOT_FOUND`, `FOLDER_EMPTY`, `NO_DOCUMENTS_LOADED`, `AI_UNAVAILABLE` (API key missing or Groq down), `AI_RATE_LIMITED`, `INTERNAL_ERROR`.

### 5.5 Settings (.env)

```text
GROQ_API_KEY=gsk_...your-new-key...
MODEL=openai/gpt-oss-120b
FALLBACK_MODEL=llama-3.3-70b-versatile
DOCS_FOLDER=./sample_docs        # loaded automatically on start (optional)
MAX_FILE_MB=100
CHROMA_DIR=./.chroma
```

### 5.6 Terminal version (Server/cli.py)

`python -m Server.cli ./sample_docs` loads the folder and starts a question loop in the terminal, printing answers and sources with the `rich` library. It reuses the same AI code. If the browser ever fails during the demo, you switch to this in 10 seconds.

## 6. AI (the agent brain)

The AI folder is a **hybrid agent**: RAG search for text questions, exact code tools for numbers and tables, and a final `submit_answer` tool that forces a structured answer with sources. The model on Groq decides which tools to call; our code does the actual reading and filtering.

### 6.1 Why hybrid, not only RAG

| Question type | Example | Best tool | Why |
| --- | --- | --- | --- |
| Find meaning in text | "What are the payment terms?" | `search_documents` (RAG) | Finds the right paragraph even if the words differ |
| Summarize a document | "Summarize the scope of work" | `read_document` | Needs the whole section, in order, not random pieces |
| Numbers and filters | "Items above SAR 1 million" | `query_table` | Must check **every** row. RAG returns only the top 8 pieces and would miss items |
| Extract all of something | "All dates and deliverables" | `find_dates` + `read_document` | Regex finds every date; nothing is skipped |

### 6.2 The tools

Each tool is one file in `AI/tools/`, one function, with a JSON schema in `registry.py`. Every result includes its source, and every result is capped (about 12,000 characters) so a huge document never overflows the AI.

| Tool | Input | Returns |
| --- | --- | --- |
| `list_documents` | none | every file: name, type, status, page count, table names with row counts and columns |
| `search_documents` | `query`, optional `document`, `top_k` (default 8) | best matching text chunks, each with file + page |
| `read_document` | `document`, `start_page`, `end_page` | the text of those pages (max \~10 pages a call; tells the AI if more exist) |
| `describe_table` | `document`, `table_id` | column names, column types, row count, first 5 rows |
| `query_table` | `document`, `table_id`, `filters` \[{column, operator, value}\], optional `columns`, `sort_by`, `limit` | matching rows with their row numbers, plus total count and sum of numeric columns |
| `find_dates` | optional `document` | every date found (many formats, incl. Hijri-style and "Q3 2026"), with the sentence around it and its page |
| `submit_answer` | `answer`, `table`, `sources` | ends the loop; this is the final answer |

**Safety in `query_table`:** operators are a fixed list (`>`, `>=`, `<`, `<=`, `=`, `!=`, `contains`). We never run code from the AI (no `eval`). Column names are matched loosely ("amount" finds "Total Amount (SAR)"), and the tool says which column it used.

**Searching all files at once:** if `document` is `"*"`, `query_table` runs on every table that has a matching column. This answers "in these BOQs" across many files in one call.

### 6.3 The agent loop (AI/agent.py)

1. Build the messages: system prompt + last 6 chat turns + the new question.
2. Send to Groq (`MODEL` from .env) with all tool schemas in OpenAI format (`tools=[{"type": "function", ...}]`).
3. If the reply has `tool_calls`, parse each `function.arguments` JSON, run the tool, record it as a step ("Filtered BOQ\_Phase1.xlsx: 14 rows"), and send the result back as a `role: "tool"` message with the matching `tool_call_id`.
4. Repeat until the model calls `submit_answer`, with a limit of **10 rounds**. If the limit is reached, ask the model once to answer with what it has.
5. Open models sometimes misbehave, so we guard it:
   - broken JSON in tool arguments → send the error back so the model fixes its call
   - a plain-text reply without `submit_answer` → use that text as the answer
   - an unknown tool name → tell the model the list of real tools
6. Retry with backoff (3 tries) on rate limits (429) and timeouts. After a 429, switch to `FALLBACK_MODEL`.
7. Return `answer`, `table`, `sources`, `steps`.

### 6.4 The structured answer

```json
{
  "answer": "Found **14 items** above SAR 1,000,000, total **SAR 38.2M**. The biggest is structural steel...",
  "table": {
    "columns": ["Item", "Description", "Amount (SAR)", "Source"],
    "rows": [["3.2", "Structural steel", 6450000, "BOQ_Phase1.xlsx · Sheet BOQ · row 47"]]
  },
  "sources": [
    { "document": "BOQ_Phase1.xlsx", "location": "Sheet 'BOQ', rows 12-210", "snippet": "3.2 Structural steel ..." }
  ],
  "steps": ["Listed 6 documents", "Filtered BOQ_Phase1.xlsx: 14 rows"]
}
```

`table` is optional: only for list-type answers. `snippet` is a short quote so the user can check the source fast.

### 6.5 The system prompt (AI/prompts.py), main rules

1. Answer **only** from the documents. If the answer is not there, say so clearly. Never invent.
2. Start with `list_documents` if you don't yet know the files.
3. For amounts, totals, counts or thresholds, **always** use `query_table`. Never compute from memory or from search snippets.
4. Before filtering, call `describe_table` to learn the real column names.
5. Note the currency. If a file is not in SAR, say so and don't mix currencies.
6. For "summarize", read the relevant pages in order with `read_document`.
7. Every fact needs a source: file + page, or file + sheet + row.
8. Mention files that could not be read if they might hold the answer.
9. Reply in the language of the question (Arabic or English).
10. Always finish by calling `submit_answer`.

### 6.6 RAG details

- **Chunking:** about 800 characters per chunk with 150 overlap, never crossing a page, so each chunk has one exact page number. Table rows are also added as short text lines, so RAG can find "steel" inside a BOQ.
- **Metadata per chunk:** `document`, `page` or `table_id`, `chunk_index`.
- **Embeddings:** multilingual MiniLM, run locally, free. The first run downloads the model (\~470 MB), so do it once before the interview.
- **Storage:** ChromaDB in `./.chroma`, one collection per folder (named from the folder's hash). Reloading the same files skips embedding.

## 7. Client (UI and UX)

The Client is a clean two-panel app in the logo's navy and teal: documents on the left, chat on the right. The goal is that an interviewer understands it in 3 seconds and trusts every answer because the source is one click away.

### 7.1 Design system

| Token | Value | Used for |
| --- | --- | --- |
| Navy (primary) | #1B3A5C | sidebar, user bubbles, headings, main buttons |
| Teal (accent) | #14A89A | links, source chips, focus ring, success, the "Lens" in the name |
| Background | #F7F9FB | page background |
| Surface | #FFFFFF | cards, answer card, inputs |
| Border | #E3E8EE | card and table borders |
| Text | #0F1B2A / #5B6B7D | main text / quiet text |
| Status colors | green #16A34A, amber #D97706, red #DC2626 | ok / warning (scanned, skipped) / error (corrupt) |
| Font | Inter (Google Fonts), 14px base, 600 for titles | all text; numbers use tabular figures so columns line up |
| Radius and spacing | 12px cards, 8px buttons, 4px spacing scale | consistent, soft look |
| Icons | lucide-react, 18px, 1.75 stroke | file, search, send, copy, download |

Put the colors in `tailwind.config.js` as `brand.navy` and `brand.teal`, so they are never typed as hex in components.

### 7.2 Layout

```text
┌───────────────────────┬──────────────────────────────────────────────────┐
│ [logo] ProjectLens    │  Ask your documents            gpt-oss-120b  · ⟳ │
│                       ├──────────────────────────────────────────────────┤
│ Folder                │                                                  │
│ [ C:/docs/tender  ][Load]│   (Empty state)                                 │
│  or drop files here   │        [logo]                                    │
│                       │   Ask anything about your 6 documents            │
│ Documents (6)         │   [List cost items above SAR 1M]                 │
│ 📄 Contract.pdf  42p ●│   [Summarize the scope of work]                  │
│ 📊 BOQ_P1.xlsx 3 sh ● │   [Extract all dates and deliverables]           │
│ 📄 Scan.pdf  scanned ▲│                                                  │
│ 📄 Old.pdf   corrupt ✕│                                                  │
│                       ├──────────────────────────────────────────────────┤
│ 2 files skipped (.docx)│ [ Ask a question...                     ] [ ➤ ] │
└───────────────────────┴──────────────────────────────────────────────────┘
```

- Sidebar 300px, navy background, white text. Collapses to a drawer on small screens.
- Chat area max width 860px, centered, so lines stay easy to read.
- Input stays fixed at the bottom. **Enter** sends, **Shift+Enter** adds a new line.

### 7.3 The answer card (the most important component)

Each answer card shows, top to bottom:

1. **Answer text** in markdown, with key numbers in bold.
2. **Result table** (when there is one): sticky header, numbers right-aligned and formatted (`SAR 6,450,000`), sortable columns, a total row, and **Export CSV** + **Copy** buttons.
3. **Sources**: small teal chips like `Contract_A.pdf · p. 14` or `BOQ_P1.xlsx · BOQ · row 47`. Clicking a chip opens a popover with the snippet.
4. **How I found this** (collapsed by default): the tool steps, e.g. "Filtered BOQ\_P1.xlsx: 14 rows". This shows the agent is not guessing, which interviewers love.
5. Small actions: copy answer, ask again.

### 7.4 States (good UX = every state is designed)

| State | What the user sees |
| --- | --- |
| No folder loaded | Empty state asks for a folder path or drag-and-drop; chat input disabled with a hint |
| Loading folder | Progress text per file ("Reading BOQ\_P1.xlsx…"), skeleton rows in the list |
| Folder loaded | Toast: "6 documents ready, 1 could not be read" |
| Waiting for answer | ThinkingIndicator: animated dots + rotating labels ("Searching documents", "Reading tables", "Writing answer") |
| Error | Red inline card with the plain message and a **Try again** button; never a blank screen |
| Bad file | Amber or red badge on that file; hover shows why ("Password protected") |
| Very long answer | Card scrolls inside itself; table shows 50 rows with "Show all" |

### 7.5 Polish details (small effort, big impression)

- Favicon and tab title "ProjectLens".
- Smooth fade-in for new messages, auto-scroll to the newest one.
- Suggested questions change to match the loaded files (BOQ files present → show the cost question).
- Accessible: visible focus rings, buttons have labels, color is never the only signal (badges also have icons and text).
- Works on a laptop screen at 100% zoom, since you will screen-share.

## 8. Edge cases

They will test these live, so each one has a planned behavior and a test file in `sample_docs/`. The rule: **detect it, explain it, keep going.**

| Case | How we detect it | What happens |
| --- | --- | --- |
| Folder does not exist | path check before scanning | Error `FOLDER_NOT_FOUND` with the path shown |
| Empty folder / no PDF or Excel | scanner finds 0 supported files | Friendly message; chat stays disabled with a hint |
| Unsupported files (.docx, .png) | file extension | Listed as "skipped" in the sidebar, not an error |
| Corrupt PDF or Excel | the reader raises an exception | File marked `corrupt` (red badge); other files still load; the AI is told the file exists but can't be read |
| Password-protected PDF | PyMuPDF `needs_pass` | Marked `encrypted` with a clear message |
| Scanned PDF (images, no text) | under \~20 characters of text per page | Marked `scanned`; the AI says it can't read it. OCR listed as an improvement |
| Empty file (0 bytes, blank sheets) | size check, no rows after cleaning | Marked `empty` |
| Very large PDF (500+ pages) | page count | Read page by page; tools return max \~10 pages; RAG indexes everything; answers stay fast |
| Very large Excel (100k rows) | row count | Never sent whole; `query_table` returns max 200 rows + total count + sums |
| File over MAX\_FILE\_MB | size check | Marked `too_large`, skipped (limit set in .env) |
| Header not on row 1, merged cells | table\_cleaner finds the first mostly-text row | Correct column names; forward-fill merged cells |
| Money as text ("SAR 1,200,000", "1.2M", Arabic digits) | table\_cleaner number parser | Converted to real numbers; original text kept for display |
| Several tables in one sheet | blank-row gaps | Split into separate tables (nice to have) |
| Mixed currencies | currency words in header or cells | AI reports them separately, never adds SAR + USD |
| Arabic documents or questions | text is UTF-8; multilingual embeddings | Works; the answer comes in the question's language |
| Question not about the documents | system prompt rule | Polite answer: "I can only answer from the loaded documents" |
| Answer not in the documents | tools find nothing | "I couldn't find this in the documents" + what was searched. No made-up answer |
| Missing or wrong API key | check on start + 401 from Groq | Clear message in the UI: "Add your GROQ\_API\_KEY to .env" |
| Groq rate limit or timeout | 429 / timeout errors | Retry 3 times with backoff, switch to the backup model, then a friendly error |
| Agent loops too long | round counter | Stops at 10 rounds and answers with what it found |
| Same folder loaded twice | file hash | Uses the saved index, loads in seconds |

**Test files to prepare in `sample_docs/`:** 1 contract PDF, 2 BOQ Excel files (one with the header on row 4), 1 BOQ as a PDF table, 1 long PDF (200+ pages), 1 scanned PDF, 1 corrupt PDF (rename a .txt to .pdf), 1 password PDF, 1 empty .xlsx, 1 .docx to be skipped, and 1 Arabic PDF if you can find one.

## 9. Commits and build plan

We build in 7 phases, about 16–18 working hours in total, and commit after every small working step. A long, clean commit history shows the reviewers how you work.

### 9.1 Commit format

```text
<Scope> -> <what you did, max 7 words>
```

| Scope | Use for | Example |
| --- | --- | --- |
| Setup | repo, config, dependencies | `Setup -> create project folder structure` |
| Server | API, routes, file reading | `Server -> add PDF reader with tables` |
| AI | agent, tools, prompts, RAG | `AI -> add query table tool` |
| Client | React UI | `Client -> add source chips to answers` |
| Tests | tests and sample files | `Tests -> cover corrupt and empty files` |
| Docs | README, note, plan | `Docs -> write setup steps in README` |
| Fix | a bug in any part | `Fix -> handle header on row four` |

Rules: start the message with a verb (add, fix, update, remove, write), no period at the end, one idea per commit, and never commit `.env`.

### 9.2 Phases, tasks and commits

**Phase 0 — Setup (30 min)**

- Clone the existing GitHub repo `project-lens`, the folders from section 4, `.gitignore`, `.env.example`, `requirements.txt`, `CLAUDE.md`, a short README stub.
- Create the Vite React app inside `Client/`, add Tailwind.
- Commits:
  - `Setup -> create project folder structure`
  - `Setup -> add env example and gitignore`
  - `Setup -> add python requirements`
  - `Setup -> init React app with Tailwind`

**Phase 1 — Server: read documents (3 h)**

- `models.py`, `folder_scanner.py`, `pdf_reader.py`, `excel_reader.py`, `table_cleaner.py`.
- Test on all `sample_docs/` files. Every file must get a correct status.
- Commits:
  - `Server -> add document data models`
  - `Server -> add folder scanner`
  - `Server -> add PDF reader with tables`
  - `Server -> add Excel reader`
  - `Server -> add table cleaner for headers`
  - `Server -> parse money text into numbers`
  - `Tests -> add sample documents and ingestion tests`

**Phase 2 — AI: tools and agent (4 h)**

- `llm_client.py`, `prompts.py`, each tool, `registry.py`, `agent.py`, then RAG (`chunker.py`, `vector_store.py`).
- Build `Server/cli.py` and test the 3 example questions from the email in the terminal.
- **Checkpoint: end of day 1 = a working agent in the terminal.**
- Commits:
  - `AI -> add Groq client with retries`
  - `AI -> add system prompt`
  - `AI -> add list and read tools`
  - `AI -> add describe and query table tools`
  - `AI -> add find dates tool`
  - `AI -> add structured submit answer tool`
  - `AI -> add agent loop with round limit`
  - `AI -> add chunker and Chroma vector store`
  - `AI -> add semantic search tool`
  - `Server -> add terminal chat interface`
  - `Tests -> add tool tests with fake LLM`

**Phase 3 — Server: API (1.5 h)**

- `main.py`, `config.py`, `state.py`, schemas, the three route files, the error format.
- Test every endpoint at `/docs`.
- Commits:
  - `Server -> add FastAPI app and config`
  - `Server -> add document load endpoints`
  - `Server -> add chat endpoint`
  - `Server -> add file upload endpoint`
  - `Server -> add consistent error responses`

**Phase 4 — Client: UI (5 h)**

- Brand colors and fonts first, then layout, then documents panel, then chat, then the answer card, then states and polish.
- Commits:
  - `Client -> add brand colors and fonts`
  - `Client -> add logo and favicon`
  - `Client -> add sidebar and main layout`
  - `Client -> add server API helper`
  - `Client -> add folder loader and document list`
  - `Client -> add chat window and input`
  - `Client -> add answer card with markdown`
  - `Client -> add result table with CSV export`
  - `Client -> add source chips with snippets`
  - `Client -> add collapsible tool steps`
  - `Client -> add empty, loading and error states`
  - `Client -> add drag and drop upload`

**Phase 5 — Edge cases and accuracy (2 h)**

- Go through every row of section 8. Ask 20 different questions on the sample docs and check each answer against the real file by hand. Improve the prompt or tools where answers are wrong.
- Commits like `Fix -> handle password protected PDFs`, `AI -> improve prompt for currency handling`.

**Phase 6 — Docs and submit (1.5 h)**

- README, NOTE.md, 2–3 screenshots, final check on a fresh clone (delete `.venv` and `node_modules`, follow your own README).
- Commits:
  - `Docs -> write README with setup steps`
  - `Docs -> add screenshots`
  - `Docs -> add submission note`
- Reply to the email with the repo link and the note.

### 9.3 Suggested schedule

| When | Work |
| --- | --- |
| Day 1 morning | Phase 0 + Phase 1 |
| Day 1 afternoon | Phase 2 → working terminal agent |
| Day 2 morning | Phase 3 + start Phase 4 |
| Day 2 afternoon | Finish Phase 4 + Phase 5 |
| Day 2 evening or Day 3 morning | Phase 6 and **submit** |

### 9.4 Zero-install setup (Mahmoud downloads nothing)

The AI coding agent does every install and download. Mahmoud only gives it the instructions and pastes his new Groq key into `.env` when asked.

1. Claude Code checks for Python 3.11+ and Node 20+. If either is missing, it installs it (`winget install Python.Python.3.11` and `winget install OpenJS.NodeJS.LTS` on Windows; `brew` on Mac).
2. It clones `https://github.com/MahmoudAmouni/project-lens.git`, creates the folders, and installs all Python packages into a `.venv` and all Node packages into `Client/node_modules`.
3. It downloads the embedding model once by running a small warm-up script, so the first real question is fast.
4. It creates `.env` from `.env.example` and asks Mahmoud to paste the key. It never prints, commits or logs the key.
5. It writes two scripts so reviewers also install nothing by hand:
   - `scripts/setup.ps1` / `scripts/setup.sh`: one command installs everything above
   - `scripts/start.ps1` / `scripts/start.sh`: one command starts the Server (port 8000) and the Client (port 5173) together
6. Commits: `Setup -> add one command setup scripts` and `Setup -> add start script for both apps`.

## 10. Testing, docs and interview prep

The last step is proof: tests that run without API cost, a README that works on a fresh machine, a half-page note, and practice for the live feature.

### 10.1 Tests (pytest)

- `test_ingestion.py`: each sample file gets the right status; the header on row 4 is found; "SAR 1,200,000" becomes 1200000.
- `test_tools.py`: `query_table` with `>` 1,000,000 returns exactly the right rows; bad column names give a helpful error, not a crash.
- `test_agent.py`: a **fake LLM** returns scripted tool calls, so we test the loop, the round limit and `submit_answer` for free.
- Run with `pytest -q`. Mention the test count in the README.

### 10.2 README.md outline

1. Logo + one-line description + a screenshot
2. Features (6 bullets)
3. Quick start: requirements (Python 3.11, Node 20), then copy-paste commands:

   ```text
   git clone https://github.com/MahmoudAmouni/project-lens.git && cd project-lens
   python -m venv .venv && .venv\Scripts\activate   (Mac/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   copy .env.example .env   # add your GROQ_API_KEY   (or simply run scripts/setup)
   uvicorn Server.main:app --reload --port 8000
   cd Client && npm install && npm run dev   # open http://localhost:5173
   ```
4. Terminal mode: `python -m Server.cli ./sample_docs`
5. Example questions with a sample answer
6. Architecture: the diagram from section 3 + folder tree (short)
7. How the agent works: hybrid tools, why numbers never come from RAG
8. Edge cases handled (short table)
9. Running tests
10. Limitations and future work

### 10.3 The submission note (docs/NOTE.md, half a page)

- **AI coding agent:** Claude Code. Say how: you planned the architecture yourself, gave it this plan and `CLAUDE.md`, worked file by file, reviewed every change, and wrote or fixed the prompt and edge cases by hand.
- **Time:** be honest, with real hours (track them with the commit times).
- **Key design decisions:** hybrid agent (RAG + exact table tools); PDF tables and Excel sheets share one Table model; structured final answer through `submit_answer`; local multilingual embeddings for Arabic (Groq has no embeddings API); Groq for fast, free tool calling with an automatic backup model; no Docker or database, for easy setup.
- **With more time:** OCR for scanned PDFs, streaming answers, a click on a source to open the PDF page, reranking for better RAG, Docker setup, an evaluation set of questions with expected answers to measure accuracy.

### 10.4 CLAUDE.md (rules for Claude Code, at the repo root)

```markdown
# ProjectLens — rules for Claude Code
- Read docs/PLAN.md before any task. Follow its folder structure and names.
- Install and download EVERYTHING yourself (Python, Node, pip and npm packages, the embedding model). Never ask Mahmoud to install anything.
- LLM = Groq via the `groq` SDK; model names come from .env. Never write the API key in code, docs, logs or commits.
- Client = React + Vite + Tailwind (JS). Server = FastAPI. AI = agent, tools, RAG.
- AI/ never imports from Server/. Server passes documents into the agent.
- One job per file. Max ~200 lines per file. Clear names, no abbreviations.
- Python: type hints, short docstrings, snake_case. React: function components, PascalCase.
- Never send numbers to the user that a tool did not compute.
- Every error is caught and turned into a clear message.
- Brand colors only from tailwind.config.js (brand.navy, brand.teal).
- Commit format: "<Scope> -> <verb + what>" max 7 words. Scopes: Setup, Server, AI, Client, Tests, Docs, Fix.
- Do one small task at a time, then stop so I can review and commit.
```

**How to work with Claude Code:** give one phase at a time, e.g. "Do Phase 1, step: pdf\_reader.py, following docs/PLAN.md section 5.2". Read the code, ask "explain this file in simple words", run it, then commit. Never accept a big change you don't understand.

### 10.5 Interview prep

**Demo script (5 minutes):** load their folder → point at the statuses → ask a number question (show the table + sources + steps) → ask a summary question → ask something not in the docs (shows it doesn't invent) → open a source chip.

**How to add a new tool in 3 steps** (the most likely live feature):

1. Create `AI/tools/<new_tool>.py` with one function that returns data + source.
2. Add its name, description and JSON schema in `AI/tools/registry.py`.
3. Add one line to the system prompt saying when to use it.

**Features they might ask you to add live — practise 2 of these before the call:**

- Support `.csv` or `.docx` files (one new reader in `Server/ingestion/`)
- A tool to compare two BOQs or sum costs per category (`group_by` in `query_table`)
- Filter the chat to one selected document
- Show token usage or cost per answer
- Export the whole chat as a file
- A "clear chat" or "reload folder" button

**Questions to be ready for:** Why not only RAG? How do you stop the AI from inventing numbers? What happens with a 1,000-page PDF? Why ChromaDB and not Qdrant? How would you deploy this for the whole company?
