import React, { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../lib/api';
import { Send, FileText, ChevronDown, ChevronUp, Bot, User } from 'lucide-react';

interface ChatAreaProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  isLoading: boolean;
  threadTitle: string;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  onSendMessage,
  isLoading,
  threadTitle,
}) => {
  const [input, setInput] = useState('');
  const [openCitations, setOpenCitations] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const toggleCitation = (msgId: string) => {
    setOpenCitations((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div className="flex flex-col flex-1 bg-zinc-950 text-zinc-100 overflow-hidden h-full">
      {/* Header */}
      <div className="flex h-16 items-center px-6 border-b border-zinc-800 bg-zinc-950">
        <h3 className="font-semibold text-zinc-200">{threadTitle}</h3>
      </div>

      {/* Messages Window */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => {
          const isAi = msg.role === 'assistant';
          const hasCitations = isAi && msg.payload?.citations && msg.payload.citations.length > 0;
          const showCitList = openCitations[msg.id] || false;

          return (
            <div
              key={msg.id}
              className={`flex gap-4 max-w-3xl ${isAi ? 'mr-auto' : 'ml-auto flex-row-reverse'}`}
            >
              {/* Avatar */}
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-lg border text-sm font-semibold shrink-0 shadow-sm ${
                  isAi
                    ? 'bg-zinc-900 border-zinc-800 text-indigo-400'
                    : 'bg-indigo-950 border-indigo-900 text-indigo-300'
                }`}
              >
                {isAi ? <Bot size={16} /> : <User size={16} />}
              </div>

              {/* Message Bubble */}
              <div className="flex flex-col gap-2 max-w-full">
                <div
                  className={`rounded-2xl px-4.5 py-3.5 text-sm leading-relaxed border ${
                    isAi
                      ? 'bg-zinc-900/40 border-zinc-900/60 text-zinc-200'
                      : 'bg-zinc-900 border-zinc-800 text-zinc-100'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {/* Citations block */}
                {hasCitations && (
                  <div className="border border-zinc-900 rounded-xl bg-zinc-900/20 overflow-hidden">
                    <button
                      onClick={() => toggleCitation(msg.id)}
                      className="flex items-center justify-between w-full px-4 py-2 text-xs font-semibold text-zinc-500 hover:text-zinc-300 transition"
                    >
                      <span className="flex items-center gap-1.5 font-sans">
                        <FileText size={12} />
                        Citations ({msg.payload.citations.length})
                      </span>
                      {showCitList ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>
                    {showCitList && (
                      <div className="px-4 pb-3 space-y-2 border-t border-zinc-900/60 pt-2 bg-zinc-950/20">
                        {msg.payload.citations.map((c: any, idx: number) => (
                          <div key={idx} className="text-xs text-zinc-400">
                            <div className="font-semibold text-indigo-400 mb-0.5">
                              [Citation {c.index}] {c.company} ({c.filing_type} {c.year}) — {c.section} (Page {c.page})
                            </div>
                            <div className="pl-3 border-l-2 border-zinc-800 text-zinc-500 italic">
                              "{c.excerpt}"
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex gap-4 max-w-3xl mr-auto animate-pulse">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-indigo-400 shrink-0">
              <Bot size={16} />
            </div>
            <div className="rounded-2xl px-5 py-3.5 bg-zinc-900/40 border border-zinc-900/60 text-zinc-450 text-sm">
              Thinking and retrieving passages...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-4 bg-zinc-950 border-t border-zinc-900">
        <form onSubmit={handleSubmit} className="relative max-w-3xl mx-auto">
          <input
            type="text"
            required
            disabled={isLoading}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="w-full rounded-2xl border border-zinc-850 bg-zinc-900/40 px-5 py-4 pr-14 text-sm text-zinc-100 placeholder-zinc-550 focus:border-zinc-750 focus:bg-zinc-900/65 focus:outline-none transition-all shadow-md"
            placeholder="Ask anything about Apple, Microsoft, NVIDIA, Amazon or Alphabet..."
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-3.5 top-3.5 flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-655 text-white hover:bg-indigo-500 transition disabled:bg-zinc-800 disabled:text-zinc-600 disabled:opacity-40 shadow-sm"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
};
