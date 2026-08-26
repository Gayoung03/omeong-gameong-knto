"""여행기록 이미지 생성.

사용자가 올린 사진에 손글씨·장식을 얹은 완성 이미지를 만드는 자리다.

## 지금은 임시 구현이다

**원본 사진 URL 을 그대로 돌려준다.** 어떤 이미지 생성 서비스를 쓸지 정해지지
않았기 때문이다(비용·API 키·저작권 검토가 남아 있다).

임시라서 화면은 원본 사진을 그대로 보여주지만, 그 앞뒤 흐름(업로드 → 저장 →
진행 상태 → 재생성 → 완료 알림)은 전부 진짜로 동작한다.

## 실제 AI 를 붙일 때

**이 파일의 `generate_log_image` 안만 고치면 된다.** 부르는 쪽
(`api/v1/endpoints/travel_logs.py` 의 뒷작업)은 한 줄도 바뀌지 않는다.

그때 할 일:

1. 원본 이미지를 내려받아 생성 서비스에 넘긴다
2. 만들어진 이미지를 S3 에 올린다 (`endpoints/uploads.py` 의 방식을 따른다)
3. 그 공개 URL 을 돌려준다

실패하면 예외를 던지면 된다 — 부르는 쪽이 `failed` 로 기록한다.
"""

from app.db.models.enums import MomentMood, WritingStyle


class ImageGenerationError(RuntimeError):
    """이미지를 만들지 못했다. 부르는 쪽이 generation_status 를 failed 로 바꾼다."""


def generate_log_image(
    original_image_url: str,
    writing_style: WritingStyle,
    mood: MomentMood | None,
    place_name: str,
) -> str:
    """완성 이미지의 공개 URL 을 돌려준다.

    임시 구현이라 인자 대부분을 쓰지 않는다. 그래도 **시그니처는 실제 구현이
    필요로 할 것에 맞춰** 두었다 — 나중에 이 파일만 고치면 되게 하기 위해서다.
    말투와 기분은 어떤 문구를 써 넣을지, 장소명은 그 문구의 재료로 쓰인다.
    """
    del writing_style, mood, place_name  # 실제 생성기가 쓸 값. 임시 구현은 쓰지 않는다.

    if not original_image_url:
        raise ImageGenerationError("원본 이미지가 없습니다")

    return original_image_url
