import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { sendMessage } from '../api/chat';
import type { ChatMessage } from '../types/chat';
import MessageBubble from '../components/molecules/MessageBubble';
import { Send, Sparkles } from 'lucide-react';
import styles from './ChatPage.module.css';

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (text: string) => sendMessage(text),
    onSuccess: (data) => {
      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.answer,
        timestamp: new Date().toISOString(),
        sources: data.sources,
        next_actions: data.next_actions,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    },
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || mutation.isPending) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    mutation.mutate(input);
    setInput('');
  };

  const handleAction = (action: string) => {
    if (action.includes('Generate MCQs')) {
      // Basic extraction of topic slug - in a real app we'd have structured action objects
      // For now, if we're in a Polity context, we can assume subject is polity
      const topic = action.split(' on ')[1]?.toLowerCase().replace(/ /g, '-') || 'polity';
      navigate(`/quiz/polity/${topic}`);
      return;
    }

    setInput(action);
    mutation.mutate(action);
    setMessages((prev) => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: action,
      timestamp: new Date().toISOString(),
    }]);
  };

  return (
    <div className={styles.container}>
      <div className={styles.chatWindow} ref={scrollRef}>
        {messages.length === 0 && (
          <div className={styles.welcome}>
            <Sparkles size={48} color="var(--color-secondary)" />
            <h2>How can I help your UPSC preparation today?</h2>
            <p>I can teach you Indian Polity topics, explain concepts from Laxmikanth, or test your knowledge with MCQs.</p>
          </div>
        )}
        
        {messages.map((m) => (
          <MessageBubble 
            key={m.id}
            role={m.role}
            content={m.content}
            sources={m.sources}
          />
        ))}

        {mutation.isPending && (
          <div className={styles.loading}>
            <span>Mentor is thinking...</span>
          </div>
        )}

        {messages.length > 0 && messages[messages.length - 1].role === 'assistant' && 
         messages[messages.length - 1].next_actions && (
          <div className={styles.actions}>
            {messages[messages.length - 1].next_actions?.map((action, i) => (
              <button 
                key={i} 
                className={styles.actionButton}
                onClick={() => handleAction(action)}
              >
                {action}
              </button>
            ))}
          </div>
        )}
      </div>

      <form className={styles.inputArea} onSubmit={handleSubmit}>
        <input 
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about Polity (e.g. Fundamental Rights, Article 32)..."
          disabled={mutation.isPending}
        />
        <button type="submit" disabled={mutation.isPending || !input.trim()}>
          <Send size={20} />
        </button>
      </form>
    </div>
  );
};

export default ChatPage;
