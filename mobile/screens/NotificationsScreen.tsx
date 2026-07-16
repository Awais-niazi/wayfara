/**
 * 07 — NOTIFICATIONS (inbox)
 * The durable feed behind the Home bell: every reminder, advisor message,
 * announcement and university update the platform has sent this student.
 * Push mirrors these; this screen is the record. Opening it marks the loaded
 * page read (badge clears), newest first, paged with "Load earlier".
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts, radius, shadow } from "../theme";
import { ChevronLeftIcon, BellIcon } from "../components/icons";
import { FadeInUp } from "../components/motion";
import {
  getNotifications,
  markNotificationsRead,
  type AppNotification,
  type NotificationCategory,
} from "../lib/api";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Notifications">;

// Visual identity per category: label + ink, all drawn from the warm palette
// (semantic greens/ambers stay; no off-brand purples/blues).
const CATEGORY_META: Record<NotificationCategory, { label: string; color: string }> = {
  reminder: { label: "Reminder", color: "#B4841A" },
  advisor: { label: "Advisor", color: "#C7502F" },
  news: { label: "News", color: "#6F5F50" },
  update: { label: "Update", color: "#C7502F" },
  system: { label: "Wayfara", color: colors.accent },
  document: { label: "Documents", color: "#1F8A5B" },
  application: { label: "Application", color: "#1F8A5B" },
  visa: { label: "Visa", color: colors.accent },
};

function timeAgo(iso: string): string {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export default function NotificationsScreen({ navigation }: Props) {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);

  const markPageRead = (page: AppNotification[]) => {
    const unreadIds = page.filter((n) => n.read_at === null).map((n) => n.id);
    if (unreadIds.length === 0) return;
    // Fire-and-forget; reflect locally so rows render as read next visit
    // while keeping the "new" highlight for this one.
    markNotificationsRead({ ids: unreadIds }).catch(() => {});
  };

  const load = useCallback(async (mode: "initial" | "refresh") => {
    mode === "initial" ? setLoading(true) : setRefreshing(true);
    try {
      const page = await getNotifications();
      setItems(page.results);
      setHasMore(page.has_more);
      setError(false);
      markPageRead(page.results);
    } catch {
      if (mode === "initial") setError(true);
    } finally {
      mode === "initial" ? setLoading(false) : setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load("initial");
  }, [load]);

  const loadEarlier = async () => {
    if (loadingMore || items.length === 0) return;
    setLoadingMore(true);
    try {
      const page = await getNotifications(items[items.length - 1].id);
      setItems((prev) => [...prev, ...page.results]);
      setHasMore(page.has_more);
      markPageRead(page.results);
    } catch {
      // Keep what we have; the footer button remains for retry.
    } finally {
      setLoadingMore(false);
    }
  };

  const renderItem = ({ item, index }: { item: AppNotification; index: number }) => {
    const meta = CATEGORY_META[item.category] ?? CATEGORY_META.system;
    const unread = item.read_at === null;
    return (
      <FadeInUp delay={Math.min(index, 8) * 40}>
      <View style={[styles.card, unread && styles.cardUnread]}>
        <View style={[styles.catBadge, { borderColor: meta.color }]}>
          <BellIcon size={15} color={meta.color} />
        </View>
        <View style={{ flex: 1 }}>
          <View style={styles.cardHead}>
            <Text style={[styles.catLabel, { color: meta.color }]}>{meta.label}</Text>
            <Text style={styles.time}>{timeAgo(item.created_at)}</Text>
          </View>
          <Text style={styles.title}>{item.title}</Text>
          {item.body !== "" && (
            <Text style={styles.body} numberOfLines={3}>
              {item.body}
            </Text>
          )}
        </View>
        {unread && <View style={styles.unreadDot} />}
      </View>
      </FadeInUp>
    );
  };

  return (
    <SafeAreaView edges={["top"]} style={styles.root}>
      <View style={styles.topBar}>
        <Pressable
          onPress={navigation.goBack}
          accessibilityRole="button"
          accessibilityLabel="Go back"
          hitSlop={8}
          style={({ pressed }) => [styles.backBtn, pressed && { opacity: 0.7 }]}
        >
          <ChevronLeftIcon size={20} />
        </Pressable>
        <Text style={styles.screenTitle}>Notifications</Text>
      </View>

      {loading && (
        <View style={styles.centerBox}>
          <ActivityIndicator color={colors.accent} />
        </View>
      )}

      {error && !loading && (
        <Pressable style={styles.errorBox} onPress={() => load("initial")}>
          <Text style={styles.errorText}>Couldn't load your notifications.</Text>
          <Text style={styles.errorRetry}>Tap to retry</Text>
        </Pressable>
      )}

      {!loading && !error && (
        <FlatList
          data={items}
          keyExtractor={(n) => String(n.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => load("refresh")}
              tintColor={colors.accent}
            />
          }
          ListEmptyComponent={
            <View style={styles.centerBox}>
              <View style={styles.emptyBadge}>
                <BellIcon size={22} color={colors.accent} />
              </View>
              <Text style={styles.emptyTitle}>Nothing yet</Text>
              <Text style={styles.emptyText}>
                No news is good news — we'll ping you the moment something needs you.
              </Text>
            </View>
          }
          ListFooterComponent={
            hasMore ? (
              <Pressable style={styles.moreBtn} onPress={loadEarlier} disabled={loadingMore}>
                <Text style={styles.moreText}>
                  {loadingMore ? "Loading…" : "Load earlier"}
                </Text>
              </Pressable>
            ) : null
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 6,
  },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  screenTitle: { fontFamily: fonts.display, fontSize: 20, letterSpacing: -0.4, color: colors.ink },

  centerBox: { alignItems: "center", paddingVertical: 70, paddingHorizontal: 32, gap: 8 },
  errorBox: {
    margin: 20,
    backgroundColor: "#FCEBE7",
    borderWidth: 1,
    borderColor: "#F3C4B8",
    borderRadius: radius["2xl"],
    padding: 18,
    alignItems: "center",
    gap: 4,
  },
  errorText: { fontFamily: fonts.bodySemi, fontSize: 13.5, color: "#B3402A" },
  errorRetry: { fontFamily: fonts.bodyBold, fontSize: 13, color: colors.accent },

  list: { padding: 16, gap: 10, flexGrow: 1, paddingBottom: 32 },
  card: {
    flexDirection: "row",
    gap: 12,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.xl,
    padding: 14,
    ...shadow.card,
  },
  cardUnread: { borderColor: "#F3D3B8", backgroundColor: "#FFFBF5" },
  catBadge: {
    width: 34,
    height: 34,
    borderRadius: 11,
    borderWidth: 1.4,
    alignItems: "center",
    justifyContent: "center",
  },
  cardHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  catLabel: { fontFamily: fonts.monoBold, fontSize: 9.5, letterSpacing: 1.2, textTransform: "uppercase" },
  time: { fontFamily: fonts.mono, fontSize: 10, letterSpacing: 0.4, color: colors.textFaintest },
  title: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.ink, marginTop: 3 },
  body: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 2, lineHeight: 17 },
  unreadDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: colors.accent,
    alignSelf: "center",
  },

  emptyBadge: {
    width: 52,
    height: 52,
    borderRadius: 16,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  emptyTitle: { fontFamily: fonts.display, fontSize: 17, color: colors.ink },
  emptyText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textFaint,
    textAlign: "center",
    lineHeight: 19,
  },

  moreBtn: {
    marginTop: 6,
    height: 44,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  moreText: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.accent },
});
