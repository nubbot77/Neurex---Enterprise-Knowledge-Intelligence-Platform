import { describe, expect, it } from 'vitest';
import { cn } from './cn';

describe('cn', () => {
  it('joins truthy class names', () => {
    const isActive = false;
    expect(cn('a', 'b', isActive && 'c', undefined, 'd')).toBe('a b d');
  });

  it('resolves conflicting Tailwind utilities in favor of the last one', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4');
  });

  it('merges conditional object syntax', () => {
    expect(cn('base', { active: true, hidden: false })).toBe('base active');
  });
});
