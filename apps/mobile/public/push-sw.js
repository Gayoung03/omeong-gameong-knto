self.addEventListener('push', (event) => {
  const payload = event.data?.json() ?? {};
  event.waitUntil(
    self.registration.showNotification(payload.title ?? '오멍가멍', {
      body: payload.body ?? '',
      data: payload.data ?? {},
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const { type, targetId } = event.notification.data ?? {};
  const paths = {
    chat_answer_ready: '/chatbot',
    inquiry_answered: targetId ? `/inquiries/${targetId}` : '/inquiries',
    notice: '/notices',
    route_ready: targetId ? `/trips/${targetId}` : '/trips',
    travel_log_ready: '/travel-logs',
  };
  const url = new URL(paths[type] ?? '/notifications', self.location.origin).href;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
      const current = windows[0];
      if (current) {
        current.navigate(url);
        return current.focus();
      }
      return clients.openWindow(url);
    }),
  );
});
