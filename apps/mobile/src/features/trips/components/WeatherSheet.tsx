import Ionicons from '@expo/vector-icons/Ionicons';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

import type { ScheduleWeather } from '../types/trip';
import type { PetWalkTipTone } from '../utils/tripFormat';
import {
  formatFullDate,
  formatTemperatureRange,
  getMaxPrecipitationProbability,
  getPetWalkTip,
  getWeatherIcon,
  getWeatherLabel,
} from '../utils/tripFormat';

type WeatherSheetProps = {
  dayNumber: number;
  /** YYYY-MM-DD */
  date: string;
  weather: ScheduleWeather;
  onClose: () => void;
};

const TIP_TONE_STYLES: Record<PetWalkTipTone, { background: string; accent: string }> = {
  caution: { background: colors.primarySoft, accent: colors.primary },
  watch: { background: colors.seaSoft, accent: colors.sea },
  good: { background: colors.leafSoft, accent: colors.leaf },
};

const TIP_TONE_ICONS: Record<PetWalkTipTone, keyof typeof Ionicons.glyphMap> = {
  caution: 'alert-circle',
  watch: 'information-circle',
  good: 'happy-outline',
};

export function WeatherSheet({ dayNumber, date, weather, onClose }: WeatherSheetProps) {
  const walkTip = getPetWalkTip(weather.condition, weather.maxTemperature);
  const tipTone = TIP_TONE_STYLES[walkTip.tone];
  const maxPrecipitation = getMaxPrecipitationProbability(weather);

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible>
      <View style={styles.backdrop}>
        <Pressable
          accessibilityLabel="닫기"
          accessibilityRole="button"
          onPress={onClose}
          style={styles.backdropArea}
        />

        <View style={styles.sheet}>
          <View style={styles.grip} />

          <View style={styles.header}>
            <View>
              <Text style={styles.headerTitle}>Day {dayNumber} 날씨</Text>
              <Text style={styles.headerDate}>{formatFullDate(date)}</Text>
            </View>
            <Pressable
              accessibilityLabel="닫기"
              accessibilityRole="button"
              hitSlop={spacing.sm}
              onPress={onClose}
            >
              <Ionicons color={colors.textSecondary} name="close" size={22} />
            </Pressable>
          </View>

          <View style={styles.summary}>
            <Text style={styles.summaryIcon}>{getWeatherIcon(weather.condition)}</Text>
            <View style={styles.summaryTexts}>
              <Text style={styles.summaryTemperature}>{weather.temperature}°</Text>
              <Text style={styles.summaryCondition}>
                {getWeatherLabel(weather.condition)} · {formatTemperatureRange(weather)}
              </Text>
            </View>
            <View style={styles.precipitationBadge}>
              <Ionicons color={colors.sea} name="water-outline" size={13} />
              <Text style={styles.precipitationText}>최대 {maxPrecipitation}%</Text>
            </View>
          </View>

          {weather.hourly.length > 0 ? (
            <ScrollView
              contentContainerStyle={styles.hourlyContent}
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.hourlyScroll}
            >
              {weather.hourly.map((hour) => (
                <View key={hour.time} style={styles.hourlyCard}>
                  <Text style={styles.hourlyTime}>{hour.time}</Text>
                  <Text style={styles.hourlyIcon}>{getWeatherIcon(hour.condition)}</Text>
                  <Text style={styles.hourlyTemperature}>{hour.temperature}°</Text>
                  <View style={styles.hourlyPrecipitation}>
                    <Ionicons color={colors.sea} name="water-outline" size={11} />
                    <Text style={styles.hourlyPrecipitationText}>
                      {hour.precipitationProbability}%
                    </Text>
                  </View>
                </View>
              ))}
            </ScrollView>
          ) : (
            <View style={styles.emptyHourly}>
              <Text style={styles.emptyHourlyText}>시간대별 예보를 아직 받아오지 못했어요</Text>
            </View>
          )}

          <View style={[styles.tipCard, { backgroundColor: tipTone.background }]}>
            <View style={styles.tipHeader}>
              <Ionicons color={tipTone.accent} name={TIP_TONE_ICONS[walkTip.tone]} size={16} />
              <Text style={[styles.tipTitle, { color: tipTone.accent }]}>{walkTip.title}</Text>
            </View>
            <Text style={styles.tipDescription}>{walkTip.description}</Text>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: overlayColors.scrim,
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdropArea: {
    flex: 1,
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl + 4,
    borderTopRightRadius: radius.xl + 4,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  grip: {
    alignSelf: 'center',
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 4,
    marginBottom: spacing.md,
    width: 40,
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  headerTitle: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: typography.sectionTitle.fontWeight,
  },
  headerDate: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    marginTop: 2,
  },
  summary: {
    alignItems: 'center',
    backgroundColor: colors.basaltSoft,
    borderRadius: radius.lg,
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
  },
  summaryIcon: {
    fontSize: 34,
  },
  summaryTexts: {
    flex: 1,
  },
  summaryTemperature: {
    color: colors.basalt,
    fontSize: typography.title.fontSize,
    fontWeight: typography.title.fontWeight,
  },
  summaryCondition: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    marginTop: 2,
  },
  precipitationBadge: {
    alignItems: 'center',
    backgroundColor: colors.seaSoft,
    borderRadius: radius.full,
    flexDirection: 'row',
    gap: 3,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  precipitationText: {
    color: colors.sea,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  hourlyScroll: {
    marginTop: spacing.md,
  },
  hourlyContent: {
    gap: spacing.sm,
    paddingRight: spacing.sm,
  },
  hourlyCard: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing.xs,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.sm + 2,
    width: 68,
  },
  hourlyTime: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  hourlyIcon: {
    fontSize: 20,
  },
  hourlyTemperature: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  hourlyPrecipitation: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 2,
  },
  hourlyPrecipitationText: {
    color: colors.sea,
    fontSize: typography.micro.fontSize - 1,
    fontWeight: typography.micro.fontWeight,
  },
  emptyHourly: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    marginTop: spacing.md,
    paddingVertical: spacing.lg,
  },
  emptyHourlyText: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
  },
  tipCard: {
    borderRadius: radius.lg,
    gap: spacing.xs,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md - 2,
  },
  tipHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs + 2,
  },
  tipTitle: {
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  tipDescription: {
    color: colors.textPrimary,
    fontSize: typography.caption.fontSize,
    lineHeight: 19,
  },
});
