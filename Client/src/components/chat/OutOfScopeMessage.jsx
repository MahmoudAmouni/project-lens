// Fixed replies: a soft amber card for questions outside the documents, a teal one for greetings
// and for messages too short to answer ("?").
// The example questions are buttons that ask them.

import { Info, MessageCircleQuestion, Sparkles } from "lucide-react";

const LOOK = {
  out_of_scope: {
    icon: Info,
    card: "border-status-warn/30 bg-status-warn/10",
    iconColor: "text-status-warn",
  },
  greeting: { icon: Sparkles, card: "border-brand-teal/30 bg-brand-teal-soft", iconColor: "text-brand-teal" },
  clarify: {
    icon: MessageCircleQuestion,
    card: "border-brand-teal/30 bg-brand-teal-soft",
    iconColor: "text-brand-teal",
  },
};

export default function OutOfScopeMessage({ answer, onAsk }) {
  const look = LOOK[answer.kind] ?? LOOK.out_of_scope;
  const Icon = look.icon;
  const rightToLeft = answer.style === "ar" || answer.style === "ar-lb";

  return (
    <div
      dir={rightToLeft ? "rtl" : "ltr"}
      className={`flex animate-fade-in gap-3 rounded-card border px-4 py-3 ${look.card}`}
      role="status"
    >
      <Icon size={18} className={`mt-0.5 shrink-0 ${look.iconColor}`} aria-hidden="true" />
      <div className="min-w-0 flex-1 space-y-2.5">
        <p className="leading-relaxed text-ink">{answer.answer}</p>
        {answer.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {answer.suggestions.map((question) => (
              <button
                key={question}
                onClick={() => onAsk(question)}
                className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5 text-[13px] text-ink hover:border-brand-teal hover:text-brand-teal-dark"
              >
                <MessageCircleQuestion size={14} aria-hidden="true" className="shrink-0 text-brand-teal" />
                {question}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
