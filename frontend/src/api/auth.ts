import { apiPost, apiGet } from './client'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  username: string
  email: string
  created_at: string
}

export function register(username: string, email: string, password: string): Promise<UserResponse> {
  return apiPost('/api/auth/register', { username, email, password })
}

export function login(username: string, password: string): Promise<TokenResponse> {
  return apiPost('/api/auth/login', { username, password })
}

export function refresh(refreshToken: string): Promise<TokenResponse> {
  return apiPost('/api/auth/refresh', { refresh_token: refreshToken })
}

export function getMe(): Promise<UserResponse> {
  return apiGet('/api/auth/me')
}
