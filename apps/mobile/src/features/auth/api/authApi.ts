import { apiClient } from '@/src/services/apiClient';

/**
 * 인증 API 호출 계층.
 *
 * 응답 타입은 `docs/api/auth.md` 예시 그대로(camelCase)다. 서버가 DB 컬럼명을
 * camelCase 로만 바꿔 내려주므로 앱은 받은 모양을 그대로 쓴다.
 */

export type AuthProvider = 'local' | 'kakao' | 'apple' | 'google';

export type AuthUser = {
  id: string;
  email: string | null;
  nickname: string;
  profileImageUrl: string | null;
  authProvider: AuthProvider;
  status: 'active' | 'deleted';
};

export type TokenResponse = {
  accessToken: string;
  refreshToken: string;
  tokenType: 'bearer';
  expiresIn: number;
  user: AuthUser;
};

export type RefreshResponse = {
  accessToken: string;
  refreshToken: string;
  tokenType: 'bearer';
  expiresIn: number;
};

export type SocialLoginResponse = TokenResponse & { isNewUser: boolean };

export type LinkRequiredResponse = {
  linkRequired: true;
  linkToken: string;
  maskedEmail: string;
};

/** 교환 결과는 로그인 완료(토큰) 또는 연동 확인 필요(linkRequired) 둘 중 하나다. */
export type SocialExchangeResponse = SocialLoginResponse | LinkRequiredResponse;

export type TravelPreferenceResponse = {
  defaultPace: string | null;
  defaultTransport: string | null;
  departureLocation: string | null;
  preferredDurationDays: number | null;
  companionCount: number;
  preferredTags: string[] | null;
  updatedAt: string | null;
};

export type SignupPetPayload = {
  name: string;
  species: 'dog' | 'cat' | 'other';
  speciesDetail?: string;
  size?: 'small' | 'medium' | 'large';
};

export type TravelPreferencePayload = {
  defaultPace?: string;
  defaultTransport?: string;
  departureLocation?: string;
  preferredDurationDays?: number;
  companionCount?: number;
  preferredTags?: string[];
};

export type SignupPayload = {
  email: string;
  password: string;
  nickname: string;
  pet?: SignupPetPayload;
  travelPreference?: TravelPreferencePayload;
};

export async function signup(payload: SignupPayload): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/signup', payload);
  return data;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', { email, password });
  return data;
}

export async function refresh(refreshToken: string): Promise<RefreshResponse> {
  const { data } = await apiClient.post<RefreshResponse>('/auth/refresh', { refreshToken });
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout');
}

export async function checkEmail(email: string): Promise<boolean> {
  const { data } = await apiClient.get<{ available: boolean }>('/auth/check-email', {
    params: { email },
  });
  return data.available;
}

export async function socialExchange(code: string): Promise<SocialExchangeResponse> {
  const { data } = await apiClient.post<SocialExchangeResponse>('/auth/social/exchange', { code });
  return data;
}

export async function socialComplete(
  linkToken: string,
  action: 'link' | 'separate',
  password?: string,
): Promise<SocialLoginResponse> {
  const { data } = await apiClient.post<SocialLoginResponse>('/auth/social/complete', {
    linkToken,
    action,
    password,
  });
  return data;
}

export async function deleteAccount(password: string): Promise<void> {
  // axios 의 delete 는 body 를 data 옵션으로 싣는다.
  await apiClient.delete('/users/me', { data: { password } });
}

export async function getTravelPreference(): Promise<TravelPreferenceResponse> {
  const { data } = await apiClient.get<TravelPreferenceResponse>('/users/me/travel-preference');
  return data;
}

export async function putTravelPreference(
  payload: TravelPreferencePayload,
): Promise<TravelPreferenceResponse> {
  const { data } = await apiClient.put<TravelPreferenceResponse>(
    '/users/me/travel-preference',
    payload,
  );
  return data;
}
