// The answer card: markdown answer, result table, sources, "How I found this", copy and ask again.

import { Check, Copy, RefreshCw } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ResultTable from "../answer/ResultTable";
import SourceList from "../answer/SourceList";
import ToolSteps from "../answer/ToolSteps";

export default function AgentMessage({ answer, onAskAgain }) {
  const [copied, setCopied] = useState(false);

  async function copyAnswer() {
    await navigator.clipboard.writeText(answer.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <article className="animate-fade-in space-y-4 rounded-card border border-line bg-surface p-5 shadow-sm">
      <div dir="auto" className="answer-markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer.answer}</ReactMarkdown>
      </div>

      {answer.table && <ResultTable table={answer.table} />}

      <SourceList sources={answer.sources} />

      <div className="flex items-center gap-3 border-t border-line pt-3">
        <ToolSteps steps={answer.steps} />
        <div className="ml-auto flex shrink-0 gap-1 text-xs text-ink-quiet">
          <button
            onClick={copyAnswer}
            className="flex items-center gap-1 rounded-button px-2 py-1 hover:bg-page hover:text-ink"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy"}
          </button>
          <button
            onClick={onAskAgain}
            className="flex items-center gap-1 rounded-button px-2 py-1 hover:bg-page hover:text-ink"
          >
            <RefreshCw size={14} /> Ask again
          </button>
        </div>
      </div>
    </article>
  );
}
