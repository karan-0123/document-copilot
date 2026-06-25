import React from 'react';
import type { ChatThread } from '../lib/api';
import { Plus, MessageSquare, Trash2, LogOut, ChevronLeft, ChevronRight, User } from 'lucide-react';

interface SidebarProps {
  threads: ChatThread[];
  activeThreadId: string | null;
  onSelectThread: (id: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (id: string) => void;
  userEmail: string | undefined;
  onSignOut: () => void;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  userEmail,
  onSignOut,
  isOpen,
  setIsOpen,
}) => {
  return (
    <div
      className={`relative flex flex-col border-r border-zinc-800 bg-zinc-950 text-zinc-200 transition-all duration-300 ${
        isOpen ? 'w-72' : 'w-0 border-r-0'
      }`}
    >
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute -right-4 top-6 z-40 flex h-8 w-8 items-center justify-center rounded-full border border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 shadow-md transition"
      >
        {isOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>

      {isOpen && (
        <>
          <div className="flex h-16 items-center px-6 border-b border-zinc-800">
            <span className="text-lg font-bold tracking-wider bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              DOCUMENT COPILOT
            </span>
          </div>

          {/* New Chat Button */}
          <div className="p-4">
            <button
              onClick={onCreateThread}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900/50 py-3 text-sm font-semibold hover:bg-zinc-800/80 hover:border-zinc-700 transition duration-200"
            >
              <Plus size={16} />
              New chat
            </button>
          </div>

          {/* Threads List */}
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
            <div className="px-3 py-1 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Conversations
            </div>
            {threads.length === 0 ? (
              <div className="px-4 py-3 text-sm text-zinc-500 italic">
                No recent chats
              </div>
            ) : (
              threads.map((thread) => (
                <div
                  key={thread.id}
                  className={`group flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition cursor-pointer ${
                    activeThreadId === thread.id
                      ? 'bg-zinc-800/80 text-zinc-100 font-medium'
                      : 'text-zinc-400 hover:bg-zinc-900/60 hover:text-zinc-200'
                  }`}
                  onClick={() => onSelectThread(thread.id)}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <MessageSquare size={16} className={activeThreadId === thread.id ? 'text-indigo-400' : 'text-zinc-500'} />
                    <span className="truncate">{thread.title || 'Untitled Chat'}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(thread.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 rounded transition"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Footer / User Profile */}
          <div className="border-t border-zinc-800 p-4 bg-zinc-950/40">
            <div className="flex items-center justify-between gap-2 rounded-xl p-2 bg-zinc-900/30">
              <div className="flex items-center gap-2 min-w-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-950 text-indigo-300 font-semibold border border-indigo-900">
                  <User size={16} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-zinc-500 font-medium">Session user</p>
                  <p className="truncate text-xs font-semibold text-zinc-300" title={userEmail}>
                    {userEmail}
                  </p>
                </div>
              </div>
              <button
                onClick={onSignOut}
                className="p-2 text-zinc-500 hover:text-red-400 hover:bg-zinc-800/40 rounded-lg transition"
                title="Sign out"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
