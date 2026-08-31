import type { WeatherCondition } from '../types/home';

export const CONDITION_LABELS: Record<WeatherCondition, string> = {
  sunny: '맑음',
  partly_cloudy: '구름 조금',
  cloudy: '흐림',
  rainy: '비',
  snowy: '눈',
  windy: '강한 바람',
};

type WeatherForCopy = {
  condition: WeatherCondition;
  temperature: number;
  precipitationProbability: number;
  windSpeed: number;
};

export function weatherTip(weather: WeatherForCopy): string {
  if (weather.condition === 'snowy') return '눈길에서는 아이 발이 미끄럽지 않게 천천히 걸어주세요!';
  if (weather.condition === 'rainy' || weather.precipitationProbability >= 60) {
    return '비에 대비해 우산과 아이를 닦을 수건을 챙겨주세요!';
  }
  if (weather.condition === 'windy' || weather.windSpeed >= 8) {
    return '바람이 강해요. 산책은 짧게 하고 아이 체온을 살펴주세요!';
  }
  if (weather.temperature >= 29) return '한낮 산책을 피하고 시원한 물을 충분히 챙겨주세요!';
  if (weather.temperature <= 5) return '기온이 낮아요. 아이가 추워하지 않도록 보온을 챙겨주세요!';
  return '아이와 산책하기 좋은 날씨예요. 즐거운 제주 나들이 되세요!';
}
