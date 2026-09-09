import type { ReactNode } from 'react';

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Wraps whole-word matches of any query term in <mark>. Renders as React children — never raw HTML, so it's XSS-safe. */
export function highlightMatches(text: string, query: string): ReactNode {
  const terms = query
    .split(/\s+/)
    .map((term) => term.trim())
    .filter(Boolean);

  if (terms.length === 0) return text;

  const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'gi');
  const parts = text.split(pattern);
  // A single capturing group means split() interleaves [text, match, text, match, ...] —
  // odd indices are always the captured matches, so parity tells us which to highlight
  // without re-testing the (stateful, /g/) pattern against each part.

  return parts.map((part, index) =>
    index % 2 === 1 ? (
      <mark key={index} className="rounded-sm bg-accent/20 text-fg">
        {part}
      </mark>
    ) : (
      <span key={index}>{part}</span>
    ),
  );
}
