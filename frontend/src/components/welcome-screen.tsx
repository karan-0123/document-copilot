import React from 'react';
import { Send, TrendingUp, AlertTriangle, Cpu, FileText } from 'lucide-react';

interface WelcomeScreenProps {
  onSelectPrompt: (prompt: string) => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onSelectPrompt }) => {
  const suggestions = [
    {
      title: 'Revenue Trends',
      desc: "Summarize Apple's revenue mix and product segment trends from 2021 to 2025.",
      prompt:
        "Summarize Apple's revenue mix and product segment trends from 2021 to 2025.",
      icon: <TrendingUp size={16} />,
    },
    {
      title: 'Export Risks',
      desc: 'What export controls risks and mitigation strategies does NVIDIA detail in its recent risk factors?',
      prompt:
        'What export controls risks and mitigation strategies does NVIDIA detail in its recent risk factors?',
      icon: <AlertTriangle size={16} />,
    },
    {
      title: 'AI Infrastructure',
      desc: 'Compare how Microsoft discusses Azure AI and CapEx infrastructure commitments YoY.',
      prompt:
        'Compare how Microsoft discusses Azure AI and CapEx infrastructure commitments YoY.',
      icon: <Cpu size={16} />,
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 max-w-2xl mx-auto h-full w-full">
      {/* Logo */}
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-border bg-muted/30 text-foreground mb-6 shadow-sm">
        <FileText size={28} strokeWidth={1.5} />
      </div>

      <h1 className="text-3xl font-semibold tracking-tight text-foreground mb-2">
        Document Copilot
      </h1>
      <p className="text-sm text-muted-foreground mb-12 text-center max-w-md">
        Your internal SEC filings research assistant. Query financial trends, compare
        filings, and locate citations.
      </p>

      {/* Suggestion cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full mb-10">
        {suggestions.map((item, idx) => (
          <button
            key={idx}
            onClick={() => onSelectPrompt(item.prompt)}
            className="flex flex-col text-left p-5 rounded-2xl border border-border bg-card hover:bg-muted/50 transition-all duration-200 cursor-pointer group shadow-sm hover:shadow-md hover:-translate-y-0.5"
          >
            <div className="mb-3 p-2 w-fit rounded-lg border border-border bg-background text-muted-foreground group-hover:text-foreground transition-colors shadow-sm">
              {item.icon}
            </div>
            <h3 className="text-sm font-medium text-foreground mb-1">
              {item.title}
            </h3>
            <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
              {item.desc}
            </p>
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="w-full max-w-xl">
        <div className="relative group">
          <input
            type="text"
            placeholder="Ask about SEC filings..."
            className="w-full rounded-full border border-input bg-muted/30 px-6 py-4 pr-14 text-sm text-foreground placeholder-muted-foreground focus:border-ring focus:ring-1 focus:ring-ring focus:outline-none transition-all shadow-sm"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.target as HTMLInputElement).value.trim()) {
                onSelectPrompt((e.target as HTMLInputElement).value.trim());
                (e.target as HTMLInputElement).value = '';
              }
            }}
          />
          <div className="absolute right-3 top-3">
            <button 
              className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
              onClick={(e) => {
                const input = e.currentTarget.parentElement?.previousElementSibling as HTMLInputElement;
                if (input && input.value.trim()) {
                  onSelectPrompt(input.value.trim());
                  input.value = '';
                }
              }}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
