import type { SignupData } from '../types/auth';

import type { SignupPayload, TravelPreferencePayload } from './authApi';

/**
 * 회원가입 화면 상태(`SignupData`)를 auth.md signup 페이로드로 옮긴다.
 *
 * 화면은 한글 라벨을 값으로 들고 있어(signupOptions 가 아직 `{ value: '자연' }`
 * 형태다), 여기서 영문 코드로 바꾼다. 코드값은 users.md 의 취향 태그·enum 규약을 따른다.
 */

const durationToDays: Record<string, number> = {
  당일치기: 1,
  '1박 2일': 2,
  '2박 3일': 3,
  '3박 4일+': 4,
};

const transportToCode: Record<string, string> = {
  자가용: 'own_car',
  항공: 'airplane',
  배: 'ferry',
  버스: 'public_transport',
};

const vibeToTag: Record<string, string> = {
  자연: 'nature',
  실내: 'indoor',
  카페: 'cafe',
  산책: 'walk',
  사진: 'photo',
  조용한: 'quiet',
  활동적: 'active',
};

function toTravelPreference(travel: SignupData['travel']): TravelPreferencePayload {
  // companionCount 는 항상 1 이상이라 늘 담는다. 나머지는 고른 것만 담는다(부분 저장).
  const preference: TravelPreferencePayload = { companionCount: travel.companions };

  if (travel.duration && durationToDays[travel.duration]) {
    preference.preferredDurationDays = durationToDays[travel.duration];
  }
  if (travel.transport && transportToCode[travel.transport]) {
    preference.defaultTransport = transportToCode[travel.transport];
  }
  const departure = travel.departure.trim();
  if (departure) preference.departureLocation = departure;

  const tags = travel.vibes.map((vibe) => vibeToTag[vibe]).filter(Boolean);
  if (tags.length > 0) preference.preferredTags = tags;

  return preference;
}

export function toSignupPayload(data: SignupData): SignupPayload {
  // NOTE(불일치): auth.md signup 의 pet 은 `name` 이 필수인데, SignupScreen 은
  //   반려동물 **이름을 입력받지 않는다**(type·size·기타 종만). 이름 없이는 유효한
  //   pet 페이로드를 만들 수 없어(422) **pet 을 보내지 않는다.** 화면에 이름 필드를
  //   추가하거나(프론트) 별도 명세 논의가 필요하다 — worklog·보고 참고. 여기서
  //   임의의 이름을 지어내지 않는다(계약을 임의 확장하지 않음).
  return {
    email: data.account.email.trim(),
    password: data.account.password,
    nickname: data.account.nickname.trim(),
    travelPreference: toTravelPreference(data.travel),
  };
}
