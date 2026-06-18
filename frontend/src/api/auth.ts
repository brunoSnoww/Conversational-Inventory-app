import { apiFetch } from './client';
import type { AuthSession } from './types';

type AuthResponseDto = {
  user_id: string;
  email: string;
  access: string;
  refresh: string;
};

function parseAuthResponse(data: AuthResponseDto): AuthSession {
  if (typeof data.user_id !== 'string' || !data.user_id) {
    throw new Error('Auth response missing user_id');
  }
  return {
    userId: data.user_id,
    email: data.email,
    access: data.access,
    refresh: data.refresh,
  };
}

export async function register(email: string, password: string): Promise<AuthSession> {
  const data = await apiFetch<AuthResponseDto>('/api/auth/register/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  return parseAuthResponse(data);
}

export async function login(email: string, password: string): Promise<AuthSession> {
  const data = await apiFetch<AuthResponseDto>('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  return parseAuthResponse(data);
}
