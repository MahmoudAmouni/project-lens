# Setup

## 1. Download

| What | Where | Note |
| --- | --- | --- |
| Git | [git-scm.com](https://git-scm.com/downloads) | to clone the project |
| Groq API key (free) | [console.groq.com/keys](https://console.groq.com/keys) | required |
| Gemini API key (free) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | optional backup model |
| OpenRouter API key (free) | [openrouter.ai/keys](https://openrouter.ai/keys) | optional backup model |

Python 3.12, Node 20 and the search model (~470 MB) are installed by the setup script.

## 2. Run

| Step | Windows (PowerShell) | Mac / Linux |
| --- | --- | --- |
| Get the code | `git clone https://github.com/MahmoudAmouni/project-lens.git C:\projects\project-lens` | `git clone https://github.com/MahmoudAmouni/project-lens.git && cd project-lens` |
| Install everything | `cd C:\projects\project-lens; powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` | `scripts/setup.sh` |
| Add your key | open `.env`, set `GROQ_API_KEY=...` | same |
| Start | `powershell -ExecutionPolicy Bypass -File scripts\start.ps1` | `scripts/start.sh` |
| Open | http://localhost:5173 | same |

The sample documents load by themselves. To use your own, type a folder path in the sidebar or drop files on it.

## Optional keys (`.env`)

```text
GROQ_API_KEY=...          # required
GEMINI_API_KEY=...        # optional: Gemini as a choice and backup
OPENROUTER_API_KEY=...    # optional: free OpenRouter models as a backup
```

## If something fails

| Problem | Fix |
| --- | --- |
| Path too long (Windows) | clone into a short folder like `C:\projects\project-lens` |
| "Add your GROQ_API_KEY" | put the key in `.env`, then restart |
| Answers are slow | free-tier rate limit: wait a minute, or pick another model in the top bar |
| Port 8000 or 5173 busy | close the other app using it, then start again |
