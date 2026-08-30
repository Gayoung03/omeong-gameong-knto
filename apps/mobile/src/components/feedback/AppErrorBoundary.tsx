import { Component, type ReactNode } from 'react';
import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { sanitizeErrorForLog } from '@/src/services/apiError';
import { colors } from '@/src/theme';

import { EmptyState } from './EmptyState';

type Props = { children: ReactNode };
type State = { hasError: boolean };

/**
 * 화면을 그리다가 예상 못한 오류로 앱이 죽으려 하면 하얀 화면 대신 이 화면을 보여준다.
 * 개별 화면의 API 실패(isError)는 각 화면·ErrorState 가 따로 처리하므로 여기서는
 * 다루지 않는다. 이건 render 도중 던져진 예외를 잡는 최후의 안전망이다.
 */
export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    // TODO: 크래시 리포팅 도구(Sentry 등) 연결 시 여기서 함께 전송한다.
    // 원본 error 를 그대로 찍으면 AxiosError 의 토큰·비밀번호가 로그에 샌다 — 새니타이즈.
    console.error('[AppErrorBoundary]', sanitizeErrorForLog(error));
  }

  private handleRetry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <SafeAreaView style={styles.safeArea}>
        <EmptyState
          actionLabel="다시 시도"
          description="일시적인 문제예요. 다시 시도해도 안 되면 앱을 껐다 켜주세요."
          icon="alert-circle-outline"
          onPressAction={this.handleRetry}
          title="문제가 생겼어요"
        />
      </SafeAreaView>
    );
  }
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});
