import Ionicons from '@expo/vector-icons/Ionicons';
import { type ReactNode, useRef, useState } from 'react';
import {
  ActivityIndicator,
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

import { AppHeader } from '@/src/components/layout/AppHeader';
import { colors, spacing } from '@/src/theme';

import { ChatMapResponse } from '../components/ChatMapResponse';
import { chatbotAssets } from '../config/chatbotAssets';
import { chatbotSuggestions } from '../constants/chatbotSuggestions';
import { entryKey, useChatbot } from '../hooks/useChatbot';
import type { ChatEntry } from '../types/chatbot';

export function ChatbotScreen() {
  const scrollRef = useRef<ScrollView>(null);
  const [input, setInput] = useState('');
  const { entries, isAnswering, ask, retry } = useChatbot();
  const hasMessages = entries.length > 0;
  const canSend = Boolean(input.trim()) && !isAnswering;

  const sendMessage = (text: string) => {
    const normalizedText = text.trim();
    if (!normalizedText || isAnswering) return;

    setInput('');
    void ask(normalizedText);
  };

  const renderComposer = (showContext: boolean) => (
    <View style={showContext ? styles.composerSection : styles.activeComposerSection}>
      {showContext ? (
        <Text style={styles.sectionTitle}>혼디에게 무엇이든 물어보세요</Text>
      ) : null}
      <View style={[styles.composer, !showContext && styles.activeComposer]}>
        <TextInput
          accessibilityLabel="혼디에게 질문 입력"
          blurOnSubmit={false}
          // 답변을 만드는 동안은 잠근다(설계 결정 F3). 두 질문이 겹치면
          // 어느 답변이 어느 질문의 것인지 화면에서 구분할 수 없다.
          editable={!isAnswering}
          onChangeText={setInput}
          onSubmitEditing={() => sendMessage(input)}
          placeholder={
            isAnswering ? '혼디가 답변을 만들고 있어요…' : '제주 여행에 대해 궁금한 점을 입력해보세요'
          }
          placeholderTextColor={colors.textTertiary}
          returnKeyType="send"
          style={styles.input}
          value={input}
        />
        <Pressable
          accessibilityLabel="질문 보내기"
          accessibilityState={{ disabled: !canSend }}
          disabled={!canSend}
          onPress={() => sendMessage(input)}
          style={({ pressed }) => [
            styles.sendButton,
            !canSend && styles.sendButtonDisabled,
            pressed && styles.pressed,
          ]}
        >
          {isAnswering ? (
            <ActivityIndicator color={colors.surface} size="small" />
          ) : (
            <Ionicons color={colors.surface} name="paper-plane" size={20} />
          )}
        </Pressable>
      </View>
    </View>
  );

  const renderUserBubble = (content: string) => (
    <View style={[styles.messageBubble, styles.userBubble]}>
      <Text style={[styles.messageText, styles.userMessageText]}>{content}</Text>
    </View>
  );

  const renderHondi = (body: ReactNode) => (
    <View style={styles.assistantResponse}>
      <View style={styles.assistantAvatar}>
        <Image
          accessibilityLabel="혼디 강아지 캐릭터 아바타"
          resizeMode="cover"
          source={chatbotAssets.avatar}
          style={styles.assistantAvatarImage}
        />
      </View>
      <View style={styles.assistantContent}>{body}</View>
    </View>
  );

  const renderEntry = (entry: ChatEntry) => {
    if (entry.kind === 'pending') {
      return (
        <>
          <View style={[styles.messageGroup, styles.userMessageGroup]}>
            {renderUserBubble(entry.content)}
          </View>
          <View style={styles.messageGroup}>
            {renderHondi(
              <View style={[styles.messageBubble, styles.assistantBubble, styles.pendingBubble]}>
                <ActivityIndicator color={colors.primary} size="small" />
                <Text style={styles.pendingText}>혼디가 장소를 찾고 있어요…</Text>
              </View>,
            )}
          </View>
        </>
      );
    }

    if (entry.kind === 'failed') {
      return (
        <>
          <View style={[styles.messageGroup, styles.userMessageGroup]}>
            {renderUserBubble(entry.question)}
          </View>
          <View style={styles.messageGroup}>
            {renderHondi(
              <View style={[styles.messageBubble, styles.failedBubble]}>
                <Text style={styles.failedText}>{entry.description}</Text>
                <Pressable
                  accessibilityRole="button"
                  onPress={() => retry(entry.localId)}
                  style={({ pressed }) => [styles.retryButton, pressed && styles.pressed]}
                >
                  <Ionicons color={colors.primary} name="refresh" size={14} />
                  <Text style={styles.retryText}>다시 시도</Text>
                </Pressable>
              </View>,
            )}
          </View>
        </>
      );
    }

    const { message } = entry;
    if (message.role === 'user') {
      return (
        <View style={[styles.messageGroup, styles.userMessageGroup]}>
          {renderUserBubble(message.content)}
        </View>
      );
    }

    return (
      <View style={styles.messageGroup}>
        {renderHondi(
          <>
            <View style={[styles.messageBubble, styles.assistantBubble]}>
              <View style={styles.assistantLabel}>
                <Text style={styles.assistantLabelText}>혼디</Text>
              </View>
              <Text style={styles.messageText}>{message.content}</Text>
            </View>
            {/*
              지도를 띄울지는 **서버가 정한다.** 답변이 언급한 장소만
              referencedPlaces 로 오므로, 비어 있으면 글만 나간다(설계 결정 C5).
              예전에는 앱이 '카페' 같은 단어를 보고 판단해서, 서버가 장소를
              못 찾았는데도 빈 지도가 뜨는 일이 있었다.
            */}
            {message.referencedPlaces.length > 0 ? (
              <ChatMapResponse places={message.referencedPlaces} />
            ) : null}
          </>,
        )}
      </View>
    );
  };

  const renderMessages = () => (
    <View accessibilityLiveRegion="polite" style={styles.messageList}>
      {entries.map((entry) => (
        <View key={entryKey(entry)}>{renderEntry(entry)}</View>
      ))}
    </View>
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.keyboardArea}
      >
        <View style={styles.screen}>
          <AppHeader notifications="popup" />

          {hasMessages ? (
            <>
              <ScrollView
                contentContainerStyle={styles.activeChatScrollContent}
                keyboardShouldPersistTaps="handled"
                // 말풍선이 늘어날 때마다 맨 아래로 붙인다. 대기 말풍선이 진짜
                // 답변으로 바뀌면서 높이가 커지는 경우까지 이걸로 덮인다.
                onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
                ref={scrollRef}
                showsVerticalScrollIndicator={false}
                style={styles.activeChatScroll}
              >
                <View style={styles.content}>{renderMessages()}</View>
              </ScrollView>
              <View style={styles.activeComposerBar}>
                <View style={styles.content}>{renderComposer(false)}</View>
              </View>
            </>
          ) : (
            <ScrollView
              contentContainerStyle={styles.scrollContent}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
            >
              <View style={styles.content}>
                <View style={styles.hero}>
                  <Text style={styles.heroTitle}>
                    <Text style={styles.heroTitleAccent}>혼디</Text>에게 물어보세요!
                  </Text>
                  <Text style={styles.heroDescription}>
                    반려동물과 함께하는 제주 여행,{'\n'}혼디가 친절하게 알려줄게요.
                  </Text>
                  <View style={styles.mascotFrame}>
                    <Image
                      accessibilityLabel="여행 정보를 찾는 혼디 강아지 캐릭터"
                      resizeMode="contain"
                      source={chatbotAssets.hero}
                      style={styles.mascot}
                    />
                  </View>
                </View>

                {renderComposer(true)}

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
                        style={({ pressed }) => [
                          styles.suggestionCard,
                          pressed && styles.pressed,
                        ]}
                      >
                        <View style={styles.suggestionIcon}>
                          <Ionicons color={colors.primary} name={suggestion.icon} size={19} />
                        </View>
                        <Text style={styles.suggestionText}>{suggestion.question}</Text>
                        <Ionicons color={colors.textTertiary} name="chevron-forward" size={19} />
                      </Pressable>
                    ))}
                  </View>
                </View>
              </View>
            </ScrollView>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  pendingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  pendingText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  failedBubble: {
    backgroundColor: colors.errorBg,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  failedText: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 21,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 4,
    paddingVertical: 4,
  },
  retryText: {
    color: colors.primary,
    fontSize: 13,
    fontWeight: '600',
  },
  safeArea: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  keyboardArea: {
    flex: 1,
  },
  screen: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingBottom: 32,
  },
  activeChatScroll: {
    flex: 1,
  },
  activeChatScrollContent: {
    flexGrow: 1,
    paddingBottom: 12,
  },
  content: {
    width: '100%',
    maxWidth: 720,
    paddingHorizontal: spacing.md,
    alignSelf: 'center',
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
  messageList: {
    marginTop: 12,
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
    borderColor: colors.primarySoftStrong,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primarySoft,
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
    borderColor: colors.basaltSoft,
    borderBottomLeftRadius: 5,
    backgroundColor: colors.primarySoft,
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
  activeComposerBar: {
    borderTopWidth: 1,
    borderTopColor: colors.basaltSoft,
    backgroundColor: colors.surface,
  },
  activeComposerSection: {
    paddingTop: 10,
    paddingBottom: 12,
  },
  activeComposer: {
    marginTop: 0,
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
    borderColor: colors.divider,
    borderRadius: 18,
    backgroundColor: colors.surface,
    shadowColor: colors.primaryInk,
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
    backgroundColor: colors.divider,
  },
  pressed: {
    opacity: 0.68,
  },
  apiHint: {
    marginTop: 7,
    marginRight: 3,
    color: colors.textTertiary,
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
    backgroundColor: colors.primarySoft,
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
    borderColor: colors.basaltSoft,
    borderRadius: 15,
    backgroundColor: colors.surface,
    shadowColor: colors.primaryInk,
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
    backgroundColor: colors.primarySoft,
  },
  suggestionText: {
    flex: 1,
    color: colors.textStrong,
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 18,
  },
});
