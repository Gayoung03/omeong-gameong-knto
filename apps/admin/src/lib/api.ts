const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
).replace(/\/$/, '');

const ACCESS_TOKEN_KEY = 'omeong-admin-access-token';
const REFRESH_TOKEN_KEY = 'omeong-admin-refresh-token';

interface TokenResponse {
  accessToken: string;
  refreshToken: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

function accessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function hasAdminSession(): boolean {
  return Boolean(accessToken());
}

export function saveAdminSession(tokens: TokenResponse): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
}

export function clearAdminSession(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string | Array<{ msg?: string }> };
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg).filter(Boolean).join(', ');
    }
  } catch {
    // JSON이 아닌 에러는 상태 문구로 대체한다.
  }
  return `요청을 처리하지 못했습니다 (${response.status})`;
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return false;

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken }),
  });
  if (!response.ok) return false;
  const tokens = (await response.json()) as TokenResponse;
  saveAdminSession(tokens);
  return true;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set('Content-Type', 'application/json');
  const token = accessToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401 && retry && (await refreshAccessToken())) {
    return apiRequest<T>(path, init, false);
  }
  if (!response.ok) {
    if (response.status === 401) {
      clearAdminSession();
      window.dispatchEvent(new Event('omeong-admin-unauthorized'));
    }
    throw new ApiError(response.status, await errorMessage(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function loginRequest(email: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return (await response.json()) as TokenResponse;
}
