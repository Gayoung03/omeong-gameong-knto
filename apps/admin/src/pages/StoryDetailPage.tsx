import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { ConfirmModal } from '../components/ConfirmModal';
import { StatusBadge } from '../components/StatusBadge';
import { apiRequest } from '../lib/api';
import type {
  EditorialSection,
  StoryDetail,
  StoryKind,
  StoryUpdatePayload,
} from '../types';

type StoryAction = 'publish' | 'archive' | 'draft';

interface StoryForm {
  kind: StoryKind;
  category: string;
  cardTitle: string;
  title: string;
  summary: string;
  heroImageUrl: string;
  sections: EditorialSection[];
  tips: string[];
  tags: string[];
  displayOrder: number;
  publishedAt: string;
  expiresAt: string;
}

const KIND_LABEL: Record<StoryKind, string> = {
  event: '행사',
  weather: '날씨',
  story: '이야기',
  guide: '가이드',
};

const ACTION_COPY: Record<
  StoryAction,
  { title: string; description: string; label: string; tone: 'primary' | 'danger' }
> = {
  publish: {
    title: '이 이야기를 게시할까요?',
    description: '승인하면 게시 시각부터 사용자 앱에 노출됩니다.',
    label: '승인하고 게시',
    tone: 'primary',
  },
  archive: {
    title: '게시를 중단하고 보관할까요?',
    description: '보관 즉시 사용자 앱에서 이 이야기가 사라집니다.',
    label: '게시 중단',
    tone: 'danger',
  },
  draft: {
    title: '다시 초안으로 돌릴까요?',
    description: '이전 게시 시각은 초기화되고, 내용을 다시 수정할 수 있습니다.',
    label: '초안으로 복귀',
    tone: 'primary',
  },
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

function storyToForm(story: StoryDetail): StoryForm {
  return {
    kind: story.kind,
    category: story.category,
    cardTitle: story.cardTitle,
    title: story.title,
    summary: story.summary,
    heroImageUrl: story.heroImageUrl,
    sections: story.sections,
    tips: story.tips,
    tags: story.tags,
    displayOrder: story.displayOrder,
    publishedAt: toLocalDateTime(story.publishedAt),
    expiresAt: toLocalDateTime(story.expiresAt),
  };
}

function cleanList(values: string[]): string[] {
  return values.map((value) => value.trim()).filter(Boolean);
}

function validationMessages(form: StoryForm): string[] {
  const messages: string[] = [];
  if (!form.cardTitle.trim() || !form.title.trim() || !form.summary.trim()) {
    messages.push('필수 제목과 요약을 모두 입력해 주세요.');
  }
  if (!form.heroImageUrl.trim()) messages.push('대표 이미지 URL을 확인해 주세요.');
  if (form.sections.length === 0) messages.push('본문 섹션은 하나 이상 필요해요.');
  if (form.sections.some((section) => !section.heading.trim() || cleanList(section.paragraphs).length === 0)) {
    messages.push('본문 소제목과 문단에 빈 곳이 있어요.');
  }
  if (/(?:하개|해멍|이개)[.!?]?(?:\s|$)/.test(form.summary)) {
    messages.push('요약은 강아지 말투보다 자연스러운 존댓말을 권장해요.');
  }
  if (form.expiresAt && form.publishedAt && new Date(form.expiresAt) <= new Date(form.publishedAt)) {
    messages.push('만료 시각은 게시 시각보다 늦어야 해요.');
  }
  if (form.expiresAt && !form.publishedAt && new Date(form.expiresAt) <= new Date()) {
    messages.push('만료 시각은 현재 시각보다 늦어야 해요.');
  }
  return messages;
}

function hasBlockingValidation(form: StoryForm): boolean {
  if (!form.cardTitle.trim() || !form.title.trim() || !form.summary.trim()) return true;
  if (!form.heroImageUrl.trim() || form.sections.length === 0) return true;
  if (
    form.sections.some(
      (section) => !section.heading.trim() || cleanList(section.paragraphs).length === 0,
    )
  ) return true;
  if (form.expiresAt) {
    const effectivePublishedAt = form.publishedAt ? new Date(form.publishedAt) : new Date();
    if (new Date(form.expiresAt) <= effectivePublishedAt) return true;
  }
  return false;
}

export function StoryDetailPage() {
  const { storyId } = useParams();
  const navigate = useNavigate();
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [form, setForm] = useState<StoryForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pendingAction, setPendingAction] = useState<StoryAction | null>(null);

  useEffect(() => {
    if (!storyId) return;
    const controller = new AbortController();
    apiRequest<StoryDetail>(`/admin/editorial-stories/${storyId}`, {
      signal: controller.signal,
    })
      .then((result) => {
        setStory(result);
        setForm(storyToForm(result));
      })
      .catch((caught) => {
        if ((caught as Error).name !== 'AbortError') {
          setError(caught instanceof Error ? caught.message : '이야기를 불러오지 못했습니다.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [storyId]);

  const editable = story?.status === 'draft';
  const dirty = useMemo(
    () => Boolean(story && form && JSON.stringify(storyToForm(story)) !== JSON.stringify(form)),
    [form, story],
  );
  const warnings = useMemo(() => (form ? validationMessages(form) : []), [form]);
  const hasBlockingIssue = useMemo(() => (form ? hasBlockingValidation(form) : true), [form]);

  const updateField = <Key extends keyof StoryForm>(key: Key, value: StoryForm[Key]) => {
    setForm((current) => (current ? { ...current, [key]: value } : current));
    setNotice('');
  };

  const updateSection = (index: number, values: Partial<EditorialSection>) => {
    if (!form) return;
    updateField(
      'sections',
      form.sections.map((section, sectionIndex) =>
        sectionIndex === index ? { ...section, ...values } : section,
      ),
    );
  };

  const updateParagraph = (sectionIndex: number, paragraphIndex: number, value: string) => {
    if (!form) return;
    const section = form.sections[sectionIndex];
    if (!section) return;
    updateSection(sectionIndex, {
      paragraphs: section.paragraphs.map((paragraph, index) =>
        index === paragraphIndex ? value : paragraph,
      ),
    });
  };

  const handleSave = async () => {
    if (!story || !form || hasBlockingIssue) return;
    setSaving(true);
    setError('');
    setNotice('');
    const payload: StoryUpdatePayload = {
      ...form,
      category: form.category.trim(),
      cardTitle: form.cardTitle.trim(),
      title: form.title.trim(),
      summary: form.summary.trim(),
      heroImageUrl: form.heroImageUrl.trim(),
      sections: form.sections.map((section) => ({
        ...section,
        heading: section.heading.trim(),
        paragraphs: cleanList(section.paragraphs),
        imageUrl: section.imageUrl?.trim() || null,
        imageCaption: section.imageCaption?.trim() || null,
      })),
      tips: cleanList(form.tips),
      tags: cleanList(form.tags),
      publishedAt: toApiDateTime(form.publishedAt),
      expiresAt: toApiDateTime(form.expiresAt),
    };
    try {
      const updated = await apiRequest<StoryDetail>(`/admin/editorial-stories/${story.id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
      setStory(updated);
      setForm(storyToForm(updated));
      setNotice('수정한 내용을 저장했어요.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '저장하지 못했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const performAction = async () => {
    if (!pendingAction || !story || !form) return;
    setSaving(true);
    setError('');
    const action = pendingAction;
    try {
      const updated = await apiRequest<StoryDetail>(
        `/admin/editorial-stories/${story.id}/${action}`,
        action === 'publish'
          ? {
              method: 'POST',
              body: JSON.stringify({ publishedAt: toApiDateTime(form.publishedAt) }),
            }
          : { method: 'POST' },
      );
      setStory(updated);
      setForm(storyToForm(updated));
      setPendingAction(null);
      setNotice(
        action === 'publish'
          ? '사용자 앱에 게시했어요.'
          : action === 'archive'
            ? '게시를 중단하고 보관했어요.'
            : '다시 수정할 수 있는 초안으로 돌렸어요.',
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '상태를 변경하지 못했습니다.');
      setPendingAction(null);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="page-loading"><span className="spinner" />이야기를 불러오는 중이에요.</div>;
  if (!story || !form) {
    return (
      <div className="not-found">
        <h1>이야기를 열 수 없어요.</h1>
        <p>{error || '삭제되었거나 접근할 수 없는 이야기입니다.'}</p>
        <button className="button button-secondary" onClick={() => navigate('/stories')}>목록으로</button>
      </div>
    );
  }

  const addSection = () => {
    updateField('sections', [
      ...form.sections,
      {
        id: `section-${crypto.randomUUID()}`,
        heading: '',
        paragraphs: [''],
        imageUrl: null,
        imageCaption: null,
      },
    ]);
  };

  return (
    <div className="detail-page">
      <div className="detail-topline">
        <div>
          <Link className="back-link" to="/stories">← 여행 이야기 목록</Link>
          <div className="detail-title-row">
            <h1>{story.cardTitle}</h1>
            <StatusBadge status={story.status} />
          </div>
          <p className="story-slug">{story.slug}</p>
        </div>
        <div className="detail-actions">
          {editable && (
            <>
              <button className="button button-secondary" type="button" onClick={handleSave} disabled={!dirty || saving}>
                {saving ? '저장 중…' : '변경 저장'}
              </button>
              <button
                className="button button-primary"
                type="button"
                onClick={() => setPendingAction('publish')}
                disabled={dirty || hasBlockingIssue || saving}
                title={dirty ? '먼저 변경 내용을 저장해 주세요.' : undefined}
              >
                승인·게시
              </button>
            </>
          )}
          {story.status === 'published' && (
            <button className="button button-danger-outline" type="button" onClick={() => setPendingAction('archive')}>
              게시 중단
            </button>
          )}
          {story.status === 'archived' && (
            <button className="button button-primary" type="button" onClick={() => setPendingAction('draft')}>
              초안으로 복귀
            </button>
          )}
        </div>
      </div>

      {notice && <div className="inline-alert success">{notice}</div>}
      {error && <div className="inline-alert error">{error}</div>}
      {!editable && (
        <div className="inline-alert neutral">
          {story.status === 'published'
            ? '게시 중인 내용은 읽기 전용입니다. 수정하려면 먼저 보관 후 초안으로 복귀해 주세요.'
            : '보관된 내용은 읽기 전용입니다. 초안으로 복귀하면 수정할 수 있어요.'}
        </div>
      )}

      <div className="editor-layout">
        <div className="editor-main">
          <section className="content-card form-section">
            <div className="section-heading">
              <div><span>01</span><h2>기본 정보</h2></div>
              <small>홈 카드와 상세 상단에 노출되는 내용</small>
            </div>
            <div className="form-grid two-columns">
              <label>콘텐츠 종류
                <select value={form.kind} onChange={(event) => updateField('kind', event.target.value as StoryKind)} disabled={!editable}>
                  {Object.entries(KIND_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <label>카테고리
                <input value={form.category} onChange={(event) => updateField('category', event.target.value)} disabled={!editable} maxLength={50} />
              </label>
              <label className="full-width">카드 제목 <span className="field-count">{form.cardTitle.length}/160</span>
                <input value={form.cardTitle} onChange={(event) => updateField('cardTitle', event.target.value)} disabled={!editable} maxLength={160} />
              </label>
              <label className="full-width">본문 제목 <span className="field-count">{form.title.length}/200</span>
                <input value={form.title} onChange={(event) => updateField('title', event.target.value)} disabled={!editable} maxLength={200} />
              </label>
              <label className="full-width">요약
                <textarea rows={4} value={form.summary} onChange={(event) => updateField('summary', event.target.value)} disabled={!editable} />
              </label>
            </div>
          </section>

          <section className="content-card form-section">
            <div className="section-heading">
              <div><span>02</span><h2>이미지</h2></div>
              <small>대표 이미지는 카드와 본문 상단에 함께 사용돼요.</small>
            </div>
            <label>대표 이미지 URL
              <input type="url" value={form.heroImageUrl} onChange={(event) => updateField('heroImageUrl', event.target.value)} disabled={!editable} />
            </label>
            {form.heroImageUrl && <img className="hero-preview" src={form.heroImageUrl} alt="대표 이미지 미리보기" />}
          </section>

          <section className="content-card form-section">
            <div className="section-heading">
              <div><span>03</span><h2>본문 구성</h2></div>
              {editable && <button className="text-button" type="button" onClick={addSection}>+ 섹션 추가</button>}
            </div>
            <div className="sections-editor">
              {form.sections.map((section, sectionIndex) => (
                <div className="section-editor" key={section.id}>
                  <div className="section-editor-head">
                    <strong>섹션 {sectionIndex + 1}</strong>
                    {editable && form.sections.length > 1 && (
                      <button type="button" onClick={() => updateField('sections', form.sections.filter((_, index) => index !== sectionIndex))}>섹션 삭제</button>
                    )}
                  </div>
                  <label>본문 소제목
                    <input value={section.heading} onChange={(event) => updateSection(sectionIndex, { heading: event.target.value })} disabled={!editable} />
                  </label>
                  <div className="paragraph-list">
                    {section.paragraphs.map((paragraph, paragraphIndex) => (
                      <label key={`${section.id}-paragraph-${paragraphIndex}`}>
                        문단 {paragraphIndex + 1}
                        <textarea rows={5} value={paragraph} onChange={(event) => updateParagraph(sectionIndex, paragraphIndex, event.target.value)} disabled={!editable} />
                        {editable && section.paragraphs.length > 1 && (
                          <button className="remove-inline" type="button" onClick={() => updateSection(sectionIndex, { paragraphs: section.paragraphs.filter((_, index) => index !== paragraphIndex) })}>문단 삭제</button>
                        )}
                      </label>
                    ))}
                    {editable && <button className="text-button" type="button" onClick={() => updateSection(sectionIndex, { paragraphs: [...section.paragraphs, ''] })}>+ 문단 추가</button>}
                  </div>
                  <div className="form-grid two-columns">
                    <label>본문 이미지 URL
                      <input type="url" value={section.imageUrl ?? ''} onChange={(event) => updateSection(sectionIndex, { imageUrl: event.target.value || null })} disabled={!editable} />
                    </label>
                    <label>이미지 설명
                      <input value={section.imageCaption ?? ''} onChange={(event) => updateSection(sectionIndex, { imageCaption: event.target.value || null })} disabled={!editable} maxLength={300} />
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="content-card form-section">
            <div className="section-heading"><div><span>04</span><h2>팁과 태그</h2></div></div>
            <div className="repeat-list">
              <span className="field-label">혼디의 여행 체크</span>
              {form.tips.map((tip, index) => (
                <div className="repeat-row" key={`tip-${index}`}>
                  <input value={tip} onChange={(event) => updateField('tips', form.tips.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} disabled={!editable} />
                  {editable && <button type="button" onClick={() => updateField('tips', form.tips.filter((_, itemIndex) => itemIndex !== index))} aria-label={`${index + 1}번 팁 삭제`}>×</button>}
                </div>
              ))}
              {editable && <button className="text-button align-start" type="button" onClick={() => updateField('tips', [...form.tips, ''])}>+ 팁 추가</button>}
            </div>
            <label>태그 <small>쉼표로 구분해 입력하세요.</small>
              <input value={form.tags.join(', ')} onChange={(event) => updateField('tags', event.target.value.split(',').map((tag) => tag.trimStart()))} disabled={!editable} />
            </label>
          </section>

          <section className="content-card form-section">
            <div className="section-heading"><div><span>05</span><h2>노출 설정</h2></div></div>
            <div className="form-grid three-columns">
              <label>노출 순서
                <input type="number" value={form.displayOrder} onChange={(event) => updateField('displayOrder', Number(event.target.value))} disabled={!editable} min={-32768} max={32767} />
              </label>
              <label>게시 시각 <small>비우면 승인 시각</small>
                <input type="datetime-local" value={form.publishedAt} onChange={(event) => updateField('publishedAt', event.target.value)} disabled={!editable} />
              </label>
              <label>만료 시각 <small>비우면 기한 없음</small>
                <input type="datetime-local" value={form.expiresAt} onChange={(event) => updateField('expiresAt', event.target.value)} disabled={!editable} />
              </label>
            </div>
          </section>

          <section className="content-card preview-section">
            <div className="section-heading"><div><span>◎</span><h2>사용자 노출 미리보기</h2></div></div>
            <article className="story-preview">
              {form.heroImageUrl && <img src={form.heroImageUrl} alt="" />}
              <div className="story-preview-body">
                <div className="preview-meta"><span>{KIND_LABEL[form.kind]}</span><span>{form.category}</span></div>
                <h2>{form.title || '본문 제목'}</h2>
                <p>{form.summary || '이야기 요약이 표시됩니다.'}</p>
                {form.sections.map((section) => (
                  <section key={`preview-${section.id}`}>
                    <h3>{section.heading || '소제목'}</h3>
                    {section.paragraphs.map((paragraph, index) => <p key={`${section.id}-${index}`}>{paragraph}</p>)}
                    {section.imageUrl && <figure><img src={section.imageUrl} alt={section.imageCaption ?? ''} /><figcaption>{section.imageCaption}</figcaption></figure>}
                  </section>
                ))}
              </div>
            </article>
          </section>
        </div>

        <aside className="editor-aside">
          <section className="content-card aside-card review-guide">
            <p className="eyebrow">검수 가이드</p>
            <h2>말투를 이렇게 확인해요</h2>
            <ul>
              <li><strong>제목·소제목</strong><span>의미를 유지한 자연스러운 강아지 말투는 가능해요.</span></li>
              <li><strong>요약·본문</strong><span>‘둘러보아요’처럼 편안한 존댓말을 사용해요.</span></li>
              <li><strong>혼디의 여행 체크</strong><span>짧고 재치 있는 반말 강아지 말투가 잘 어울려요.</span></li>
            </ul>
            <p className="guide-note">모든 문장에 억지로 ‘~개’를 붙이지 않아요.</p>
          </section>

          <section className="content-card aside-card validation-card">
            <div className="aside-title-row"><h2>현재 확인 사항</h2><span>{warnings.length}</span></div>
            {warnings.length === 0 ? (
              <p className="validation-ok">✓ 기본 검수 항목을 모두 통과했어요.</p>
            ) : (
              <ul className="warning-list">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
            )}
            {dirty && <p className="unsaved-note">● 저장하지 않은 변경이 있어요.</p>}
          </section>

          <section className="content-card aside-card source-card">
            <p className="eyebrow">출처 확인</p>
            <h2>비짓제주 원문</h2>
            {story.sources.map((source) => (
              <div className="source-item" key={source.id}>
                {source.sourceImageUrl && <img src={source.sourceImageUrl} alt="수집된 원문" />}
                <strong>{source.sourceTitle}</strong>
                <dl>
                  <div><dt>출처</dt><dd>{source.sourceName}</dd></div>
                  <div><dt>원문 게시</dt><dd>{formatDate(source.sourcePublishedAt)}</dd></div>
                  <div><dt>수집</dt><dd>{formatDate(source.collectedAt)}</dd></div>
                </dl>
                <a href={source.sourceUrl} target="_blank" rel="noreferrer">원문 새 창에서 보기 ↗</a>
              </div>
            ))}
          </section>

          <section className="content-card aside-card history-card">
            <p className="eyebrow">변경 이력</p>
            <h2>최근 운영 기록</h2>
            {story.auditLogs.length === 0 ? <p className="muted-text">아직 변경 이력이 없어요.</p> : (
              <ol>{story.auditLogs.slice(0, 8).map((log) => (
                <li key={log.id}>
                  <span className="history-dot" />
                  <div><strong>{log.action === 'updated' ? '내용 수정' : log.action === 'published' ? '게시 승인' : log.action === 'archived' ? '게시 중단' : '초안 복귀'}</strong><small>{formatDate(log.createdAt)}</small></div>
                </li>
              ))}</ol>
            )}
          </section>
        </aside>
      </div>

      {pendingAction && (
        <ConfirmModal
          open
          title={ACTION_COPY[pendingAction].title}
          description={ACTION_COPY[pendingAction].description}
          confirmLabel={ACTION_COPY[pendingAction].label}
          tone={ACTION_COPY[pendingAction].tone}
          busy={saving}
          onCancel={() => setPendingAction(null)}
          onConfirm={performAction}
        />
      )}
    </div>
  );
}
