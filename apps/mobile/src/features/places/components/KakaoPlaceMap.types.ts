export type KakaoMapPlace = {
  id: string;
  name: string;
  address: string;
  category: string;
  latitude: number;
  longitude: number;
};

export type KakaoPlaceMapProps = {
  appKey: string;
  places: KakaoMapPlace[];
};
