import type { PetSize, PetType } from '../types/auth';

export const petTypeOptions: { value: PetType; label: string; icon: string }[] = [
  { value: 'dog', label: '강아지', icon: '🐶' },
  { value: 'cat', label: '고양이', icon: '🐱' },
  { value: 'other', label: '기타', icon: '•••' },
];

export const petSizeOptions: { value: PetSize; label: string }[] = [
  { value: 'small', label: '소형' },
  { value: 'medium', label: '중형' },
  { value: 'large', label: '대형' },
];

export const durationOptions = ['당일치기', '1박 2일', '2박 3일', '3박 4일+'];

export const transportOptions = [
  { value: '자가용', icon: 'car-outline' as const },
  { value: '항공', icon: 'airplane-outline' as const },
  { value: '배', icon: 'boat-outline' as const },
  { value: '버스', icon: 'bus-outline' as const },
];

export const vibeOptions = [
  { value: '자연', icon: 'leaf-outline' as const },
  { value: '실내', icon: 'home-outline' as const },
  { value: '카페', icon: 'cafe-outline' as const },
  { value: '산책', icon: 'paw-outline' as const },
  { value: '사진', icon: 'camera-outline' as const },
  { value: '조용한', icon: 'volume-low-outline' as const },
  { value: '활동적', icon: 'walk-outline' as const },
];

