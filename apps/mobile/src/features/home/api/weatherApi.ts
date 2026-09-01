import { apiClient } from '@/src/services/apiClient';

import type { WeatherCondition, WeatherSummary } from '../types/home';
import { CONDITION_LABELS, weatherTip } from '../utils/weatherCopy';

const REGIONS = ['제주', '서귀포', '한림', '성산'] as const;
const WEATHER_API_URL = process.env.EXPO_PUBLIC_WEATHER_API_URL;
type WeatherRegion = (typeof REGIONS)[number];

const REGION_LABELS: Record<WeatherRegion, string> = {
  제주: '제주',
  서귀포: '서귀포',
  한림: '서부(한림)',
  성산: '동부(성산)',
};

type WeatherApiResponse = {
  region: WeatherRegion;
  condition: WeatherCondition;
  temperature: number;
  precipitationProbability: number;
  humidity: number;
  windSpeed: number;
};

export async function fetchJejuWeather(): Promise<WeatherSummary[]> {
  const responses = await Promise.all(
    REGIONS.map((region) =>
      apiClient.get<WeatherApiResponse>('/weather/current', {
        ...(WEATHER_API_URL ? { baseURL: WEATHER_API_URL } : {}),
        params: { region },
      }),
    ),
  );

  return responses.map(({ data }) => ({
    location: REGION_LABELS[data.region],
    temperature: Math.round(data.temperature),
    condition: data.condition,
    conditionLabel: CONDITION_LABELS[data.condition],
    precipitationProbability: data.precipitationProbability,
    humidity: data.humidity,
    windSpeed: data.windSpeed,
    tip: weatherTip(data),
  }));
}
