import React from 'react';
import Card from '../atoms/Card';
import ProgressBar from '../atoms/ProgressBar';
import styles from './ProgressCard.module.css';

interface ProgressCardProps {
  topicName: string;
  completion: number;
  confidence: number;
}

const ProgressCard: React.FC<ProgressCardProps> = ({ topicName, completion, confidence }) => {
  return (
    <Card className={styles.card}>
      <div className={styles.header}>
        <h4>{topicName}</h4>
        <span className={styles.badge}>{completion}% Done</span>
      </div>
      
      <div className={styles.metrics}>
        <div className={styles.metric}>
          <label>Course Completion</label>
          <ProgressBar value={completion} />
        </div>
        <div className={styles.metric}>
          <label>Confidence (LLM Assessment)</label>
          <ProgressBar value={confidence * 10} color="var(--color-secondary)" />
        </div>
      </div>
    </Card>
  );
};

export default ProgressCard;
