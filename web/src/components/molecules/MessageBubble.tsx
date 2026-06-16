import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatSource } from '../../types/chat';
import { Book, ChevronDown, ChevronUp } from 'lucide-react';
import styles from './MessageBubble.module.css';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ role, content, sources }) => {
  const [showSources, setShowSources] = React.useState(false);

  return (
    <div className={`${styles.bubble} ${styles[role]}`}>
      <div className={styles.content}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </div>

      {sources && sources.length > 0 && (
        <div className={styles.sources}>
          <button 
            className={styles.sourceToggle}
            onClick={() => setShowSources(!showSources)}
          >
            <Book size={14} />
            <span>{sources.length} Sources cited</span>
            {showSources ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showSources && (
            <ul className={styles.sourceList}>
              {sources.map((source, index) => (
                <li key={index}>
                  <strong>{source.title}</strong>
                  {source.chapter && <span> - {source.chapter}</span>}
                  {source.page_start && <span> (Page {source.page_start})</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default MessageBubble;
