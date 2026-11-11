import * as React from 'react';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

export interface SearchInputProps {
  value: string;
  onChange: (nextValue: string) => void;
  placeholder?: string;
  shortcutHint?: string;
  ariaLabel?: string;
  className?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Search decisions, agents, or policies…',
  shortcutHint,
  ariaLabel = 'Search',
  className,
}: SearchInputProps) {
  return (
    <div className={cn('relative flex items-center', className)}>
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute left-3 h-4 w-4 text-muted-foreground"
      />
      <Input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        className="pl-9 pr-14"
      />
      {value ? (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="Clear search"
          className="absolute right-2.5 rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      ) : shortcutHint ? (
        <kbd className="pointer-events-none absolute right-2.5 hidden rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline-block">
          {shortcutHint}
        </kbd>
      ) : null}
    </div>
  );
}

export interface FilterBarProps {
  children: React.ReactNode;
  className?: string;
}

export function FilterBar({ children, className }: FilterBarProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-lg border border-border bg-card/60 p-3 sm:flex-row sm:items-center sm:justify-between',
        className
      )}
    >
      {children}
    </div>
  );
}

