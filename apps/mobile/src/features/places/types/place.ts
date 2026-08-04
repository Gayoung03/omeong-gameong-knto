import type Ionicons from '@expo/vector-icons/Ionicons';
import type { ComponentProps } from 'react';

export type PlaceIconName = ComponentProps<typeof Ionicons>['name'];

export type PlaceRegion =
  | '제주시/제주국제공항'
  | '서귀포시/모슬포'
  | '애월/한림/협재'
  | '중문'
  | '표선/성산'
  | '함덕/김녕/세화';

export type PlaceCategory = {
  id: string;
  label: string;
  icon: PlaceIconName;
};

export type Place = {
  id: string;
  name: string;
  address: string;
  region: PlaceRegion;
  category: string;
  environment?: '실내' | '야외';
  distanceKm: number;
  latitude: number;
  longitude: number;
  petFriendly: boolean;
  imageUrl: string;
  initiallyFavorite?: boolean;
};
