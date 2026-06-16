import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getDashboard } from '../api/learning';
import ProgressCard from '../components/molecules/ProgressCard';
import Card from '../components/atoms/Card';
import { AlertCircle, ArrowRight, BookOpen, GraduationCap, Clock } from 'lucide-react';
import styles from './DashboardPage.module.css';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
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
          <h2 className={styles.title}>
            <GraduationCap size={24} className={styles.titleIcon} />
            Your Study Progress
          </h2>
        </div>
        <div className={styles.grid}>
          {data?.progress.map((p) => (
            <div 
              key={p.topic_slug} 
              className={styles.clickableProgress}
              onClick={() => navigate(`/chat?topic=${p.topic_slug}`)}
            >
              <ProgressCard 
                topicName={p.topic_name}
                completion={p.completion_percent}
                confidence={p.confidence_score}
              />
            </div>
          ))}
          {data?.progress.length === 0 && (
            <Card className={styles.emptyCard}>
              <p className={styles.empty}>No progress tracked yet. Start a chat to begin learning!</p>
              <button 
                className={styles.startLearningButton}
                onClick={() => navigate('/chat')}
              >
                Start Learning <ArrowRight size={16} />
              </button>
            </Card>
          )}
        </div>
      </section>

      <div className={styles.bottomRow}>
        <section className={styles.revisions}>
          <h2 className={styles.title}>
            <Clock size={22} className={styles.titleIcon} />
            Due Revisions
          </h2>
          <div className={styles.revisionList}>
            {data?.due_revisions.map((r) => (
              <div key={r.task_id} className={styles.revisionItem}>
                <div className={styles.revisionInfo}>
                  <AlertCircle size={20} className={styles.alertIcon} />
                  <div>
                    <strong>{r.topic_name}</strong>
                    <p>{r.reason}</p>
                  </div>
                </div>
                <button 
                  className={styles.reviseButton}
                  onClick={() => navigate(`/chat?topic=${r.topic_slug}&mode=revision`)}
                >
                  Revise Now <ArrowRight size={16} />
                </button>
              </div>
            ))}
            {data?.due_revisions.length === 0 && (
              <div className={styles.emptyState}>
                <p className={styles.empty}>All caught up! No revisions due.</p>
              </div>
            )}
          </div>
        </section>

        <section className={styles.subjects}>
          <h2 className={styles.title}>
            <BookOpen size={22} className={styles.titleIcon} />
            Available Subjects
          </h2>
          <div className={styles.subjectGrid}>
            {data?.available_subjects.map((s) => (
              <Card 
                key={s.code} 
                className={styles.subjectCard}
                onClick={() => navigate(`/chat?subject=${s.code}`)}
              >
                <div className={styles.subjectIcon}>
                  {s.code === 'POLITY' ? '🏛️' : '📚'}
                </div>
                <div className={styles.subjectInfo}>
                  <strong>{s.name}</strong>
                  <p>{s.topics_count} Topics Covered</p>
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
