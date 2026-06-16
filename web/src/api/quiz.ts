import type { QuizResponse, QuizSubmissionRequest, QuizSubmissionResponse } from '../types/quiz';
import { MOCK_USER_ID } from './learning';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export async function generateQuiz(
  subjectCode: string,
  topicSlug: string,
  userId: string = MOCK_USER_ID,
  count: number = 5
): Promise<QuizResponse> {
  const response = await fetch(
    `${API_BASE_URL}/subjects/${subjectCode}/topics/${topicSlug}/mcqs?user_id=${userId}&count=${count}`,
    { method: 'POST' }
  );

  if (!response.ok) {
    throw new Error('Failed to generate quiz');
  }

  return response.json();
}

export async function submitQuiz(
  assessmentId: string,
  request: QuizSubmissionRequest
): Promise<QuizSubmissionResponse> {
  const response = await fetch(`${API_BASE_URL}/assessments/${assessmentId}/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error('Failed to submit quiz');
  }

  return response.json();
}
