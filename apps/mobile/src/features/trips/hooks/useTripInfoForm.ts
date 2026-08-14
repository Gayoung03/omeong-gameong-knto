import { useCallback, useMemo, useState } from 'react';

import type { Trip, TripPet, TripTransport } from '../types/trip';
import { calculateTripLength } from '../utils/tripFormat';

export type TripInfoDraft = {
  title: string;
  startDate: string;
  endDate: string;
  transport: TripTransport;
  pets: TripPet[];
  accommodationSummary: string;
  travelStyle: string;
  styleKeywords: string[];
  memo: string;
};

function toDraft(trip: Trip): TripInfoDraft {
  return {
    title: trip.title,
    startDate: trip.startDate,
    endDate: trip.endDate,
    transport: trip.transport,
    pets: trip.pets.map((pet) => ({ ...pet })),
    accommodationSummary: trip.accommodationSummary,
    travelStyle: trip.travelStyle,
    styleKeywords: [...trip.styleKeywords],
    memo: trip.memo,
  };
}

/**
 * 여행 정보 편집 상태를 화면 단위로 관리한다.
 * TODO: 백엔드 준비 후 TanStack Query mutation 으로 교체
 */
export function useTripInfoForm(initialTrip: Trip) {
  const [trip, setTrip] = useState<Trip>(initialTrip);
  const [draft, setDraft] = useState<TripInfoDraft>(() => toDraft(initialTrip));
  const [isEditing, setIsEditing] = useState(false);

  const canSubmit = useMemo(() => draft.title.trim().length > 0, [draft.title]);

  const startEditing = useCallback(() => {
    setDraft(toDraft(trip));
    setIsEditing(true);
  }, [trip]);

  const cancelEditing = useCallback(() => {
    setIsEditing(false);
  }, []);

  const updateField = useCallback(
    <Key extends keyof TripInfoDraft>(key: Key, value: TripInfoDraft[Key]) => {
      setDraft((previous) => ({ ...previous, [key]: value }));
    },
    [],
  );

  const updateDateRange = useCallback((startDate: string, endDate: string) => {
    setDraft((previous) => ({
      ...previous,
      startDate,
      endDate: endDate < startDate ? startDate : endDate,
    }));
  }, []);

  const updatePet = useCallback((petId: string, patch: Partial<Omit<TripPet, 'id'>>) => {
    setDraft((previous) => ({
      ...previous,
      pets: previous.pets.map((pet) => (pet.id === petId ? { ...pet, ...patch } : pet)),
    }));
  }, []);

  const addPet = useCallback(() => {
    setDraft((previous) => ({
      ...previous,
      pets: [...previous.pets, { id: `pet-${Date.now()}`, name: '', sizeType: 'small', count: 1 }],
    }));
  }, []);

  const removePet = useCallback((petId: string) => {
    setDraft((previous) => ({
      ...previous,
      pets: previous.pets.filter((pet) => pet.id !== petId),
    }));
  }, []);

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

    const { nights, days } = calculateTripLength(draft.startDate, draft.endDate);

    setTrip((previous) => ({
      ...previous,
      ...draft,
      title: draft.title.trim(),
      accommodationSummary: draft.accommodationSummary.trim(),
      travelStyle: draft.travelStyle.trim(),
      memo: draft.memo.trim(),
      pets: draft.pets
        .map((pet) => ({ ...pet, name: pet.name.trim() }))
        .filter((pet) => pet.name.length > 0),
      nights,
      days,
    }));
    setIsEditing(false);
  }, [canSubmit, draft]);

  const saveMemoOnly = useCallback((memo: string) => {
    const trimmed = memo.trim();
    setTrip((previous) => ({ ...previous, memo: trimmed }));
    setDraft((previous) => ({ ...previous, memo: trimmed }));
  }, []);

  return {
    trip,
    draft,
    isEditing,
    canSubmit,
    startEditing,
    cancelEditing,
    updateField,
    updateDateRange,
    updatePet,
    addPet,
    removePet,
    addKeyword,
    removeKeyword,
    submit,
    saveMemoOnly,
  };
}
