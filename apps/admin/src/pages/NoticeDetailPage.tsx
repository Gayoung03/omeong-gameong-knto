import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { ConfirmModal } from '../components/ConfirmModal';
import { StatusBadge } from '../components/StatusBadge';
import { apiRequest } from '../lib/api';
import { NOTICE_STATUS_LABEL, noticeDisplayStatus } from '../lib/notice';
import type { AdminNoticeDetail, NoticeUpdatePayload } from '../types';

interface NoticeForm {
  title: string;
  content: string;
  isPinned: boolean;
  isActive: boolean;
  publishedAt: string;
}

type PendingAction = 'publish' | 'toggle-active' | null;

const AUDIT_LABEL: Record<string, string> = {
  created: '초안 생성',
  updated: '내용 수정',
  published: '발행',
  unpublished: '게시 중단',
};

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

function toLocalDateTime(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toApiDateTime(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function noticeToForm(notice: AdminNoticeDetail): NoticeForm {
  return {
    title: notice.title,
    content: notice.content,
    isPinned: notice.isPinned,
    isActive: notice.isActive,
    publishedAt: toLocalDateTime(notice.publishedAt),
  };
}

const EMPTY_FORM: NoticeForm = {
  title: '',
  content: '',
  isPinned: false,
  isActive: false,
  publishedAt: '',
};

export function NoticeDetailPage() {
  const { noticeId } = useParams();
  const navigate = useNavigate();
  const isCreate = !noticeId;

  const [notice, setNotice] = useState<AdminNoticeDetail | null>(null);
  const [form, setForm] = useState<NoticeForm>(EMPTY_FORM);
  const [loading, setLoading] = useState(!isCreate);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [banner, setBanner] = useState('');
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);

  useEffect(() => {
    if (isCreate) return;
    const controller = new AbortController();
    apiRequest<AdminNoticeDetail>(`/admin/notices/${noticeId}`, { signal: controller.signal })
      .then((result) => {
        setNotice(result);
        setForm(noticeToForm(result));
      })
      .catch((caught) => {
        if ((caught as Error).name !== 'AbortError') {
          setError(caught instanceof Error ? caught.message : '공지를 불러오지 못했습니다.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [isCreate, noticeId]);

  const announced = Boolean(notice?.announcedAt);
  const dirty = useMemo(
    () => (notice ? JSON.stringify(noticeToForm(notice)) !== JSON.stringify(form) : true),
    [form, notice],
  );
  const canSubmit = form.title.trim().length > 0 && form.content.trim().length > 0;

  const updateField = <Key extends keyof NoticeForm>(key: Key, value: NoticeForm[Key]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setBanner('');
  };

  const handleCreate = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setError('');
    try {
      const created = await apiRequest<AdminNoticeDetail>('/admin/notices', {
        method: 'POST',
        body: JSON.stringify({
          title: form.title.trim(),
          content: form.content.trim(),
          isPinned: form.isPinned,
          publishedAt: toApiDateTime(form.publishedAt),
        }),
      });
      navigate(`/notices/${created.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '공지를 만들지 못했어요.');
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async () => {
    if (!notice || !canSubmit) return;
    setBusy(true);
    setError('');
    setBanner('');
    const payload: NoticeUpdatePayload = {};
    const base = noticeToForm(notice);
    if (form.title.trim() !== base.title) payload.title = form.title.trim();
    if (form.content.trim() !== base.content) payload.content = form.content.trim();
    if (form.isPinned !== base.isPinned) payload.isPinned = form.isPinned;
    if (form.isActive !== base.isActive) payload.isActive = form.isActive;
    if (form.publishedAt !== base.publishedAt) {
      const iso = toApiDateTime(form.publishedAt);
      if (iso) payload.publishedAt = iso;
    }
    try {
      const updated = await apiRequest<AdminNoticeDetail>(`/admin/notices/${notice.id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
      setNotice(updated);
      setForm(noticeToForm(updated));
      setBanner('변경 내용을 저장했어요.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '저장하지 못했어요.');
    } finally {
      setBusy(false);
    }
  };

  const runAction = async () => {
    if (!notice || !pendingAction) return;
    setBusy(true);
    setError('');
    try {
      let updated: AdminNoticeDetail;
      if (pendingAction === 'publish') {
        updated = await apiRequest<AdminNoticeDetail>(`/admin/notices/${notice.id}/publish`, {
          method: 'POST',
          body: JSON.stringify({ publishedAt: toApiDateTime(form.publishedAt) }),
        });
        setBanner('공지를 발행하고 전체 사용자에게 알림을 보냈어요.');
      } else {
        const path = notice.isActive ? 'unpublish' : 'publish';
        // 이미 발송된 공지의 재게시는 조용한 PATCH 로 처리한다(재발송 없음).
        updated = notice.isActive
          ? await apiRequest<AdminNoticeDetail>(`/admin/notices/${notice.id}/${path}`, {
              method: 'POST',
            })
          : await apiRequest<AdminNoticeDetail>(`/admin/notices/${notice.id}`, {
              method: 'PATCH',
              body: JSON.stringify({ isActive: true }),
            });
        setBanner(notice.isActive ? '공지 게시를 중단했어요.' : '공지를 다시 게시했어요.');
      }
      setNotice(updated);
      setForm(noticeToForm(updated));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '처리하지 못했어요.');
    } finally {
      setBusy(false);
      setPendingAction(null);
    }
  };

  if (loading) {
    return <div className="page-loading"><span className="spinner" />공지를 불러오는 중이에요.</div>;
  }
  if (!isCreate && !notice) {
    return (
      <div className="not-found">
        <h1>공지를 열 수 없어요.</h1>
        <p>{error || '삭제되었거나 접근할 수 없는 공지입니다.'}</p>
        <button className="button button-secondary" onClick={() => navigate('/notices')}>목록으로</button>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <div className="detail-topline">
        <div>
          <Link className="back-link" to="/notices">← 공지사항 목록</Link>
          <div className="detail-title-row">
            <h1>{isCreate ? '새 공지 작성' : notice!.title}</h1>
            {notice && (
              <StatusBadge
                status={noticeDisplayStatus(notice)}
                labels={NOTICE_STATUS_LABEL}
              />
            )}
          </div>
        </div>
        <div className="detail-actions">
          {isCreate ? (
            <button
              className="button button-primary"
              type="button"
              onClick={handleCreate}
              disabled={!canSubmit || busy}
            >
              {busy ? '저장 중…' : '초안 저장'}
            </button>
          ) : (
            <>
              <button
                className="button button-secondary"
                type="button"
                onClick={handleSave}
                disabled={!dirty || !canSubmit || busy}
              >
                {busy ? '저장 중…' : '변경 저장'}
              </button>
              {!announced ? (
                <button
                  className="button button-danger"
                  type="button"
                  onClick={() => setPendingAction('publish')}
                  disabled={dirty || busy}
                  title={dirty ? '먼저 변경 내용을 저장해 주세요.' : undefined}
                >
                  발행
                </button>
              ) : (
                <button
                  className={notice!.isActive ? 'button button-danger-outline' : 'button button-primary'}
                  type="button"
                  onClick={() => setPendingAction('toggle-active')}
                  disabled={busy}
                >
                  {notice!.isActive ? '게시 중단' : '다시 게시'}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {banner && <div className="inline-alert success">{banner}</div>}
      {error && <div className="inline-alert error">{error}</div>}
      {announced && (
        <div className="inline-alert neutral">
          발송 완료 · {formatDate(notice!.announcedAt)} — 이미 전체 사용자에게 알림이 전송된 공지예요.
          내용을 수정해도 다시 발송되지 않아요.
        </div>
      )}

      <div className="editor-layout">
        <div className="editor-main">
          <section className="content-card form-section">
            <div className="section-heading"><div><span>01</span><h2>공지 내용</h2></div></div>
            <div className="form-grid">
              <label className="full-width">
                제목 <span className="field-count">{form.title.length}/200</span>
                <input
                  value={form.title}
                  onChange={(event) => updateField('title', event.target.value)}
                  maxLength={200}
                />
              </label>
              <label className="full-width">
                본문
                <textarea
                  rows={10}
                  value={form.content}
                  onChange={(event) => updateField('content', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="content-card form-section">
            <div className="section-heading"><div><span>02</span><h2>노출 설정</h2></div></div>
            <div className="form-grid two-columns">
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={form.isPinned}
                  onChange={(event) => updateField('isPinned', event.target.checked)}
                />
                상단 고정
              </label>
              {!isCreate && announced && (
                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={form.isActive}
                    onChange={(event) => updateField('isActive', event.target.checked)}
                  />
                  사용자 앱에 노출
                </label>
              )}
              <label>
                게시 시각 <small>미래로 두면 사용자에게 숨겨져요</small>
                <input
                  type="datetime-local"
                  value={form.publishedAt}
                  onChange={(event) => updateField('publishedAt', event.target.value)}
                />
              </label>
            </div>
          </section>
        </div>

        <aside className="editor-aside">
          <section className="content-card aside-card review-guide">
            <p className="eyebrow">발행 안내</p>
            <h2>발행하면 되돌릴 수 없어요</h2>
            <p className="guide-note">
              ‘발행’은 전체 사용자에게 알림·푸시를 한 번 보냅니다. 발송 뒤에는 게시 중단만
              가능하고, 알림을 다시 보낼 수는 없어요. 발행 전 내용을 충분히 검토해 주세요.
            </p>
          </section>

          {notice && (
            <section className="content-card aside-card history-card">
              <p className="eyebrow">변경 이력</p>
              <h2>최근 운영 기록</h2>
              {notice.auditLogs.length === 0 ? (
                <p className="muted-text">아직 이력이 없어요.</p>
              ) : (
                <ol>
                  {notice.auditLogs.slice(0, 8).map((log) => (
                    <li key={log.id}>
                      <span className="history-dot" />
                      <div>
                        <strong>{AUDIT_LABEL[log.action] ?? log.action}</strong>
                        <small>{formatDate(log.createdAt)}</small>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          )}
        </aside>
      </div>

      {pendingAction === 'publish' && (
        <ConfirmModal
          open
          title="이 공지를 발행할까요?"
          description="전체 사용자에게 알림과 푸시가 한 번 발송돼요. 되돌릴 수 없어요."
          confirmLabel="발행하고 알림 발송"
          tone="danger"
          busy={busy}
          onCancel={() => setPendingAction(null)}
          onConfirm={runAction}
        />
      )}
      {pendingAction === 'toggle-active' && (
        <ConfirmModal
          open
          title={notice!.isActive ? '게시를 중단할까요?' : '다시 게시할까요?'}
          description={
            notice!.isActive
              ? '사용자 앱 공지 목록에서 즉시 사라져요. 알림은 다시 보내지 않아요.'
              : '사용자 앱 공지 목록에 다시 나타나요. 알림은 보내지 않아요.'
          }
          confirmLabel={notice!.isActive ? '게시 중단' : '다시 게시'}
          tone={notice!.isActive ? 'danger' : 'primary'}
          busy={busy}
          onCancel={() => setPendingAction(null)}
          onConfirm={runAction}
        />
      )}
    </div>
  );
}
