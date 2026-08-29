import type { SignupData } from '../types/auth';

import type { SignupPayload, SignupPetPayload, TravelPreferencePayload } from './authApi';

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

/**
 * 펫 페이로드. 화면 검증(validatePet)이 "정보가 있으면 완전한 펫"을 보장하므로,
 * 여기서는 그 결과를 옮기기만 한다. 정보가 전혀 없으면(이름·종류·크기 모두 없음)
 * `undefined` 를 돌려 pet 을 보내지 않는다(선택 단계).
 *
 * species 는 화면 값(dog·cat·other)이 백엔드 코드와 같아 변환이 없다. speciesDetail
 * 은 **other 일 때만** 담는다(백엔드 CHECK 규칙). size 는 고른 경우에만.
 */
function toPet(pet: SignupData['pet']): SignupPetPayload | undefined {
  const name = pet.name.trim();
  if (pet.type === null || name.length === 0) return undefined;

  const payload: SignupPetPayload = { name, species: pet.type };
  if (pet.type === 'other') {
    const detail = pet.typeDetail.trim();
    if (detail) payload.speciesDetail = detail;
  }
  if (pet.size) payload.size = pet.size;
  return payload;
}

export function toSignupPayload(data: SignupData): SignupPayload {
  const pet = toPet(data.pet);
  return {
    email: data.account.email.trim(),
    password: data.account.password,
    nickname: data.account.nickname.trim(),
    ...(pet ? { pet } : {}),
    travelPreference: toTravelPreference(data.travel),
  };
}
