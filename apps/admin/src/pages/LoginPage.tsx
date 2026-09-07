import { useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/stories" replace />;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await login(email, password);
      const from = (location.state as { from?: string } | null)?.from ?? '/stories';
      navigate(from, { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '로그인을 확인해 주세요.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="login-brand">
          <span className="brand-mark">오</span>
          <strong>오멍가멍</strong>
        </div>
        <div>
          <p className="eyebrow">OMEONG GAMEONG ADMIN</p>
          <h1>좋은 제주 이야기를<br />안심하고 전해요.</h1>
          <p>수집된 원문을 확인하고, 오멍가멍의 말투로 다듬어<br className="desktop-only" /> 승인하는 콘텐츠 운영 공간입니다.</p>
        </div>
        <div className="login-orbit" aria-hidden="true">
          <span>원문</span><span>검수</span><span>게시</span>
        </div>
      </section>
      <section className="login-panel">
        <form className="login-card" onSubmit={handleSubmit}>
          <div>
            <p className="eyebrow">관리자 로그인</p>
            <h2>다시 만나서 반가워요</h2>
            <p>관리자 권한이 부여된 계정으로 로그인해 주세요.</p>
          </div>
          <label>
            이메일
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@example.com"
              autoComplete="username"
              required
            />
          </label>
          <label>
            비밀번호
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="비밀번호를 입력하세요"
              autoComplete="current-password"
              required
            />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button button-primary login-button" type="submit" disabled={submitting}>
            {submitting ? '확인 중…' : '운영 센터 입장'}
          </button>
          <small className="login-security">권한이 없는 계정은 로그인할 수 없습니다.</small>
        </form>
      </section>
    </main>
  );
}
