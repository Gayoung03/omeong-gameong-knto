export function validateNickname(nickname: string): string | null {
  const trimmed = nickname.trim();

  if (trimmed.length === 0) {
    return '닉네임을 입력해 주세요';
  }

  if (trimmed.length < 2) {
    return '닉네임은 2자 이상이어야 해요';
  }

  if (trimmed.length > 12) {
    return '닉네임은 12자 이하여야 해요';
  }

  const allowedPattern = /^[가-힣a-zA-Z0-9\s]+$/;
  if (!allowedPattern.test(trimmed)) {
    return '한글, 영문, 숫자, 공백만 사용할 수 있어요';
  }

  return null;
}
