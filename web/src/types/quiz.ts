export interface MCQResponse {
  id: string;
  stem: string;
  options: string[];
}

export interface QuizResponse {
  assessment_id: string;
  questions: MCQResponse[];
}

export interface UserAnswerRequest {
  question_id: string;
  selected_option: string;
}

export interface QuizSubmissionRequest {
  user_id: string;
  answers: UserAnswerRequest[];
}

export interface MCQResult {
  question_id: string;
  is_correct: boolean;
  correct_option: string;
  user_option: string | null;
  explanation: string;
}

export interface QuizSubmissionResponse {
  score: number;
  total: number;
  percentage: number;
  feedback: string;
  results: MCQResult[];
  weak_topics: string[];
}
