import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { StatusBadge } from '../components/StatusBadge';
import { apiRequest } from '../lib/api';
import {
  INQUIRY_CATEGORY_LABEL,
  INQUIRY_STATUS_LABEL,
  type AdminInquiryListResponse,
  type InquiryCategory,
  type InquiryStatus,
} from '../types';

const STATUS_FILTERS: Array<{ value: InquiryStatus | 'all'; label: string }> = [
  { value: 'all', label: '전체' },
  { value: 'pending', label: '답변 대기' },
  { value: 'completed', label: '답변 완료' },
];

const CATEGORY_OPTIONS: Array<{ value: InquiryCategory | 'all'; label: string }> = [
  { value: 'all', label: '전체 분류' },
  ...(Object.entries(INQUIRY_CATEGORY_LABEL) as Array<[InquiryCategory, string]>).map(
    ([value, label]) => ({ value, label }),
  ),
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

export function InquiryListPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const rawStatus = params.get('status');
  const status = STATUS_FILTERS.some((item) => item.value === rawStatus) ? rawStatus! : 'all';
  const rawCategory = params.get('category');
  const category = CATEGORY_OPTIONS.some((item) => item.value === rawCategory)
    ? rawCategory!
    : 'all';
  const [data, setData] = useState<AdminInquiryListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ sortBy: 'created_at', order: 'desc', limit: '100' });
    if (status !== 'all') query.set('status', status);
    if (category !== 'all') query.set('category', category);
    apiRequest<AdminInquiryListResponse>(`/admin/inquiries?${query}`, {
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
  }, [status, category]);

  const items = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    const filtered = keyword
      ? (data?.items ?? []).filter((item) =>
          [item.title, item.askerNickname].join(' ').toLowerCase().includes(keyword),
        )
      : (data?.items ?? []);
    // 미답변을 먼저, 그 안에서는 서버가 준 순서(최신순)를 유지한다.
    return [...filtered].sort((a, b) => {
      if (a.status === b.status) return 0;
      return a.status === 'pending' ? -1 : 1;
    });
  }, [data, search]);

  const pendingCount = useMemo(
    () => (data?.items ?? []).filter((item) => item.status === 'pending').length,
    [data],
  );

  const updateParam = (key: string, value: string) => {
    setLoading(true);
    setError('');
    const next = new URLSearchParams(params);
    if (value === 'all') next.delete(key);
    else next.set(key, value);
    setParams(next);
  };

  return (
    <div className="list-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">고객지원</p>
          <h1>1:1 문의</h1>
          <p>사용자가 보낸 문의를 확인하고 답변합니다.</p>
        </div>
        <div className="summary-card">
          {pendingCount > 0 ? (
            <>
              <span>답변 대기</span>
              <strong className="count-attention">{pendingCount}</strong>
              <small>/ {data?.total ?? 0}건</small>
            </>
          ) : (
            <>
              <span>현재 조건</span>
              <strong>{data?.total ?? 0}</strong>
              <small>건의 문의</small>
            </>
          )}
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
                placeholder="제목·문의자 검색"
              />
            </label>
            <select
              value={category}
              onChange={(event) => updateParam('category', event.target.value)}
            >
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && <div className="inline-alert error">{error}</div>}
        {loading ? (
          <div className="table-state"><span className="spinner" />목록을 불러오는 중이에요.</div>
        ) : items.length === 0 ? (
          <div className="table-state empty">
            <strong>조건에 맞는 문의가 없어요.</strong>
            <span>다른 상태나 검색어를 확인해 보세요.</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>상태</th>
                  <th>분류</th>
                  <th>제목</th>
                  <th>문의자</th>
                  <th>작성일</th>
                  <th>답변일</th>
                  <th><span className="sr-only">상세 보기</span></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className={item.status === 'pending' ? 'row-attention' : ''}
                    onClick={() => navigate(`/inquiries/${item.id}`)}
                  >
                    <td>
                      <StatusBadge status={item.status} labels={INQUIRY_STATUS_LABEL} />
                    </td>
                    <td>
                      <span className="kind-label">{INQUIRY_CATEGORY_LABEL[item.category]}</span>
                    </td>
                    <td className="story-cell"><strong>{item.title}</strong></td>
                    <td>{item.askerNickname}</td>
                    <td className="date-cell">{formatDate(item.createdAt)}</td>
                    <td className="date-cell">{formatDate(item.answeredAt)}</td>
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
