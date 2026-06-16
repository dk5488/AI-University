import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getDashboard } from '../api/learning';
import ProgressCard from '../components/molecules/ProgressCard';
import Card from '../components/atoms/Card';
import { AlertCircle, ArrowRight, BookOpen, GraduationCap, Clock } from 'lucide-react';
import styles from './DashboardPage.module.css';

import Skeleton from '../components/atoms/Skeleton';
import { useToast } from '../hooks/useToast';

const DashboardSkeleton: React.FC = () => (
  <div className={styles.container}>
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <Skeleton width={250} height={32} />
      </div>
      <div className={styles.grid}>
        {[1, 2, 3].map((i) => (
          <Card key={i} className={styles.skeletonCard}>
            <Skeleton width="60%" height={24} />
            <div style={{ marginTop: '20px' }}>
              <Skeleton width="100%" height={12} />
              <div style={{ marginTop: '12px' }}>
                <Skeleton width="100%" height={12} />
              </div>
            </div>
          </Card>
        ))}
      </div>
    </section>

    <div className={styles.bottomRow}>
      <section className={styles.revisions}>
        <Skeleton width={200} height={28} />
        <div className={styles.revisionList} style={{ marginTop: '16px' }}>
          {[1, 2].map((i) => (
            <div key={i} className={styles.revisionItem}>
              <div className={styles.revisionInfo}>
                <Skeleton width={40} height={40} circle />
                <div>
                  <Skeleton width={120} height={16} />
                  <div style={{ marginTop: '8px' }}>
                    <Skeleton width={180} height={12} />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.subjects}>
        <Skeleton width={200} height={28} />
        <div className={styles.subjectGrid} style={{ marginTop: '16px' }}>
          {[1, 2].map((i) => (
            <Card key={i} className={styles.subjectCard}>
              <Skeleton width={48} height={48} />
              <div>
                <Skeleton width={100} height={16} />
                <div style={{ marginTop: '8px' }}>
                  <Skeleton width={80} height={12} />
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </div>
  </div>
);

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => getDashboard(),
  });

  React.useEffect(() => {
    if (error) {
      showToast('Backend connection failed. Please check your local server.', 'error');
    }
  }, [error, showToast]);

  if (isLoading) return <DashboardSkeleton />;
  if (error) return (
    <div className={styles.error}>
      <AlertCircle size={48} />
      <p>Unable to retrieve study records. Ensure the FastAPI backend is running.</p>
    </div>
  );

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
