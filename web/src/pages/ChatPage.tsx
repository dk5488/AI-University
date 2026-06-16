import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { sendMessage } from '../api/chat';
import type { ChatMessage } from '../types/chat';
import MessageBubble from '../components/molecules/MessageBubble';
import { Send, Sparkles, BookOpen, RotateCcw } from 'lucide-react';
import { useToast } from '../hooks/useToast';
import styles from './ChatPage.module.css';

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();
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
    onError: () => {
      showToast('Failed to connect to Mentor. Checking your connection...', 'error');
    }
  });

  const handleSend = React.useCallback((text: string) => {
    if (!text.trim() || mutation.isPending) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    mutation.mutate(text);
    setInput('');
  }, [mutation]);

  const initialHandleRef = useRef(false);

  // Handle initial topic/subject from URL
  useEffect(() => {
    if (initialHandleRef.current) return;

    const topic = searchParams.get('topic');
    const subject = searchParams.get('subject');
    const mode = searchParams.get('mode');

    if ((topic || subject) && messages.length === 0 && !mutation.isPending) {
      initialHandleRef.current = true;
      const initialText = mode === 'revision' 
        ? `I'd like to revise ${topic || subject}.` 
        : `Tell me about ${topic || subject}.`;
      // Defer to avoid synchronous state update in effect
      setTimeout(() => handleSend(initialText), 0);
    }
  }, [searchParams, handleSend, messages.length, mutation.isPending]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend(input);
  };

  const handleAction = (action: string) => {
    if (action.toLowerCase().includes('generate mcqs')) {
      // Find the last assistant message to get topic context if possible
      const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant');
      const topic = lastAssistant?.content.split(' ')[0] || 'general'; // Simplified
      navigate(`/quiz/POLITY/${topic.toLowerCase().replace(/ /g, '-')}`);
      return;
    }

    handleSend(action);
  };

  return (
    <div className={styles.container}>
      <header className={styles.chatHeader}>
        <div className={styles.mentorInfo}>
          <div className={styles.avatar}>🏛️</div>
          <div>
            <h3>UPSC Mentor</h3>
            <span className={styles.status}>Online | Grounded in Laxmikanth & NCERT</span>
          </div>
        </div>
        <button className={styles.resetButton} onClick={() => setMessages([])}>
          <RotateCcw size={16} />
          New Session
        </button>
      </header>

      <div className={styles.chatWindow} ref={scrollRef}>
        {messages.length === 0 && !mutation.isPending && (
          <div className={styles.welcome}>
            <div className={styles.sparkleIcon}>
              <Sparkles size={48} />
            </div>
            <h2>Namaste, Aspirant</h2>
            <p>I am your personalized AI mentor for UPSC Civil Services preparation.</p>
            <div className={styles.suggestions}>
              <button onClick={() => handleSend('Explain Preamble of India')}>
                <BookOpen size={16} /> Explain Preamble
              </button>
              <button onClick={() => handleSend('What are Fundamental Rights?')}>
                <BookOpen size={16} /> Fundamental Rights
              </button>
              <button onClick={() => handleSend('Difference between Article 32 and 226')}>
                <BookOpen size={16} /> Article 32 vs 226
              </button>
            </div>
          </div>
        )}
        
        <div className={styles.messageList}>
          {messages.map((m) => (
            <MessageBubble 
              key={m.id}
              role={m.role}
              content={m.content}
              sources={m.sources}
            />
          ))}

          {mutation.isPending && (
            <div className={`${styles.bubble} ${styles.assistant} ${styles.loadingBubble}`}>
              <div className={styles.typingIndicator}>
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span className={styles.loadingText}>Consulting source material...</span>
            </div>
          )}
        </div>

        {messages.length > 0 && messages[messages.length - 1].role === 'assistant' && 
         messages[messages.length - 1].next_actions && !mutation.isPending && (
          <div className={styles.actions}>
            <span className={styles.actionLabel}>Recommended Next Steps:</span>
            <div className={styles.actionButtons}>
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
          </div>
        )}
      </div>

      <form className={styles.inputArea} onSubmit={handleSubmit}>
        <div className={styles.inputWrapper}>
          <input 
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask your mentor about Polity, History, or Economy..."
            disabled={mutation.isPending}
          />
          <button type="submit" disabled={mutation.isPending || !input.trim()}>
            <Send size={20} />
          </button>
        </div>
        <p className={styles.disclaimer}>
          AI responses are grounded in NCERT and Laxmikanth but may still contain errors.
        </p>
      </form>
    </div>
  );
};

export default ChatPage;
