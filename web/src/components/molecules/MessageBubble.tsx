import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatSource } from '../../types/chat';
import { Book, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import styles from './MessageBubble.module.css';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ role, content, sources }) => {
  const [showSources, setShowSources] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`${styles.wrapper} ${styles[role]}`}>
      {role === 'assistant' && <div className={styles.avatar}>🏛️</div>}
      
      <div className={styles.bubble}>
        <div className={styles.content}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>

        {role === 'assistant' && (
          <div className={styles.bubbleFooter}>
            {sources && sources.length > 0 && (
              <button 
                className={styles.sourceToggle}
                onClick={() => setShowSources(!showSources)}
              >
                <Book size={12} />
                <span>{sources.length} citations</span>
                {showSources ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
            <button className={styles.copyButton} onClick={handleCopy} title="Copy response">
              {copied ? <Check size={12} className={styles.copiedIcon} /> : <Copy size={12} />}
            </button>
          </div>
        )}

        {showSources && sources && (
          <div className={styles.sourceList}>
            <span className={styles.sourceHeader}>Grounded Sources:</span>
            <ul>
              {sources.map((source, index) => (
                <li key={index}>
                  <Book size={10} className={styles.sourceIcon} />
                  <strong>{source.title}</strong>
                  {source.chapter && <span className={styles.sourceChapter}> — {source.chapter}</span>}
                  {source.page_start && <span className={styles.sourcePage}> (p. {source.page_start})</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
