"""카카오 소셜 로그인 서버 콜백 연동 (docs/api/auth.md 소셜 절).

서버가 인가 코드를 카카오 토큰으로 교환하고(시크릿이 앱 번들에 들어가지 않게),
`access_token_info` 로 **그 토큰이 우리 앱 것인지** 확인한 뒤 프로필을 읽는다.
실 카카오 호출은 이 모듈에만 있다 — 엔드포인트는 `get_kakao_client` 의존성으로
`KakaoOAuthClient` 를 받고, 테스트는 그 의존성을 fake 로 갈아끼운다.

provider 를 확장할 수 있게 프로필 형태(`SocialProfile`)와 예외는 provider 중립이다.
"""

import logging
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _log_rejection(step: str, response: httpx.Response) -> None:
    """카카오가 거부한 이유를 내부 로그에만 남긴다.

    외부 응답은 일반화된 401 하나지만(정보 노출 방지), KOE 코드가 로그에 없으면
    콘솔 설정 문제(client secret 사용함, 동의항목 등)를 진단할 방법이 없다.
    토큰·사용자 정보는 남기지 않는다 — error/error_code 필드만.
    """
    try:
        body = response.json()
        detail = {k: body.get(k) for k in ("error", "error_code", "error_description") if k in body}
    except ValueError:
        detail = {"raw": response.text[:200]}
    logger.warning("카카오 %s 거부: status=%s %s", step, response.status_code, detail)

KAKAO_AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_TOKEN_INFO_URL = "https://kapi.kakao.com/v1/user/access_token_info"
KAKAO_USER_ME_URL = "https://kapi.kakao.com/v2/user/me"
REQUEST_TIMEOUT_SECONDS = 10.0


class SocialAuthError(RuntimeError):
    """제공처 토큰이 무효하거나 우리 앱 것이 아니다 (→ 401)."""


class SocialProviderUnavailable(RuntimeError):
    """제공처 서버에 닿지 못했다 (→ 502)."""


@dataclass(frozen=True)
class SocialProfile:
    """제공처가 확인해 준 사용자 정보. 이메일은 **검증된 경우에만** 채운다."""

    provider: str
    provider_user_id: str
    email: str | None
    nickname: str | None
    profile_image_url: str | None


class KakaoOAuthClient:
    provider = "kakao"

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        """카카오 인가 페이지 URL. 네트워크 호출 없이 문자열만 만든다."""
        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.kakao_rest_api_key,
                "redirect_uri": redirect_uri,
                "state": state,
            }
        )
        return f"{KAKAO_AUTHORIZE_URL}?{query}"

    def fetch_profile(self, code: str, redirect_uri: str) -> SocialProfile:
        """인가 코드를 토큰으로 바꾸고, 앱 소유를 확인한 뒤 프로필을 읽는다."""
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            token = self._exchange_code(client, code, redirect_uri)
            self._verify_app_ownership(client, token)
            return self._read_profile(client, token)

    def _exchange_code(self, client: httpx.Client, code: str, redirect_uri: str) -> str:
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.kakao_rest_api_key,
            "redirect_uri": redirect_uri,
            "code": code,
        }
        if settings.kakao_client_secret:
            data["client_secret"] = settings.kakao_client_secret
        try:
            response = client.post(KAKAO_TOKEN_URL, data=data)
        except httpx.HTTPError as error:
            raise SocialProviderUnavailable("카카오 토큰 교환에 실패했습니다") from error
        if response.status_code >= 500:
            raise SocialProviderUnavailable("카카오 서버가 응답하지 않습니다")
        if response.status_code != 200:
            # 400/401(잘못된·만료된 코드, client secret 미전송 등)은 인증 실패로 통일.
            _log_rejection("토큰 교환", response)
            raise SocialAuthError("카카오 인가 코드가 유효하지 않습니다")
        access_token = response.json().get("access_token")
        if not access_token:
            raise SocialAuthError("카카오 토큰 응답에 access_token 이 없습니다")
        return access_token

    def _verify_app_ownership(self, client: httpx.Client, token: str) -> None:
        info = self._get_json(client, KAKAO_TOKEN_INFO_URL, token)
        # 설정된 경우에만 대조한다. 토큰은 우리 REST 키로 교환해 이미 우리 앱 것이지만,
        # app_id 대조로 토큰 스와핑까지 막는 방어층을 둔다.
        if settings.kakao_app_id and str(info.get("app_id")) != str(settings.kakao_app_id):
            raise SocialAuthError("우리 앱의 토큰이 아닙니다")

    def _read_profile(self, client: httpx.Client, token: str) -> SocialProfile:
        me = self._get_json(client, KAKAO_USER_ME_URL, token)
        account = me.get("kakao_account") or {}
        profile = account.get("profile") or {}
        # 검증된 이메일만 신뢰한다(is_email_valid && is_email_verified).
        email = None
        if account.get("is_email_valid") and account.get("is_email_verified"):
            email = account.get("email")
        return SocialProfile(
            provider="kakao",
            provider_user_id=str(me["id"]),
            email=email,
            nickname=profile.get("nickname"),
            profile_image_url=profile.get("profile_image_url"),
        )

    def _get_json(self, client: httpx.Client, url: str, token: str) -> dict:
        try:
            response = client.get(url, headers={"Authorization": f"Bearer {token}"})
        except httpx.HTTPError as error:
            raise SocialProviderUnavailable("카카오 서버가 응답하지 않습니다") from error
        if response.status_code >= 500:
            raise SocialProviderUnavailable("카카오 서버가 응답하지 않습니다")
        if response.status_code != 200:
            _log_rejection("사용자 정보 조회", response)
            raise SocialAuthError("카카오 사용자 정보를 확인하지 못했습니다")
        return response.json()


def get_kakao_client() -> KakaoOAuthClient:
    """FastAPI 의존성. 테스트는 이 의존성을 override 해 fake 를 넣는다."""
    return KakaoOAuthClient()
