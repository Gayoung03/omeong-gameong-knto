import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { getApiErrorMessage } from '@/src/services/apiError';

import { updateTrip } from '../api/tripsApi';
import type { RouteUpdateRequest } from '../types/routeApi';
import type { Trip } from '../types/trip';
import { tripQueryKeys } from './useTrips';

/**
 * 편집 폼이 다루는 값.
 *
 * **서버 `PATCH /routes` 가 받는 것만 담는다.** 예전에는 기간·이동수단·반려동물·
 * 숙소·여행스타일까지 8개를 편집했는데, 그중 저장되는 것은 이 셋뿐이었다.
 * 고칠 수 있어 보이는데 새로고침하면 되돌아가는 상태였다.
 *
 * 나머지는 성격이 둘로 갈린다 —
 * ① 서버가 받게 되면 돌아올 것: 이동수단(`transport`), 여행스타일(`pace`), 반려동물
 * ② 여기서 고칠 것이 아닌 것: 기간(날짜 행을 만들고 지워야 한다),
 *    숙소(저장된 값이 아니라 일정의 숙소 항목에서 뽑아낸 문구다)
 *
 * `components/DateRangeField.tsx` 와 `components/PetEditRow.tsx` 는 ①이 돌아올 때
 * 다시 쓰려고 **지우지 않고 남겨뒀다.** 지금은 참조가 없다.
 */
export type TripInfoDraft = {
  title: string;
  styleKeywords: string[];
  memo: string;
};

function toDraft(trip: Trip): TripInfoDraft {
  return {
    memo: trip.memo,
    styleKeywords: [...trip.styleKeywords],
    title: trip.title,
  };
}

/**
 * 여행 정보 편집.
 *
 * 화면이 보여주는 여행은 이 훅이 아니라 `useTrip` 이 들고 있다.
 * 저장에 성공하면 캐시를 버려 서버 값으로 다시 그린다 — 예전처럼 훅이 사본을
 * 들고 있으면 서버가 다듬은 값(공백 정리 등)과 화면이 어긋난다.
 */
export function useTripInfoForm(trip: Trip) {
  const queryClient = useQueryClient();

  const [draft, setDraft] = useState<TripInfoDraft>(() => toDraft(trip));
  const [isEditing, setIsEditing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();

  const saveMutation = useMutation({
    mutationFn: (payload: RouteUpdateRequest) => updateTrip(trip.id, payload),
    onError: (error) => setErrorMessage(getApiErrorMessage(error).description),
    onSuccess: () => {
      setErrorMessage(undefined);
      queryClient.invalidateQueries({ queryKey: tripQueryKeys.detail(trip.id) });
      queryClient.invalidateQueries({ queryKey: tripQueryKeys.list() });
    },
  });

  const canSubmit = useMemo(
    () => draft.title.trim().length > 0 && !saveMutation.isPending,
    [draft.title, saveMutation.isPending],
  );

  const startEditing = useCallback(() => {
    setDraft(toDraft(trip));
    setErrorMessage(undefined);
    setIsEditing(true);
  }, [trip]);

  const cancelEditing = useCallback(() => {
    setErrorMessage(undefined);
    setIsEditing(false);
  }, []);

  const updateField = useCallback(
    <Key extends keyof TripInfoDraft>(key: Key, value: TripInfoDraft[Key]) => {
      setDraft((previous) => ({ ...previous, [key]: value }));
    },
    [],
  );

  const addKeyword = useCallback((keyword: string) => {
    const trimmed = keyword.trim();

    if (trimmed.length === 0) {
      return;
    }

    setDraft((previous) =>
      previous.styleKeywords.includes(trimmed)
        ? previous
        : { ...previous, styleKeywords: [...previous.styleKeywords, trimmed] },
    );
  }, []);

  const removeKeyword = useCallback((keyword: string) => {
    setDraft((previous) => ({
      ...previous,
      styleKeywords: previous.styleKeywords.filter((item) => item !== keyword),
    }));
  }, []);

  const submit = useCallback(() => {
    if (!canSubmit) {
      return;
    }

    saveMutation.mutate(
      {
        // 빈 메모는 null 로 보낸다. 서버 컬럼이 nullable 이라 ''와 null 이 섞이면
        // "메모 없음" 판정이 두 갈래가 된다.
        memo: draft.memo.trim() || null,
        styleKeywords: draft.styleKeywords,
        title: draft.title.trim(),
      },
      { onSuccess: () => setIsEditing(false) },
    );
  }, [canSubmit, draft, saveMutation]);

  /** 메모 카드에서 메모만 고칠 때. 편집 모드를 거치지 않는다. */
  const saveMemoOnly = useCallback(
    (memo: string) => {
      const trimmed = memo.trim();
      setDraft((previous) => ({ ...previous, memo: trimmed }));
      saveMutation.mutate({ memo: trimmed || null });
    },
    [saveMutation],
  );

  return {
    draft,
    isEditing,
    canSubmit,
    isSaving: saveMutation.isPending,
    errorMessage,
    startEditing,
    cancelEditing,
    updateField,
    addKeyword,
    removeKeyword,
    submit,
    saveMemoOnly,
  };
}
