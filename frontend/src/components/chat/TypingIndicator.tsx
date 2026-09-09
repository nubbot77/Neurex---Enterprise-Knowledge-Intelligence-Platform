export function TypingIndicator() {
  return (
    <span
      className="inline-flex items-center gap-1"
      role="status"
      aria-label="Assistant is typing"
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="size-1.5 animate-bounce rounded-full bg-fg-subtle"
          style={{ animationDelay: `${i * 120}ms` }}
        />
      ))}
    </span>
  );
}
