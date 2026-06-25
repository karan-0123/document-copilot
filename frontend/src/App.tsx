import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthGuard } from './components/auth-guard';
import { Login } from './pages/login';
import { Signup } from './pages/signup';
import { useState, useEffect } from 'react';
import { supabase } from './lib/supabase';
import type { User } from '@supabase/supabase-js';
import { useChat } from '@ai-sdk/react';

import { Sidebar } from './components/sidebar';
import { WelcomeScreen } from './components/welcome-screen';
import { ChatArea } from './components/chat-area';
import { api } from './lib/api';
import type { ChatThread } from './lib/api';

function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Sync session and token
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setToken(session?.access_token ?? null);
      setUser(session?.user ?? null);
      if (session?.user) {
        loadThreads();
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setToken(session?.access_token ?? null);
      setUser(session?.user ?? null);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // Vercel AI SDK useChat Hook
  const {
    messages,
    setMessages,
    append,
    isLoading: streamingLoading,
  } = useChat({
    api: `${import.meta.env.VITE_API_BASE_URL}/chat/stream`,
    id: activeThreadId || undefined,
    body: {
      thread_id: activeThreadId,
    },
    headers: token
      ? {
          Authorization: `Bearer ${token}`,
        }
      : undefined,
  });

  // Track stream completion to refresh messages with backend citations
  const [prevIsLoading, setPrevIsLoading] = useState(false);
  useEffect(() => {
    if (prevIsLoading && !streamingLoading && activeThreadId) {
      // Reload from backend to get the persisted citations
      api.getMessages(activeThreadId).then((refreshed) => {
        setMessages(refreshed as any);
      }).catch(() => {});
    }
    setPrevIsLoading(streamingLoading);
  }, [streamingLoading, activeThreadId, prevIsLoading, setMessages]);

  // Fetch threads list
  const loadThreads = async () => {
    try {
      const threadList = await api.listThreads();
      setThreads(threadList);
    } catch {
      // Fallback
    }
  };

  // Select Thread
  const handleSelectThread = async (id: string) => {
    setActiveThreadId(id);
    setLoadingHistory(true);
    try {
      const messagesList = await api.getMessages(id);
      setMessages(messagesList as any);
    } catch {
      setMessages([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Create Thread
  const handleCreateThread = async () => {
    const title = `Chat on ${new Date().toLocaleDateString()}`;
    try {
      const newThread = await api.createThread(title);
      setThreads((prev) => [newThread, ...prev]);
      setActiveThreadId(newThread.id);
      setMessages([]);
    } catch {
      // Fallback
    }
  };

  // Delete Thread
  const handleDeleteThread = async (id: string) => {
    try {
      await api.deleteThread(id);
    } catch {
      // Fallback
    }
    const filtered = threads.filter((t) => t.id !== id);
    setThreads(filtered);
    if (activeThreadId === id) {
      setActiveThreadId(null);
      setMessages([]);
    }
  };

  // Sign out
  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  // Send message
  const handleSendMessage = async (content: string) => {
    if (!activeThreadId) return;
    append({ role: 'user', content });
  };

  // Select suggestion prompt card
  const handleSelectPrompt = async (prompt: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      const title = prompt.length > 30 ? `${prompt.substring(0, 30)}...` : prompt;
      try {
        const newThread = await api.createThread(title);
        setThreads((prev) => [newThread, ...prev]);
        threadId = newThread.id;
        setActiveThreadId(threadId);
        setMessages([]);
      } catch {
        return;
      }
    }
    append({ role: 'user', content: prompt }, {
      body: {
        thread_id: threadId
      }
    });
  };

  const activeThread = threads.find((t) => t.id === activeThreadId);

  return (
    <div className="flex h-screen w-screen bg-zinc-950 font-sans overflow-hidden">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onCreateThread={handleCreateThread}
        onDeleteThread={handleDeleteThread}
        userEmail={user?.email}
        onSignOut={handleSignOut}
        isOpen={sidebarOpen}
        setIsOpen={setSidebarOpen}
      />

      <div className="flex flex-col flex-1 overflow-hidden h-full">
        {activeThreadId ? (
          <ChatArea
            messages={messages as any}
            onSendMessage={handleSendMessage}
            isLoading={streamingLoading || loadingHistory}
            threadTitle={activeThread?.title || 'Untitled Chat'}
          />
        ) : (
          <WelcomeScreen onSelectPrompt={handleSelectPrompt} />
        )}
      </div>
    </div>
  );
}


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        
        {/* Protected Routes */}
        <Route element={<AuthGuard />}>
          <Route path="/" element={<Dashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
