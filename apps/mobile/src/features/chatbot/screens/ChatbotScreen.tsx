import Ionicons from '@expo/vector-icons/Ionicons';
import { useRef, useState } from 'react';
import {
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { colors, spacing } from '@/src/theme';

import { ChatMapResponse } from '../components/ChatMapResponse';
import { chatbotAssets } from '../config/chatbotAssets';
import { getMapPlacesForQuestion, needsMapResponse } from '../data/chatbotMapResponse';
import { chatbotSuggestions } from '../data/chatbotSuggestions';
import type { ChatMessage } from '../types/chatbot';

const API_PLACEHOLDER_RESPONSE =
  '현재는 화면 디자인 단계예요. AI API가 연결되면 혼디가 제주 여행 정보를 찾아 답변해드릴게요.';

export function ChatbotScreen() {
  const scrollRef = useRef<ScrollView>(null);
  const composerOffset = useRef(0);
  const nextMessageId = useRef(1);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const sendMessage = (text: string) => {
    const normalizedText = text.trim();
    if (!normalizedText) return;
    const showMap = needsMapResponse(normalizedText);

    const userMessage: ChatMessage = {
      id: nextMessageId.current++,
      role: 'user',
      text: normalizedText,
    };
    const assistantMessage: ChatMessage = {
      id: nextMessageId.current++,
      role: 'assistant',
      text: showMap
        ? '요청하신 조건에 맞는 추천 장소를 지도에 정리했어요. 장소 데이터는 추후 API와 연결될 예정이에요.'
        : API_PLACEHOLDER_RESPONSE,
      mapPlaces: showMap ? getMapPlacesForQuestion(normalizedText) : undefined,
    };

    setMessages((currentMessages) => [...currentMessages, userMessage, assistantMessage]);
    setInput('');
    requestAnimationFrame(() =>
      scrollRef.current?.scrollTo({
        animated: true,
        y: Math.max(0, composerOffset.current - 12),
      }),
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.keyboardArea}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          ref={scrollRef}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.content}>
            <View style={styles.header}>
              <View style={styles.brand}>
                <View style={styles.brandIcon}>
                  <Ionicons color={colors.surface} name="paw" size={17} />
                </View>
                <Text style={styles.brandText}>오멍가멍</Text>
              </View>
              <Pressable accessibilityLabel="알림" hitSlop={10}>
                <Ionicons color={colors.textPrimary} name="notifications-outline" size={23} />
              </Pressable>
            </View>

            <View style={styles.hero}>
              <Text style={styles.heroTitle}>
                <Text style={styles.heroTitleAccent}>혼디</Text>에게 물어보세요!
              </Text>
              <Text style={styles.heroDescription}>
                반려동물과 함께하는 제주 여행,{`\n`}혼디가 친절하게 알려줄게요.
              </Text>
              <View style={styles.mascotFrame}>
                {chatbotAssets.mascot ? (
                  <Image
                    accessibilityLabel="혼디 캐릭터"
                    resizeMode="contain"
                    source={chatbotAssets.mascot}
                    style={styles.mascot}
                  />
                ) : (
                  <View
                    accessibilityLabel="혼디 캐릭터 플레이스홀더"
                    style={styles.mascotPlaceholder}
                  >
                    <View style={styles.mascotIconCircle}>
                      <Ionicons color={colors.primary} name="paw" size={42} />
                    </View>
                    <Text style={styles.mascotPlaceholderText}>혼디 캐릭터</Text>
                  </View>
                )}
              </View>
              <Text style={styles.assetHint}>캐릭터 이미지 추후 교체 예정</Text>
            </View>

            <View
              onLayout={(event) => {
                composerOffset.current = event.nativeEvent.layout.y;
              }}
              style={styles.composerSection}
            >
              <Text style={styles.sectionTitle}>혼디에게 무엇이든 물어보세요</Text>
              <View style={styles.composer}>
                <TextInput
                  accessibilityLabel="혼디에게 질문 입력"
                  blurOnSubmit={false}
                  onChangeText={setInput}
                  onSubmitEditing={() => sendMessage(input)}
                  placeholder="제주 여행에 대해 궁금한 점을 입력해보세요"
                  placeholderTextColor="#9B9692"
                  returnKeyType="send"
                  style={styles.input}
                  value={input}
                />
                <Pressable
                  accessibilityLabel="질문 보내기"
                  accessibilityState={{ disabled: !input.trim() }}
                  disabled={!input.trim()}
                  onPress={() => sendMessage(input)}
                  style={({ pressed }) => [
                    styles.sendButton,
                    !input.trim() && styles.sendButtonDisabled,
                    pressed && styles.pressed,
                  ]}
                >
                  <Ionicons color={colors.surface} name="paper-plane" size={20} />
                </Pressable>
              </View>
              <Text style={styles.apiHint}>AI 답변은 백엔드 API 연동 예정</Text>
            </View>

            {messages.length > 0 ? (
              <View accessibilityLiveRegion="polite" style={styles.messageList}>
                {messages.map((message) => (
                  <View
                    key={message.id}
                    style={[
                      styles.messageGroup,
                      message.role === 'user' && styles.userMessageGroup,
                    ]}
                  >
                    {message.role === 'user' ? (
                      <View style={[styles.messageBubble, styles.userBubble]}>
                        <Text style={[styles.messageText, styles.userMessageText]}>
                          {message.text}
                        </Text>
                      </View>
                    ) : (
                      <View style={styles.assistantResponse}>
                        <View style={styles.assistantAvatar}>
                          {chatbotAssets.mascot ? (
                            <Image
                              accessibilityLabel="혼디 캐릭터 아바타"
                              resizeMode="cover"
                              source={chatbotAssets.mascot}
                              style={styles.assistantAvatarImage}
                            />
                          ) : (
                            <Ionicons color={colors.primary} name="paw" size={17} />
                          )}
                        </View>
                        <View style={styles.assistantContent}>
                          <View style={[styles.messageBubble, styles.assistantBubble]}>
                            <View style={styles.assistantLabel}>
                              <Text style={styles.assistantLabelText}>혼디</Text>
                            </View>
                            <Text style={styles.messageText}>{message.text}</Text>
                          </View>
                          {message.mapPlaces ? (
                            <ChatMapResponse places={message.mapPlaces} />
                          ) : null}
                        </View>
                      </View>
                    )}
                  </View>
                ))}
              </View>
            ) : null}

            <View style={styles.suggestionSection}>
              <View style={styles.suggestionHeading}>
                <Text style={styles.sectionTitle}>이런 질문은 어때요?</Text>
                <View style={styles.popularBadge}>
                  <Ionicons color={colors.primary} name="sparkles" size={12} />
                  <Text style={styles.popularBadgeText}>인기 질문</Text>
                </View>
              </View>

              <View style={styles.suggestionList}>
                {chatbotSuggestions.map((suggestion) => (
                  <Pressable
                    accessibilityHint="선택한 질문을 채팅창에 바로 전송합니다"
                    accessibilityRole="button"
                    key={suggestion.id}
                    onPress={() => sendMessage(suggestion.question)}
                    style={({ pressed }) => [styles.suggestionCard, pressed && styles.pressed]}
                  >
                    <View style={styles.suggestionIcon}>
                      <Ionicons color={colors.primary} name={suggestion.icon} size={19} />
                    </View>
                    <Text style={styles.suggestionText}>{suggestion.question}</Text>
                    <Ionicons color="#A7A29E" name="chevron-forward" size={19} />
                  </Pressable>
                ))}
              </View>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  keyboardArea: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingBottom: 32,
  },
  content: {
    width: '100%',
    maxWidth: 720,
    paddingHorizontal: spacing.md,
    alignSelf: 'center',
  },
  header: {
    height: 54,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
  },
  brandIcon: {
    width: 29,
    height: 29,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
  },
  brandText: {
    color: colors.primary,
    fontSize: 19,
    fontWeight: '900',
    letterSpacing: -0.8,
  },
  hero: {
    alignItems: 'center',
    paddingTop: 18,
  },
  heroTitle: {
    color: colors.textPrimary,
    fontSize: 25,
    fontWeight: '900',
    letterSpacing: -1,
  },
  heroTitleAccent: {
    color: colors.primary,
  },
  heroDescription: {
    marginTop: 9,
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 20,
    textAlign: 'center',
  },
  mascotFrame: {
    width: '100%',
    height: 180,
    marginTop: 5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  mascot: {
    width: '100%',
    height: '100%',
  },
  mascotPlaceholder: {
    alignItems: 'center',
  },
  mascotIconCircle: {
    width: 118,
    height: 118,
    borderWidth: 1,
    borderColor: '#FFDCC8',
    borderRadius: 59,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFF3EA',
  },
  mascotPlaceholderText: {
    marginTop: 8,
    color: colors.primary,
    fontSize: 12,
    fontWeight: '800',
  },
  assetHint: {
    marginTop: -8,
    color: '#A09A96',
    fontSize: 10,
  },
  messageList: {
    marginTop: 21,
    gap: 10,
  },
  messageGroup: {
    width: '100%',
    alignItems: 'flex-start',
  },
  userMessageGroup: {
    alignItems: 'flex-end',
  },
  assistantResponse: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  assistantAvatar: {
    width: 34,
    height: 34,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#FFDCC8',
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFF3EA',
  },
  assistantAvatarImage: {
    width: '100%',
    height: '100%',
  },
  assistantContent: {
    flex: 1,
    alignItems: 'flex-start',
  },
  messageBubble: {
    maxWidth: '84%',
    paddingHorizontal: 14,
    paddingVertical: 11,
    borderRadius: 16,
  },
  userBubble: {
    borderBottomRightRadius: 5,
    backgroundColor: colors.primary,
  },
  assistantBubble: {
    maxWidth: '100%',
    borderWidth: 1,
    borderColor: '#F0E5DF',
    borderBottomLeftRadius: 5,
    backgroundColor: '#FFF8F3',
  },
  assistantLabel: {
    marginBottom: 5,
  },
  assistantLabelText: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: '800',
  },
  messageText: {
    color: colors.textPrimary,
    fontSize: 13,
    lineHeight: 19,
  },
  userMessageText: {
    color: colors.surface,
    fontWeight: '600',
  },
  composerSection: {
    marginTop: 26,
  },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: -0.3,
  },
  composer: {
    minHeight: 54,
    marginTop: 11,
    paddingLeft: 15,
    paddingRight: 6,
    paddingVertical: 5,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: '#E7E2DE',
    borderRadius: 18,
    backgroundColor: colors.surface,
    shadowColor: '#64351E',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 2,
  },
  input: {
    flex: 1,
    paddingVertical: 8,
    color: colors.textPrimary,
    fontSize: 13,
  },
  sendButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
  },
  sendButtonDisabled: {
    backgroundColor: '#D9D4D0',
  },
  pressed: {
    opacity: 0.68,
  },
  apiHint: {
    marginTop: 7,
    marginRight: 3,
    color: '#A09A96',
    fontSize: 10,
    textAlign: 'right',
  },
  suggestionSection: {
    marginTop: 24,
  },
  suggestionHeading: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  popularBadge: {
    paddingHorizontal: 9,
    paddingVertical: 5,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: 11,
    backgroundColor: '#FFF3EA',
  },
  popularBadgeText: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: '800',
  },
  suggestionList: {
    marginTop: 11,
    gap: 9,
  },
  suggestionCard: {
    minHeight: 56,
    paddingHorizontal: 12,
    paddingVertical: 9,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: '#EEE8E4',
    borderRadius: 15,
    backgroundColor: colors.surface,
    shadowColor: '#64351E',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 1,
  },
  suggestionIcon: {
    width: 34,
    height: 34,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFF3EA',
  },
  suggestionText: {
    flex: 1,
    color: '#4F4A47',
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 18,
  },
});
