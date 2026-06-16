export interface ProgressItem {
  topic_name: string;
  topic_slug: string;
  completion_percent: number;
  confidence_score: number;
  last_studied_at: string;
}

export interface RevisionItem {
  task_id: string;
  topic_name: string;
  topic_slug: string;
  due_at: string;
  reason: string;
}

export interface SubjectSummary {
  code: string;
  name: string;
  topics_count: number;
}

export interface UserDashboard {
  user_id: string;
  progress: ProgressItem[];
  due_revisions: RevisionItem[];
  available_subjects: SubjectSummary[];
}
