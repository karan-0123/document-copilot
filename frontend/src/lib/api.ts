import { request } from './http';

export interface ChatThread {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant';
  content: string;
  sequence: number;
  payload?: any;
  created_at: string;
}

export const api = {
  async listThreads(): Promise<ChatThread[]> {
    const res = await request('/chats/threads');
    return res.json();
  },

  async createThread(title?: string): Promise<ChatThread> {
    const res = await request('/chats/threads', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
    return res.json();
  },

  async getThread(threadId: string): Promise<ChatThread> {
    const res = await request(`/chats/threads/${threadId}`);
    return res.json();
  },

  async updateThread(threadId: string, title: string): Promise<ChatThread> {
    const res = await request(`/chats/threads/${threadId}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    });
    return res.json();
  },

  async deleteThread(threadId: string): Promise<boolean> {
    const res = await request(`/chats/threads/${threadId}`, {
      method: 'DELETE',
    });
    return res.json();
  },

  async getMessages(threadId: string): Promise<ChatMessage[]> {
    const res = await request(`/chats/threads/${threadId}/messages`);
    return res.json();
  },

  async getChunkContext(chunkId: string): Promise<{ id: string; text: string; chunk_index: number }[]> {
    const res = await request(`/chat/chunks/${chunkId}`);
    return res.json();
  },
};

