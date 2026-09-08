import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { StatusBadge } from '../components/StatusBadge';
import { apiRequest } from '../lib/api';
import type { StoryListResponse, StoryStatus } from '../types';

const STATUS_FILTERS: Array<{ value: StoryStatus | 'all'; label: string }> = [
  { value: 'all', label: '전체' },
  { value: 'draft', label: '초안' },
  { value: 'published', label: '게시 중' },
  { value: 'archived', label: '보관' },
];

const KIND_LABEL = {
  event: '행사',
  weather: '날씨',
  story: '이야기',
  guide: '가이드',
};

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

export function StoryListPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const rawStatus = params.get('status');
  const status = STATUS_FILTERS.some((item) => item.value === rawStatus) ? rawStatus! : 'all';
  const sortBy = params.get('sortBy') === 'published_at' ? 'published_at' : 'collected_at';
  const [data, setData] = useState<StoryListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ sortBy, order: 'desc', limit: '100' });
    if (status !== 'all') query.set('status', status);
    apiRequest<StoryListResponse>(`/admin/editorial-stories?${query}`, {
      signal: controller.signal,
    })
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
  }, [sortBy, status]);

  const items = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return data?.items ?? [];
    return (data?.items ?? []).filter((item) =>
      [item.cardTitle, item.title, item.category, ...item.sourceNames]
        .join(' ')
        .toLowerCase()
        .includes(keyword),
    );
  }, [data, search]);

  const updateParam = (key: string, value: string) => {
    setLoading(true);
    setError('');
    const next = new URLSearchParams(params);
    if (value === 'all' && key === 'status') next.delete(key);
    else next.set(key, value);
    setParams(next);
  };

  return (
    <div className="list-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">콘텐츠 운영</p>
          <h1>여행 이야기</h1>
          <p>비짓제주에서 수집한 초안을 확인하고 승인합니다.</p>
        </div>
        <div className="summary-card">
          <span>현재 조건</span>
          <strong>{data?.total ?? 0}</strong>
          <small>개의 이야기</small>
        </div>
      </div>

      <section className="content-card list-card">
        <div className="list-toolbar">
          <div className="status-tabs" role="tablist" aria-label="상태 필터">
            {STATUS_FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={status === item.value ? 'active' : ''}
                onClick={() => updateParam('status', item.value)}
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
                placeholder="제목·카테고리 검색"
              />
            </label>
            <select value={sortBy} onChange={(event) => updateParam('sortBy', event.target.value)}>
              <option value="collected_at">최신 수집순</option>
              <option value="published_at">최신 게시순</option>
            </select>
          </div>
        </div>

        {error && <div className="inline-alert error">{error}</div>}
        {loading ? (
          <div className="table-state"><span className="spinner" />목록을 불러오는 중이에요.</div>
        ) : items.length === 0 ? (
          <div className="table-state empty">
            <strong>조건에 맞는 이야기가 없어요.</strong>
            <span>다른 상태나 검색어를 확인해 보세요.</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>상태</th>
                  <th>이야기</th>
                  <th>종류 / 카테고리</th>
                  <th>출처</th>
                  <th>수집일</th>
                  <th>게시일</th>
                  <th><span className="sr-only">상세 보기</span></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} onClick={() => navigate(`/stories/${item.id}`)}>
                    <td><StatusBadge status={item.status} /></td>
                    <td className="story-cell">
                      <strong>{item.cardTitle}</strong>
                      <span>{item.title}</span>
                    </td>
                    <td>
                      <span className="kind-label">{KIND_LABEL[item.kind]}</span>
                      <span className="muted-block">{item.category}</span>
                    </td>
                    <td>
                      <span className="source-label">{item.sourceNames.join(', ') || '—'}</span>
                    </td>
                    <td className="date-cell">{formatDate(item.collectedAt)}</td>
                    <td className="date-cell">{formatDate(item.publishedAt)}</td>
                    <td><button className="row-arrow" type="button" aria-label={`${item.cardTitle} 상세 보기`}>→</button></td>
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
