import type Ionicons from '@expo/vector-icons/Ionicons';
import type { ComponentProps } from 'react';

export type IoniconName = ComponentProps<typeof Ionicons>['name'];

export type WeatherSummary = {
  location: string;
  temperature: number;
  condition: WeatherCondition;
  conditionLabel: string;
  precipitationProbability: number;
  humidity: number;
  windSpeed: number;
  tip: string;
};

export type WeatherCondition =
  | 'sunny'
  | 'partly_cloudy'
  | 'cloudy'
  | 'rainy'
  | 'snowy'
  | 'windy';

export type QuickMenuDestination =
  'chatbot' | 'place-explorer' | 'travel-preparation' | 'travel-log-new' | 'saved-places';

export type QuickMenuItem = {
  id: string;
  title: string;
  subtitle: string;
  icon: IoniconName;
  iconColor: string;
  iconBackgroundColor: string;
  destination: QuickMenuDestination;
};

export type EditorialStorySection = {
  id: string;
  heading: string;
  paragraphs: string[];
  imageUrl?: string;
  imageCaption?: string;
};

export type EditorialStory = {
  id: string;
  slug: string;
  kind: 'event' | 'weather' | 'story' | 'guide';
  category: string;
  cardTitle: string;
  title: string;
  summary: string;
  heroImageUrl: string;
  publishedAt: string;
  readingMinutes: number;
  author: string;
  sections: EditorialStorySection[];
  tips: string[];
  tags: string[];
  sources: {
    sourceName: string;
    sourceTitle: string;
    sourceUrl: string;
    sourcePublishedAt: string | null;
  }[];
};
