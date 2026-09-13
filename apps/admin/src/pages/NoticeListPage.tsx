import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { StatusBadge } from '../components/StatusBadge';
import { apiRequest } from '../lib/api';
import { NOTICE_STATUS_LABEL, noticeDisplayStatus } from '../lib/notice';
import type { AdminNoticeListItem, AdminNoticeListResponse, NoticeFilter } from '../types';

const FILTERS: Array<{ value: NoticeFilter; label: string }> = [
  { value: 'all', label: '전체' },
  { value: 'announced', label: '발송 완료' },
  { value: 'draft', label: '초안' },
];

function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function NoticeListPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const rawFilter = params.get('filter');
  const filter = (FILTERS.some((f) => f.value === rawFilter) ? rawFilter : 'all') as NoticeFilter;
  const [data, setData] = useState<AdminNoticeListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ limit: '100' });
    if (filter !== 'all') query.set('filter', filter);
    apiRequest<AdminNoticeListResponse>(`/admin/notices?${query}`, { signal: controller.signal })
      .then(setData)
      .catch((caught) => {
        if ((caught as Error).name !== 'AbortError') {
          setError(caught instanceof Error ? caught.message : '목록을 불러오지 못했습니다.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [filter]);

  const items = useMemo<AdminNoticeListItem[]>(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return data?.items ?? [];
    return (data?.items ?? []).filter((item) => item.title.toLowerCase().includes(keyword));
  }, [data, search]);

  const updateFilter = (value: string) => {
    setLoading(true);
    setError('');
    const next = new URLSearchParams(params);
    if (value === 'all') next.delete('filter');
    else next.set('filter', value);
    setParams(next);
  };

  return (
    <div className="list-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">고객지원</p>
          <h1>공지사항</h1>
          <p>공지를 작성하고 전체 사용자에게 발행합니다.</p>
        </div>
        <button className="button button-primary" type="button" onClick={() => navigate('/notices/new')}>
          새 공지
        </button>
      </div>

      <section className="content-card list-card">
        <div className="list-toolbar">
          <div className="status-tabs" role="tablist" aria-label="발행 상태 필터">
            {FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={filter === item.value ? 'active' : ''}
                onClick={() => updateFilter(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="toolbar-controls">
            <label className="search-box">
              <span aria-hidden="true">⌕</span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="제목 검색"
              />
            </label>
          </div>
        </div>

        {error && <div className="inline-alert error">{error}</div>}
        {loading ? (
          <div className="table-state"><span className="spinner" />목록을 불러오는 중이에요.</div>
        ) : items.length === 0 ? (
          <div className="table-state empty">
            <strong>공지가 없어요.</strong>
            <span>‘새 공지’로 첫 공지를 작성해 보세요.</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>상태</th>
                  <th>제목</th>
                  <th>고정</th>
                  <th>게시일</th>
                  <th>작성일</th>
                  <th><span className="sr-only">상세 보기</span></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} onClick={() => navigate(`/notices/${item.id}`)}>
                    <td>
                      <StatusBadge status={noticeDisplayStatus(item)} labels={NOTICE_STATUS_LABEL} />
                    </td>
                    <td className="story-cell"><strong>{item.title}</strong></td>
                    <td>{item.isPinned ? '고정' : '—'}</td>
                    <td className="date-cell">{formatDate(item.publishedAt)}</td>
                    <td className="date-cell">{formatDate(item.createdAt)}</td>
                    <td>
                      <button className="row-arrow" type="button" aria-label={`${item.title} 상세 보기`}>→</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
