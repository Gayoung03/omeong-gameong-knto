import type Ionicons from '@expo/vector-icons/Ionicons';
import type { ComponentProps } from 'react';

export type IoniconName = ComponentProps<typeof Ionicons>['name'];

export type WeatherSummary = {
  greeting: string;
  location: string;
  temperature: number;
  condition: string;
  humidity: number;
  windSpeed: number;
  tip: string;
};

export type QuickMenuDestination = 'chatbot' | 'place-explorer' | 'coming-soon';

export type QuickMenuItem = {
  id: string;
  title: string;
  subtitle: string;
  icon: IoniconName;
  iconColor: string;
  iconBackgroundColor: string;
  destination: QuickMenuDestination;
};

export type EditorialCard = {
  id: string;
  title: string;
  imageUrl: string;
};
