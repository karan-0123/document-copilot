import React, { useState } from 'react';
import type { ChatThread } from '@/lib/api';
import { MessageSquare, MoreHorizontal, Pencil, Trash2, Check, X } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ThreadItemProps {
  thread: ChatThread;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (newTitle: string) => void;
}

/**
 * Individual thread list item with dropdown actions (rename, delete).
 * Extracted from sidebar for reusability and cleaner code.
 */
export const ThreadItem: React.FC<ThreadItemProps> = ({
  thread,
  isActive,
  onSelect,
  onDelete,
  onRename,
}) => {
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(thread.title || '');

  const handleStartRename = () => {
    setRenameValue(thread.title || '');
    setIsRenaming(true);
  };

  const handleConfirmRename = () => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== thread.title) {
      onRename(trimmed);
    }
    setIsRenaming(false);
  };

  const handleCancelRename = () => {
    setIsRenaming(false);
    setRenameValue(thread.title || '');
  };

  if (isRenaming) {
    return (
      <div className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 bg-[var(--surface-2)] border border-[var(--border-default)]">
        <MessageSquare size={14} className="text-[var(--text-quaternary)] shrink-0" />
        <input
          type="text"
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleConfirmRename();
            if (e.key === 'Escape') handleCancelRename();
          }}
          autoFocus
          className="flex-1 bg-transparent text-xs text-[var(--text-primary)] outline-none min-w-0 py-0.5"
        />
        <button
          onClick={handleConfirmRename}
          className="p-0.5 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <Check size={12} />
        </button>
        <button
          onClick={handleCancelRename}
          className="p-0.5 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <X size={12} />
        </button>
      </div>
    );
  }

  return (
    <div
      className={`group flex items-center justify-between rounded-lg px-2.5 py-2 text-sm transition-colors cursor-pointer ${
        isActive
          ? 'bg-[var(--surface-2)] text-[var(--text-primary)]'
          : 'text-[var(--text-secondary)] hover:bg-[var(--surface-2)]/50 hover:text-[var(--text-primary)]'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-center gap-2 min-w-0">
        <MessageSquare
          size={14}
          className={
            isActive
              ? 'text-[var(--text-primary)] shrink-0'
              : 'text-[var(--text-quaternary)] shrink-0'
          }
        />
        <span className="truncate text-xs">{thread.title || 'Untitled Chat'}</span>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            onClick={(e) => e.stopPropagation()}
            className="opacity-0 group-hover:opacity-100 p-1 rounded text-[var(--text-quaternary)] hover:text-[var(--text-primary)] transition-all"
          >
            <MoreHorizontal size={14} />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-36">
          <DropdownMenuItem onClick={handleStartRename}>
            <Pencil size={12} />
            Rename
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="text-[var(--destructive-text)]"
          >
            <Trash2 size={12} />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};
