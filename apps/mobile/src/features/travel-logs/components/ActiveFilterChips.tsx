import { Chip, ChipRow } from '@/src/components/ui/Chip';

type ActiveFilterChipsProps = {
  dateChipLabel: string | null;
  petChipLabel: string | null;
  onRemoveDateFilter: () => void;
  onRemovePetFilter: () => void;
};

/**
 * 활성화된 날짜·반려동물 필터만 칩으로 보여준다.
 * 장소명은 검색창에 그대로 노출되므로 칩을 만들지 않는다.
 * 활성 필터가 없으면 아무것도 렌더하지 않아 빈 공간이 생기지 않는다.
 */
export function ActiveFilterChips({
  dateChipLabel,
  petChipLabel,
  onRemoveDateFilter,
  onRemovePetFilter,
}: ActiveFilterChipsProps) {
  if (!dateChipLabel && !petChipLabel) {
    return null;
  }

  return (
    <ChipRow>
      {dateChipLabel ? (
        <Chip
          label={dateChipLabel}
          onRemove={onRemoveDateFilter}
          removeAccessibilityLabel="날짜 필터 해제"
          tone="orange"
        />
      ) : null}
      {petChipLabel ? (
        <Chip
          label={petChipLabel}
          onRemove={onRemovePetFilter}
          removeAccessibilityLabel="반려동물 필터 해제"
          tone="mint"
        />
      ) : null}
    </ChipRow>
  );
}
