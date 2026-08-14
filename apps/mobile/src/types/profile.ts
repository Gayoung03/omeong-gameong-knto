export interface ActivitySummary {
  savedPlacesCount: number;
  savedCoursesCount: number;
  travelLogsCount: number;
}

export interface RecentVisit {
  placeId: string;
  placeName: string;
  date: string;
  image: string;
}
