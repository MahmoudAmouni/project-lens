// The question bubble.

export default function UserMessage({ text }) {
  return (
    <div className="flex animate-fade-in justify-end">
      <p
        dir="auto"
        className="max-w-[80%] whitespace-pre-wrap rounded-card rounded-br-sm bg-brand-navy px-4 py-2.5 leading-relaxed text-white"
      >
        {text}
      </p>
    </div>
  );
}
