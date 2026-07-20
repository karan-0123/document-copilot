import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { TooltipProvider } from '@/components/ui/tooltip';
import { AuthGuard } from './components/auth-guard';
import { Login } from './pages/login';
import { Signup } from './pages/signup';
import { useState, useEffect, useRef } from 'react';
import { supabase } from './lib/supabase';
import type { User } from '@supabase/supabase-js';
import { useChat } from 'ai/react';

import { SidebarProvider } from '@/components/ui/sidebar';
import { Sidebar } from './components/sidebar';
import { WelcomeScreen } from './components/welcome-screen';
import { ChatArea } from './components/chat-area';
import { api } from './lib/api';
import { CitationInspector } from './components/citation-inspector';

function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<any | null>(null);

  // Clear citation when active thread changes
  useEffect(() => {
    setSelectedCitation(null);
  }, [activeThreadId]);

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
  const chatResult = useChat({
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

  const {
    messages,
    setMessages,
    append,
    isLoading: streamingLoading,
    stop,
    error,
  } = chatResult || {};

  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);

  useEffect(() => {
    if (pendingPrompt && activeThreadId && append) {
      console.log("APPENDING PENDING PROMPT:", pendingPrompt);
      append({ role: 'user', content: pendingPrompt }).catch(e => console.error("Append error:", e));
      setPendingPrompt(null);
    }
  }, [pendingPrompt, activeThreadId, append]);

  useEffect(() => {
    console.log("CHAT_RESULT_KEYS:", Object.keys(chatResult || {}));
    console.log("APPEND_IS_FUNCTION:", typeof (chatResult as any)?.append === 'function');
  }, [chatResult]);

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

  // Fetch thread history when active thread changes
  useEffect(() => {
    if (activeThreadId) {
      let isMounted = true;
      setLoadingHistory(true);
      api.getMessages(activeThreadId)
        .then((messagesList) => {
          if (isMounted) setMessages(messagesList as any);
        })
        .catch(() => {
          if (isMounted) setMessages([]);
        })
        .finally(() => {
          if (isMounted) setLoadingHistory(false);
        });
      return () => { isMounted = false; };
    }
  }, [activeThreadId, setMessages]);

  // Select Thread
  const handleSelectThread = async (id: string) => {
    setActiveThreadId(id);
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
    try {
      console.log("CALLING APPEND WITH:", { role: 'user', content });
      await append({ role: 'user', content });
    } catch (e) {
      console.error("Append error:", e);
    }
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
        setPendingPrompt(prompt); // Queue it for after state updates
      } catch {
        return;
      }
    } else {
      try {
        console.log("CALLING APPEND WITH:", { role: 'user', content: prompt });
        await append({ role: 'user', content: prompt });
      } catch (e) {
        console.error("Append error:", e);
      }
    }
  };

  const activeThread = threads.find((t) => t.id === activeThreadId);

  return (
    <SidebarProvider>
      <div className="flex h-screen w-screen bg-background text-foreground font-sans overflow-hidden">
        <Sidebar
          threads={threads}
          activeThreadId={activeThreadId}
          onSelectThread={handleSelectThread}
          onCreateThread={handleCreateThread}
          onDeleteThread={handleDeleteThread}
          onRenameThread={(id, title) => console.log('Rename')}
          userEmail={user?.email}
          onSignOut={handleSignOut}
        />

        <div className="flex flex-col flex-1 overflow-hidden h-full min-w-0">
          {activeThreadId ? (
            <div className="flex flex-row flex-1 overflow-hidden h-full min-w-0">
              <ChatArea
                messages={messages as any}
                onSendMessage={handleSendMessage}
                isLoading={streamingLoading || loadingHistory}
                threadTitle={activeThread?.title || 'Untitled Chat'}
                streamError={error?.message}
                onStopGeneration={stop}
                selectedCitation={selectedCitation}
                onSelectCitation={setSelectedCitation}
              />
              {selectedCitation && (
                <CitationInspector
                  citation={selectedCitation}
                  onClose={() => setSelectedCitation(null)}
                />
              )}
            </div>
          ) : (
            <WelcomeScreen onSelectPrompt={handleSelectPrompt} />
          )}
        </div>
      </div>
    </SidebarProvider>
  );
}


function App() {
  return (
    <BrowserRouter>
      <TooltipProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          
          {/* Protected Routes */}
          <Route element={<AuthGuard />}>
            <Route path="/" element={<Dashboard />} />
          </Route>
        </Routes>
      </TooltipProvider>
    </BrowserRouter>
  );
}

export default App;
