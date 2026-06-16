import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDashboard } from '../api/learning';
import ProgressCard from '../components/molecules/ProgressCard';
import Card from '../components/atoms/Card';
import { AlertCircle, ArrowRight } from 'lucide-react';
import styles from './DashboardPage.module.css';

const DashboardPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => getDashboard(),
  });

  if (isLoading) return <div className={styles.loading}>Analyzing your progress...</div>;
  if (error) return <div className={styles.error}>Error loading dashboard. Ensure backend is running.</div>;

  return (
    <div className={styles.container}>
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.title}>Your Study Progress</h2>
        </div>
        <div className={styles.grid}>
          {data?.progress.map((p) => (
            <ProgressCard 
              key={p.topic_slug}
              topicName={p.topic_name}
              completion={p.completion_percent}
              confidence={p.confidence_score}
            />
          ))}
          {data?.progress.length === 0 && (
            <p className={styles.empty}>No progress tracked yet. Start a chat to begin learning!</p>
          )}
        </div>
      </section>

      <div className={styles.bottomRow}>
        <section className={styles.revisions}>
          <h2 className={styles.title}>Due Revisions</h2>
          <div className={styles.revisionList}>
            {data?.due_revisions.map((r) => (
              <div key={r.task_id} className={styles.revisionItem}>
                <div className={styles.revisionInfo}>
                  <AlertCircle size={16} color="var(--color-error)" />
                  <div>
                    <strong>{r.topic_name}</strong>
                    <p>{r.reason}</p>
                  </div>
                </div>
                <button className={styles.reviseButton}>
                  Revise Now <ArrowRight size={16} />
                </button>
              </div>
            ))}
            {data?.due_revisions.length === 0 && (
              <p className={styles.empty}>All caught up! No revisions due.</p>
            )}
          </div>
        </section>

        <section className={styles.subjects}>
          <h2 className={styles.title}>Available Subjects</h2>
          <div className={styles.subjectGrid}>
            {data?.available_subjects.map((s) => (
              <Card key={s.code} className={styles.subjectCard}>
                <div className={styles.subjectIcon}>🏛️</div>
                <div>
                  <strong>{s.name}</strong>
                  <p>{s.topics_count} Topics</p>
                </div>
              </Card>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

export default DashboardPage;
