import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { ConfirmModal } from '../components/ConfirmModal';
import { StatusBadge } from '../components/StatusBadge';
import { apiRequest } from '../lib/api';
import { INQUIRIES_CHANGED_EVENT } from '../lib/usePendingInquiryCount';
import {
  INQUIRY_CATEGORY_LABEL,
  INQUIRY_STATUS_LABEL,
  type AdminInquiryDetail,
  type InquiryDraftResponse,
} from '../types';

type PendingAction = 'draft' | 'answer' | null;

const AUDIT_LABEL: Record<string, string> = { answered: '답변 등록' };
// AI 초안 생성은 한도 계산용으로 남길 뿐, 이력에는 보이지 않는다.
const HIDDEN_AUDIT_ACTIONS = new Set(['ai_drafted']);

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

export function InquiryDetailPage() {
  const { inquiryId } = useParams();
  const navigate = useNavigate();
  const [inquiry, setInquiry] = useState<AdminInquiryDetail | null>(null);
  const [answer, setAnswer] = useState('');
  const [draft, setDraft] = useState<InquiryDraftResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);

  useEffect(() => {
    if (!inquiryId) return;
    const controller = new AbortController();
    apiRequest<AdminInquiryDetail>(`/admin/inquiries/${inquiryId}`, { signal: controller.signal })
      .then((result) => {
        setInquiry(result);
        // 미답변이면 편집기를 인사말·맺음말이 채워진 템플릿으로 연다(수정 가능).
        setAnswer(result.answer ?? result.answerTemplate);
      })
      .catch((caught) => {
        if ((caught as Error).name !== 'AbortError') {
          setError(caught instanceof Error ? caught.message : '문의를 불러오지 못했습니다.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [inquiryId]);

  const editable = inquiry?.status === 'pending';
  // 템플릿 그대로(본문 안 채움)면 아직 답변할 게 없다고 본다.
  const written = useMemo(
    () =>
      Boolean(inquiry) &&
      answer.trim().length > 0 &&
      answer.trim() !== (inquiry?.answerTemplate ?? '').trim(),
    [answer, inquiry],
  );

  const generateDraft = async () => {
    if (!inquiry) return;
    setBusy(true);
    setError('');
    try {
      const result = await apiRequest<InquiryDraftResponse>(
        `/admin/inquiries/${inquiry.id}/draft-answer`,
        { method: 'POST' },
      );
      setDraft(result);
      setAnswer(result.reply);
      setNotice('AI 초안을 불러왔어요. 내용을 검토하고 다듬어 주세요.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'AI 초안 생성에 실패했어요.');
    } finally {
      setBusy(false);
      setPendingAction(null);
    }
  };

  const submitAnswer = async () => {
    if (!inquiry || !answer.trim()) return;
    setBusy(true);
    setError('');
    try {
      const updated = await apiRequest<AdminInquiryDetail>(
        `/admin/inquiries/${inquiry.id}/answer`,
        { method: 'POST', body: JSON.stringify({ answer: answer.trim() }) },
      );
      setInquiry(updated);
      setAnswer(updated.answer ?? '');
      setDraft(null);
      setNotice('답변을 등록했어요. 문의자에게 알림이 전송됐어요.');
      window.dispatchEvent(new Event(INQUIRIES_CHANGED_EVENT));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '답변을 등록하지 못했어요.');
    } finally {
      setBusy(false);
      setPendingAction(null);
    }
  };

  if (loading) {
    return <div className="page-loading"><span className="spinner" />문의를 불러오는 중이에요.</div>;
  }
  if (!inquiry) {
    return (
      <div className="not-found">
        <h1>문의를 열 수 없어요.</h1>
        <p>{error || '삭제되었거나 접근할 수 없는 문의입니다.'}</p>
        <button className="button button-secondary" onClick={() => navigate('/inquiries')}>목록으로</button>
      </div>
    );
  }

  const historyLogs = inquiry.auditLogs.filter(
    (log) => !HIDDEN_AUDIT_ACTIONS.has(log.action),
  );

  return (
    <div className="detail-page">
      <div className="detail-topline">
        <div>
          <Link className="back-link" to="/inquiries">← 1:1 문의 목록</Link>
          <div className="detail-title-row">
            <h1>{inquiry.title}</h1>
            <StatusBadge status={inquiry.status} labels={INQUIRY_STATUS_LABEL} />
          </div>
          <p className="story-slug">
            {INQUIRY_CATEGORY_LABEL[inquiry.category]} · {inquiry.asker.nickname}
            {inquiry.asker.email ? ` (${inquiry.asker.email})` : ''}
          </p>
        </div>
      </div>

      {notice && <div className="inline-alert success">{notice}</div>}
      {error && <div className="inline-alert error">{error}</div>}
      {!editable && (
        <div className="inline-alert neutral">
          답변이 등록된 문의는 읽기 전용입니다. 문의는 작성 후 수정할 수 없어요.
        </div>
      )}

      <div className="editor-layout">
        <div className="editor-main">
          <section className="content-card form-section">
            <div className="section-heading">
              <div><span>01</span><h2>문의 내용</h2></div>
              <small>{formatDate(inquiry.createdAt)}</small>
            </div>
            <p className="inquiry-body">{inquiry.content}</p>
            {inquiry.imageUrls.length > 0 && (
              <div className="inquiry-images">
                {inquiry.imageUrls.map((url) => (
                  <a key={url} href={url} target="_blank" rel="noreferrer">
                    <img src={url} alt="첨부 이미지" />
                  </a>
                ))}
              </div>
            )}
          </section>

          <section className="content-card form-section">
            <div className="section-heading">
              <div><span>02</span><h2>답변</h2></div>
              {editable && (
                <button
                  className="button button-secondary"
                  type="button"
                  onClick={() => setPendingAction('draft')}
                  disabled={busy}
                >
                  AI 초안 생성
                </button>
              )}
            </div>

            {draft?.needsHumanReview && (
              <div className="inline-alert neutral">
                AI가 맥락만으로는 확실히 답하기 어렵다고 표시했어요. 사실 확인 후 보내 주세요.
              </div>
            )}
            {draft && draft.usedContext.length > 0 && (
              <div className="context-chips">
                <span>참고</span>
                {draft.usedContext.map((item) => (
                  <span key={item} className="context-chip">{item}</span>
                ))}
              </div>
            )}

            {editable ? (
              <>
                <textarea
                  className="answer-editor"
                  rows={14}
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                  disabled={busy}
                  placeholder="문의자에게 보낼 답변 전체를 작성하세요."
                />
                <div className="answer-actions">
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => setAnswer(inquiry.answerTemplate)}
                    disabled={busy}
                  >
                    양식 초기화
                  </button>
                  <button
                    className="button button-primary"
                    type="button"
                    onClick={() => setPendingAction('answer')}
                    disabled={!written || busy}
                  >
                    답변 등록
                  </button>
                  {written && <span className="unsaved-note">● 아직 등록하지 않았어요.</span>}
                </div>
              </>
            ) : (
              <>
                <pre className="answer-sent">{inquiry.answer}</pre>
                <p className="answered-at">{formatDate(inquiry.answeredAt)}에 답변함</p>
              </>
            )}
          </section>
        </div>

        <aside className="editor-aside">
          <section className="content-card aside-card history-card">
            <p className="eyebrow">변경 이력</p>
            <h2>최근 운영 기록</h2>
            {historyLogs.length === 0 ? (
              <p className="muted-text">아직 이력이 없어요.</p>
            ) : (
              <ol>
                {historyLogs.slice(0, 8).map((log) => (
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
        </aside>
      </div>

      {pendingAction === 'draft' && (
        <ConfirmModal
          open
          title="AI 답변 초안을 만들까요?"
          description="과거 답변과 가이드 문서를 참고해 초안을 생성해요. 실제 LLM을 호출합니다."
          confirmLabel="초안 생성"
          busy={busy}
          onCancel={() => setPendingAction(null)}
          onConfirm={generateDraft}
        />
      )}
      {pendingAction === 'answer' && (
        <ConfirmModal
          open
          title="이 답변을 등록할까요?"
          description="답변을 등록하면 상태가 '답변 완료'로 바뀌고 문의자에게 알림이 전송돼요. 등록 후에는 수정할 수 없어요."
          confirmLabel="답변 등록"
          busy={busy}
          onCancel={() => setPendingAction(null)}
          onConfirm={submitAnswer}
        />
      )}
    </div>
  );
}
