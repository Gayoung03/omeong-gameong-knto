import { ConfirmModal } from '@/src/components/feedback/ConfirmModal';

type Props = {
  visible: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

/** 로그아웃 확인. 실제 그리기는 공용 `ConfirmModal` 이 한다. */
export function LogoutConfirmModal({ visible, onCancel, onConfirm }: Props) {
  return (
    <ConfirmModal
      confirmLabel="로그아웃"
      description={'다시 로그인하면 언제든\n기존 여행 기록을 볼 수 있어요.'}
      onCancel={onCancel}
      onConfirm={onConfirm}
      title="로그아웃 할까요?"
      tone="destructive"
      visible={visible}
    />
  );
}
