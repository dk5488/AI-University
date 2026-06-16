import React from 'react';
import styles from './Skeleton.module.css';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  circle?: boolean;
  className?: string;
}

const Skeleton: React.FC<SkeletonProps> = ({ width, height, circle, className = '' }) => {
  const style: React.CSSProperties = {
    width: width,
    height: height,
    borderRadius: circle ? '50%' : 'var(--border-radius-sm)',
  };

  return (
    <div 
      className={`${styles.skeleton} ${className}`} 
      style={style}
    />
  );
};

export default Skeleton;
