export interface ChatSource {
  title: string;
  chapter: string | null;
  page_start: number | null;
}

export interface ChatResponse {
  answer: string;
  subject: string;
  topic: string | null;
  sources: ChatSource[];
  next_actions: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: ChatSource[];
  next_actions?: string[];
}
