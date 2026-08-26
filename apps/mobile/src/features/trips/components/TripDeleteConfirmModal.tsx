import { ConfirmModal } from '@/src/components/feedback/ConfirmModal';

type Props = {
  visible: boolean;
  tripTitle: string;
  isDeleting?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

/** 여행 삭제 확인. 여행기록·사진이 남는다는 것을 함께 알린다. */
export function TripDeleteConfirmModal({
  visible,
  tripTitle,
  isDeleting,
  onCancel,
  onConfirm,
}: Props) {
  return (
    <ConfirmModal
      busyLabel="삭제 중..."
      confirmLabel="삭제"
      description={'일정·체크리스트·메모가 모두 지워지고\n되돌릴 수 없어요.'}
      isBusy={isDeleting}
      // 사진까지 지워질까 봐 망설이는 경우가 많은데 실제로는 남는다.
      note="여행 로그와 사진은 지워지지 않아요"
      onCancel={onCancel}
      onConfirm={onConfirm}
      title={tripTitle}
      tone="destructive"
      visible={visible}
    />
  );
}
