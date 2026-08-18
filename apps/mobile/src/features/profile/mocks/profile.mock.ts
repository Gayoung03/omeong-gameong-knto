import { Image } from 'react-native';

import type { Pet } from '@/src/types/pet';
import type { ActivitySummary, RecentVisit } from '@/src/types/profile';
import type { User } from '@/src/types/user';

export const mockUser: User = {
  userId: 'user-1',
  nickname: '혼디온님',
  email: 'hondion_jeju@gmail.com',
  profileImage: Image.resolveAssetSource(require('@/assets/images/profile/default-user.jpg')).uri,
};

/**
 * 앱 전체가 공유하는 반려동물 목업의 유일한 원본.
 *
 * 프로필 사진은 번들 이미지를 `Image.resolveAssetSource` 로 URI 문자열로 바꿔 쓴다.
 * `Pet.profileImage` 는 API 가 붙으면 서버 URL 이 들어올 자리라 타입을 string 으로 유지한다.
 * 실제 데이터 접근은 petService를 통해서만 하고, 화면이 이 배열을 직접 import하지 않는다.
 */
export const mockPets: Pet[] = [
  {
    petId: 'pet-1',
    name: '몽이',
    species: '강아지',
    breed: '몰티즈',
    age: 3,
    weight: 4.2,
    profileImage: Image.resolveAssetSource(require('@/assets/images/pets/mongi.jpg')).uri,
    status: 'active',
  },
  {
    petId: 'pet-2',
    name: '코코',
    species: '고양이',
    breed: '코리안숏헤어',
    age: 2,
    weight: 3.5,
    profileImage: Image.resolveAssetSource(require('@/assets/images/pets/coco.jpg')).uri,
    status: 'active',
  },
];

export const mockActivitySummary: ActivitySummary = {
  savedPlacesCount: 23,
  savedCoursesCount: 8,
  travelLogsCount: 12,
};

export const mockRecentVisits: RecentVisit[] = [
  {
    placeId: 'place-1',
    placeName: '함덕해수욕장',
    date: '2024-05-18',
    image: 'https://placehold.co/400x200',
  },
  {
    placeId: 'place-2',
    placeName: '제주 곶자왈 도립공원',
    date: '2024-05-02',
    image: 'https://placehold.co/400x200',
  },
];
