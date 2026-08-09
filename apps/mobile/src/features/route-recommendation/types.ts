export type RoutePlace = {
  id: string;
  name: string;
  subtitle: string;
  category: string;
  time: string;
  travelMinutes?: number;
  petStatus: '동반 가능' | '확인 필요';
  emoji: string;
  thumbnailColor: string;
};

export type RecommendedDay = {
  day: number;
  date: string;
  weather: string;
  temperature: string;
  places: RoutePlace[];
};
