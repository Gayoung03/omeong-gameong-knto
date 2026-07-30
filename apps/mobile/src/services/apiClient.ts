import { create } from 'axios';

export const apiClient = create({
  baseURL: process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1',
  timeout: 10_000,
});
