import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { generateQuiz, submitQuiz } from '../api/quiz';
import { MOCK_USER_ID } from '../api/learning';
import Card from '../components/atoms/Card';
import { CheckCircle, XCircle, ChevronRight, GraduationCap } from 'lucide-react';
import styles from './QuizPage.module.css';

const QuizPage: React.FC = () => {
  const { subjectCode, topicSlug } = useParams<{ subjectCode: string; topicSlug: string }>();
  const navigate = useNavigate();
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isFinished, setIsFinished] = useState(false);

  const { data: quizData, isLoading: isQuizLoading } = useQuery({
    queryKey: ['quiz', subjectCode, topicSlug],
    queryFn: () => generateQuiz(subjectCode!, topicSlug!),
    enabled: !!subjectCode && !!topicSlug,
  });

  const mutation = useMutation({
    mutationFn: (results: any) => submitQuiz(quizData!.assessment_id, results),
    onSuccess: () => {
      setIsFinished(true);
    },
  });

  if (isQuizLoading) return <div className={styles.loading}>Generating your examination paper...</div>;
  if (!quizData) return <div>Error loading quiz.</div>;

  const currentQuestion = quizData.questions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === quizData.questions.length - 1;

  const handleOptionSelect = (option: string) => {
    setAnswers({ ...answers, [currentQuestion.id]: option });
  };

  const handleNext = () => {
    if (isLastQuestion) {
      const submission = {
        user_id: MOCK_USER_ID,
        answers: Object.entries(answers).map(([id, opt]) => ({
          question_id: id,
          selected_option: opt,
        })),
      };
      mutation.mutate(submission);
    } else {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  if (isFinished && mutation.data) {
    const results = mutation.data;
    return (
      <div className={styles.results}>
        <Card className={styles.resultsCard}>
          <div className={styles.resultsHeader}>
            <GraduationCap size={48} color="var(--color-secondary)" />
            <h2>Examination Results</h2>
            <div className={styles.scoreCircle}>
              <span>{results.score}</span> / {results.total}
            </div>
            <p className={styles.percentage}>{results.percentage}%</p>
          </div>

          <div className={styles.feedback}>
            <h3>Mentor's Assessment</h3>
            <p>{results.feedback}</p>
          </div>

          <div className={styles.questionReview}>
            {results.results.map((r: any, i: number) => (
              <div key={i} className={styles.reviewItem}>
                <div className={styles.reviewStatus}>
                  {r.is_correct ? <CheckCircle color="var(--color-success)" /> : <XCircle color="var(--color-error)" />}
                  <strong>Question {i + 1}</strong>
                </div>
                <p className={styles.reviewExplanation}>{r.explanation}</p>
              </div>
            ))}
          </div>

          <button className={styles.doneButton} onClick={() => navigate('/')}>
            Return to Dashboard
          </button>
        </Card>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.quizHeader}>
        <h2>{topicSlug?.replace('-', ' ')} Quiz</h2>
        <span>Question {currentQuestionIndex + 1} of {quizData.questions.length}</span>
      </div>

      <Card className={styles.questionCard}>
        <p className={styles.stem}>{currentQuestion.stem}</p>
        <div className={styles.options}>
          {currentQuestion.options.map((opt, i) => (
            <button 
              key={i}
              className={`${styles.option} ${answers[currentQuestion.id] === opt ? styles.selected : ''}`}
              onClick={() => handleOptionSelect(opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      </Card>

      <button 
        className={styles.nextButton}
        disabled={!answers[currentQuestion.id] || mutation.isPending}
        onClick={handleNext}
      >
        {mutation.isPending ? 'Submitting...' : isLastQuestion ? 'Submit Exam' : 'Next Question'}
        {!mutation.isPending && <ChevronRight size={20} />}
      </button>
    </div>
  );
};

export default QuizPage;
