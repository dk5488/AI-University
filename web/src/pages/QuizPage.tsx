import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { generateQuiz, submitQuiz } from '../api/quiz';
import { MOCK_USER_ID } from '../api/learning';
import Card from '../components/atoms/Card';
import { CheckCircle, XCircle, ChevronRight, GraduationCap, Clock, AlertTriangle, Calendar, ArrowLeft } from 'lucide-react';
import styles from './QuizPage.module.css';

import { QuizResponse, QuizSubmissionRequest, QuizSubmissionResponse, MCQResult } from '../types/quiz';

const QuizPage: React.FC = () => {
  const { subjectCode, topicSlug } = useParams<{ subjectCode: string; topicSlug: string }>();
  const navigate = useNavigate();
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isFinished, setIsFinished] = useState(false);
  const [secondsElapsed, setSecondsElapsed] = useState(0);
  const [showConfirm, setShowConfirm] = useState(false);

  const { data: quizData, isLoading: isQuizLoading } = useQuery<QuizResponse>({
    queryKey: ['quiz', subjectCode, topicSlug],
    queryFn: () => generateQuiz(subjectCode!, topicSlug!),
    enabled: !!subjectCode && !!topicSlug,
  });

  const mutation = useMutation<QuizSubmissionResponse, Error, QuizSubmissionRequest>({
    mutationFn: (results) => submitQuiz(quizData!.assessment_id, results),
    onSuccess: () => {
      setIsFinished(true);
    },
  });

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (!isFinished && !isQuizLoading && !showConfirm) {
      interval = setInterval(() => {
        setSecondsElapsed((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isFinished, isQuizLoading, showConfirm]);

  if (isQuizLoading) return <div className={styles.loading}>Preparing your examination papers...</div>;
  if (!quizData) return <div className={styles.error}>Error loading examination.</div>;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const currentQuestion = quizData.questions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === quizData.questions.length - 1;

  const handleOptionSelect = (option: string) => {
    setAnswers({ ...answers, [currentQuestion.id]: option });
  };

  const handleSubmit = () => {
    const submission = {
      user_id: MOCK_USER_ID,
      answers: Object.entries(answers).map(([id, opt]) => ({
        question_id: id,
        selected_option: opt,
      })),
    };
    mutation.mutate(submission);
  };

  if (isFinished && mutation.data) {
    const results = mutation.data;
    return (
      <div className={styles.resultsContainer}>
        <div className={styles.resultsHeaderArea}>
          <GraduationCap size={48} className={styles.goldIcon} />
          <h1>Examination Report</h1>
          <p>Candidate Performance Analysis</p>
        </div>

        <div className={styles.resultsGrid}>
          <Card className={styles.scoreCard}>
            <div className={styles.analyticalScore}>
              <div className={styles.scoreCircle}>
                <span className={styles.actualScore}>{results.score}</span>
                <span className={styles.totalScore}>/ {results.total}</span>
              </div>
              <div className={styles.percentageBadge}>{results.percentage}% Accuracy</div>
            </div>
            <div className={styles.timeInfo}>
              <Clock size={16} /> Time Taken: {formatTime(secondsElapsed)}
            </div>
          </Card>

          <Card className={styles.mentorCard}>
            <h3><Sparkles size={18} /> Mentor's Feedback</h3>
            <p className={styles.feedbackText}>{results.feedback}</p>
            {results.weak_topics.length > 0 && (
              <div className={styles.weakTopics}>
                <label>Focus Areas:</label>
                <div className={styles.tags}>
                  {results.weak_topics.map(t => <span key={t} className={styles.tag}>{t}</span>)}
                </div>
              </div>
            )}
          </Card>

          {results.weak_topics.length > 0 && (
            <Card className={styles.revisionCard}>
              <h3><Calendar size={18} /> Scheduled Revisions</h3>
              <p>Based on your performance, the following sessions have been scheduled:</p>
              <ul className={styles.revisionList}>
                {results.weak_topics.map((topic, i) => (
                  <li key={i}>
                    <strong>{topic}</strong> Review
                  </li>
                ))}
              </ul>
              <div className={styles.revisionNote}>
                Automated reminders will appear on your dashboard.
              </div>
            </Card>
          )}
        </div>

        <div className={styles.reviewSection}>
          <h2>Detailed Item Analysis</h2>
          <div className={styles.reviewList}>
            {results.results.map((r: MCQResult, i: number) => (
              <div key={i} className={`${styles.reviewItem} ${r.is_correct ? styles.correctReview : styles.incorrectReview}`}>
                <div className={styles.reviewMain}>
                  <div className={styles.reviewLabel}>
                    {r.is_correct ? <CheckCircle size={20} /> : <XCircle size={20} />}
                    <span>Question {i + 1}</span>
                  </div>
                  <p className={styles.reviewExplanation}>{r.explanation}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.resultsActions}>
          <button className={styles.doneButton} onClick={() => navigate('/')}>
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (showConfirm) {
    const unansweredCount = quizData.questions.length - Object.keys(answers).length;
    return (
      <div className={styles.confirmOverlay}>
        <Card className={styles.confirmCard}>
          <AlertTriangle size={48} color="var(--color-warning)" />
          <h2>Confirm Submission</h2>
          <p>You have completed the examination. Are you ready to submit your answers for evaluation?</p>
          {unansweredCount > 0 && (
            <div className={styles.unansweredWarning}>
              Note: You have {unansweredCount} unanswered questions.
            </div>
          )}
          <div className={styles.confirmActions}>
            <button className={styles.backButton} onClick={() => setShowConfirm(false)}>
              <ArrowLeft size={16} /> Go Back
            </button>
            <button 
              className={styles.submitFinalButton} 
              onClick={handleSubmit}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Evaluating...' : 'Submit Now'}
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className={styles.examContainer}>
      <header className={styles.examHeader}>
        <div className={styles.examInfo}>
          <h1>{topicSlug?.replace(/-/g, ' ')}</h1>
          <div className={styles.examMeta}>
            <span className={styles.badge}>UPSC Standard</span>
            <span className={styles.timer}>
              <Clock size={16} /> {formatTime(secondsElapsed)}
            </span>
          </div>
        </div>
        <div className={styles.progressTracker}>
          <span>Question {currentQuestionIndex + 1} of {quizData.questions.length}</span>
          <div className={styles.progressBar}>
            <div 
              className={styles.progressFill} 
              style={{ width: `${((currentQuestionIndex + 1) / quizData.questions.length) * 100}%` }}
            />
          </div>
        </div>
      </header>

      <div className={styles.questionArea}>
        <Card className={styles.questionCard}>
          <p className={styles.stem}>{currentQuestion.stem}</p>
          <div className={styles.options}>
            {currentQuestion.options.map((opt, i) => (
              <button 
                key={i}
                className={`${styles.option} ${answers[currentQuestion.id] === opt ? styles.selected : ''}`}
                onClick={() => handleOptionSelect(opt)}
              >
                <span className={styles.optionLabel}>{String.fromCharCode(65 + i)}</span>
                <span className={styles.optionText}>{opt}</span>
              </button>
            ))}
          </div>
        </Card>
      </div>

      <footer className={styles.examFooter}>
        <button 
          className={styles.prevButton} 
          onClick={() => setCurrentQuestionIndex(prev => prev - 1)}
          disabled={currentQuestionIndex === 0}
        >
          Previous
        </button>
        {isLastQuestion ? (
          <button 
            className={styles.submitButton}
            onClick={() => setShowConfirm(true)}
          >
            Finish Examination
          </button>
        ) : (
          <button 
            className={styles.nextButton}
            disabled={!answers[currentQuestion.id]}
            onClick={() => setCurrentQuestionIndex(prev => prev + 1)}
          >
            Next Question <ChevronRight size={18} />
          </button>
        )}
      </footer>
    </div>
  );
};

export default QuizPage;
