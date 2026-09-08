import { NavLink, Outlet } from 'react-router-dom';

import brandSymbol from '../assets/brand-symbol.png';
import { useAuth } from '../auth/useAuth';
import { usePendingInquiryCount } from '../lib/usePendingInquiryCount';

export function AppLayout() {
  const { user, logout } = useAuth();
  const pendingInquiries = usePendingInquiryCount();

  return (
    <div className="admin-shell">
      <aside className="sidebar">
        <div className="brand">
          <img className="brand-logo" src={brandSymbol} alt="" aria-hidden="true" />
          <div>
            <strong>오멍가멍</strong>
            <span>운영 센터</span>
          </div>
        </div>
        <nav className="side-nav" aria-label="관리자 메뉴">
          <p className="nav-group">콘텐츠</p>
          <NavLink to="/stories" className={({ isActive }) => (isActive ? 'active' : '')}>
            <span className="nav-icon" aria-hidden="true">▦</span>
            여행 이야기
          </NavLink>
          <p className="nav-group">고객지원</p>
          <NavLink to="/inquiries" className={({ isActive }) => (isActive ? 'active' : '')}>
            <span className="nav-icon" aria-hidden="true">✉</span>
            1:1 문의
            {pendingInquiries !== null && pendingInquiries > 0 && (
              <span className="nav-badge" aria-label={`미답변 ${pendingInquiries}건`}>
                {pendingInquiries > 99 ? '99+' : pendingInquiries}
              </span>
            )}
          </NavLink>
          <NavLink to="/notices" className={({ isActive }) => (isActive ? 'active' : '')}>
            <span className="nav-icon" aria-hidden="true">◈</span>
            공지사항
          </NavLink>
          <span className="nav-disabled" aria-disabled="true">
            <span className="nav-icon" aria-hidden="true">◇</span>
            품질 검증
            <small>다음 작업</small>
          </span>
        </nav>
        <div className="sidebar-foot">
          <span>관리자 전용</span>
          <small>모든 변경은 이력으로 남아요.</small>
        </div>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <div className="environment-pill">
            <span /> Editorial Console
          </div>
          <div className="admin-profile">
            <span className="avatar">{user?.nickname.slice(0, 1)}</span>
            <div>
              <strong>{user?.nickname}</strong>
              <span>{user?.email}</span>
            </div>
            <button type="button" onClick={logout}>로그아웃</button>
          </div>
        </header>
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
