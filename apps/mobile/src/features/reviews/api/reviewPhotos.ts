import { uploadImage } from '@/src/services/uploadImage';

/** 이미 서버에 올라간 사진인지. 수정 화면은 기존 사진과 새 사진을 섞어서 넘긴다. */
function isUploaded(uri: string): boolean {
  return uri.startsWith('http://') || uri.startsWith('https://');
}

/**
 * 리뷰 사진을 서버에 올리고 저장할 URL 목록을 돌려준다.
 *
 * 앨범에서 새로 고른 로컬 URI 만 올리고 **기존 사진은 그대로 통과시킨다.**
 * 수정할 때마다 안 바뀐 사진까지 다시 올리면 같은 파일이 S3에 쌓인다.
 *
 * 반환 순서가 그대로 `sortOrder` 가 되므로 입력 순서를 지킨다.
 */
export async function uploadReviewPhotos(uris: string[]): Promise<string[]> {
  if (uris.length === 0) return [];

  return Promise.all(
    uris.map((uri) => (isUploaded(uri) ? Promise.resolve(uri) : uploadImage(uri, 'review'))),
  );
}
