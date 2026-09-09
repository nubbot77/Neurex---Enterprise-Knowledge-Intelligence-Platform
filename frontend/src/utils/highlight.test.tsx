import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { highlightMatches } from './highlight';

describe('highlightMatches', () => {
  it('wraps matching terms in <mark>', () => {
    const { container } = render(
      <>{highlightMatches('the quick brown fox', 'quick fox')}</>,
    );
    const marks = container.querySelectorAll('mark');
    expect(marks).toHaveLength(2);
    expect(marks[0]).toHaveTextContent('quick');
    expect(marks[1]).toHaveTextContent('fox');
  });

  it('is case-insensitive', () => {
    const { container } = render(
      <>{highlightMatches('Hello World', 'world')}</>,
    );
    expect(container.querySelector('mark')).toHaveTextContent('World');
  });

  it('returns plain text when the query is empty', () => {
    const { container } = render(
      <>{highlightMatches('no matches here', '')}</>,
    );
    expect(container.querySelectorAll('mark')).toHaveLength(0);
  });
});
