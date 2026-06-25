import React from 'react';
import { Sparkles, TrendingUp, AlertTriangle, Cpu } from 'lucide-react';

interface WelcomeScreenProps {
  onSelectPrompt: (prompt: string) => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onSelectPrompt }) => {
  const suggestions = [
    {
      title: 'Apple Revenue Mix',
      desc: 'Show Apple revenue segments and products trends for 2021–2025.',
      prompt: 'Summarize Apple\'s revenue mix and product segment trends from 2021 to 2025.',
      icon: <TrendingUp size={18} className="text-green-400" />,
    },
    {
      title: 'NVIDIA Export Risks',
      desc: 'Explain export control risks and mitigations noted in NVIDIA 10-Ks.',
      prompt: 'What export controls risks and mitigation strategies does NVIDIA detail in its recent risk factors?',
      icon: <AlertTriangle size={18} className="text-amber-400" />,
    },
    {
      title: 'Microsoft AI Cloud Wording',
      desc: 'Compare AI infrastructure Capex commitments wording YoY.',
      prompt: 'Compare how Microsoft discusses Azure AI and CapEx infrastructure commitments YoY.',
      icon: <Cpu size={18} className="text-cyan-400" />,
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center px-4 max-w-3xl mx-auto py-16">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-900 border border-zinc-800 text-indigo-400 mb-6 shadow-md shadow-indigo-950/20">
        <Sparkles size={32} className="animate-pulse" />
      </div>
      <h1 className="text-4xl font-extrabold tracking-tight mb-2 text-white">
        Document Copilot
      </h1>
      <p className="text-zinc-400 text-lg mb-10 max-w-xl">
        Your internal SEC filings research assistant. Query financial trends, compare filings, and locate citations.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
        {suggestions.map((item, idx) => (
          <div
            key={idx}
            onClick={() => onSelectPrompt(item.prompt)}
            className="flex flex-col text-left p-5 rounded-2xl border border-zinc-800 bg-zinc-900/35 hover:bg-zinc-900/70 hover:border-zinc-700 transition cursor-pointer group shadow-sm"
          >
            <div className="mb-3 p-2 w-fit rounded-lg bg-zinc-900 border border-zinc-800 group-hover:border-zinc-700 transition">
              {item.icon}
            </div>
            <h3 className="font-semibold text-zinc-200 mb-1 group-hover:text-white transition">
              {item.title}
            </h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              {item.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
