import type { UserDashboard } from '../types/learning';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Mock user ID for MVP
export const MOCK_USER_ID = '00000000-0000-0000-0000-000000000000';

export async function getDashboard(userId: string = MOCK_USER_ID): Promise<UserDashboard> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}/dashboard`);
  if (!response.ok) {
    throw new Error('Failed to fetch dashboard data');
  }
  return response.json();
}
