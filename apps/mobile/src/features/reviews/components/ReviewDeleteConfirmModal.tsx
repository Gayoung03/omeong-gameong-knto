import { ConfirmModal } from '@/src/components/feedback/ConfirmModal';

type Props = {
  visible: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  isDeleting?: boolean;
};

/** 리뷰 삭제 확인. 물리 삭제라 되돌릴 수 없다. */
export function ReviewDeleteConfirmModal({ visible, onCancel, onConfirm, isDeleting }: Props) {
  return (
    <ConfirmModal
      busyLabel="삭제 중..."
      confirmLabel="삭제"
      description={'첨부한 사진도 함께 지워지고\n되돌릴 수 없어요.'}
      isBusy={isDeleting}
      onCancel={onCancel}
      onConfirm={onConfirm}
      title="리뷰를 삭제할까요?"
      tone="destructive"
      visible={visible}
    />
  );
}
