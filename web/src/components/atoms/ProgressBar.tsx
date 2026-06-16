import React from 'react';
import styles from './ProgressBar.module.css';

interface ProgressBarProps {
  value: number; // 0 to 100
  color?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ value, color = 'var(--color-primary)' }) => {
  return (
    <div className={styles.container}>
      <div 
        className={styles.fill} 
        style={{ width: `${value}%`, backgroundColor: color }}
      />
    </div>
  );
};

export default ProgressBar;
