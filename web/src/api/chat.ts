import type { ChatResponse } from '../types/chat';
import { MOCK_USER_ID } from './learning';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export async function sendMessage(
  message: string, 
  userId: string = MOCK_USER_ID,
  sessionId?: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: userId,
      message,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to send message');
  }

  return response.json();
}
