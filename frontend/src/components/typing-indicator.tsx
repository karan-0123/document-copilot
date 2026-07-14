import React from 'react';

/**
 * Three-dot pulsing animation shown when the AI is processing.
 * Displayed before the first token arrives during streaming.
 */
export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-1 px-1 py-1" aria-label="AI is thinking">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="block h-1.5 w-1.5 rounded-full bg-[var(--text-quaternary)]"
          style={{
            animation: 'typing-dot 1.4s ease-in-out infinite',
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes typing-dot {
          0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
          30% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
};
