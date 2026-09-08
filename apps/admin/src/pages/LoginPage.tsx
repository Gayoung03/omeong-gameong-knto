import { useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import brandSymbol from '../assets/brand-symbol.png';
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
          <img className="brand-logo" src={brandSymbol} alt="오멍가멍" />
          <strong>오멍가멍</strong>
        </div>
        <div>
          <p className="eyebrow">OMEONG GAMEONG ADMIN</p>
          <h1>오멍가멍 운영을<br />한곳에서 돌봐요.</h1>
          <p>여행 이야기 검수부터 고객 문의 응대, 공지 발행까지<br className="desktop-only" /> 오멍가멍 서비스 운영을 이 화면에서 관리합니다.</p>
        </div>
        <div className="login-orbit" aria-hidden="true">
          <span>여행 이야기</span><span>1:1 문의</span><span>공지사항</span>
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
