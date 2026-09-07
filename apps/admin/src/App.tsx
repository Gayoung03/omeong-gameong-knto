import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { useAuth } from './auth/useAuth';
import { AppLayout } from './components/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { StoryDetailPage } from './pages/StoryDetailPage';
import { StoryListPage } from './pages/StoryListPage';

function ProtectedLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return <div className="app-loading"><span className="spinner" />관리자 권한을 확인하는 중이에요.</div>;
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <AppLayout />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/stories" element={<StoryListPage />} />
        <Route path="/stories/:storyId" element={<StoryDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/stories" replace />} />
    </Routes>
  );
}
