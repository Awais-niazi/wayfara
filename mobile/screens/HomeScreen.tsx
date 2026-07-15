/**
 * 03 — HOME · UNIVERSITY MATCHES
 * The signed-in dashboard, wired to the real API:
 *   - greeting        ← GET /api/profile/  (name/email)
 *   - match cards     ← GET /api/matches/  (best fit first)
 *   - journey card    ← GET /api/tasks/    (per-phase progress)
 *   - next action     ← first pending task by due date
 * The savings banner and quick-actions grid remain static design elements.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import type { RootStackParamList } from "../navigation/types";

import { colors, fonts, radius } from "../theme";
import {
  BellIcon,
  ChevronRightIcon,
  UploadIcon,
  VisaIcon,
  PlaneIcon,
  HousingIcon,
  SparkleIcon,
  HomeIcon,
  CompassIcon,
  AppsIcon,
  ChatIcon,
  ProfileIcon,
} from "../components/icons";
import {
  getAiMatches,
  getMatches,
  getNotifications,
  getProfile,
  getTasks,
  type AiMatch,
  type Match,
  type Profile,
  type Task,
} from "../lib/api";

// Rotating visual identity for match cards (avatar + hero tint).
const CARD_COLORS = [
  { badge: colors.accent, hero: "#EAD9C0" },
  { badge: "#C7502F", hero: "#E4D2E8" },
  { badge: "#F49A1A", hero: "#E2DFC6" },
  { badge: "#1F8A5B", hero: "#D8E8DC" },
  { badge: "#2A6FDB", hero: "#D9E4F2" },
];

type QuickAction = { key: string; title: string; sub: string; bg: string; icon: React.ReactNode };

const QUICK_ACTIONS: QuickAction[] = [
  { key: "visa", title: "Visa", sub: "Residence permit", bg: "#FBEEE7", icon: <VisaIcon color="#F8593C" /> },
  { key: "flights", title: "Flights", sub: "To Helsinki", bg: "#E9F1FB", icon: <PlaneIcon color="#2A6FDB" /> },
  { key: "housing", title: "Housing", sub: "Student rooms", bg: "#E8F4EC", icon: <HousingIcon color="#1F8A5B" /> },
  { key: "advisor", title: "Advisor", sub: "AI + human", bg: "#F3ECFB", icon: <SparkleIcon color="#7B4FD6" /> },
];

// Tabs without a target yet (Apps, Chat) render disabled rather than dead.
const TABS = [
  { key: "home", label: "Home", Icon: HomeIcon, active: true, target: null },
  { key: "explore", label: "Explore", Icon: CompassIcon, active: false, target: "matches" },
  { key: "apps", label: "Apps", Icon: AppsIcon, active: false, target: "applications" },
  { key: "chat", label: "Chat", Icon: ChatIcon, active: false, target: null },
  { key: "profile", label: "Profile", Icon: ProfileIcon, active: false, target: "profile" },
] as const;

const euro = (v: string | null) =>
  v === null ? "—" : `€${Math.round(parseFloat(v)).toLocaleString("en-US")}`;

const shortDate = (iso: string | null) =>
  iso === null
    ? "—"
    : new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });


function UniCard({ match, index, onPress }: { match: Match; index: number; onPress: () => void }) {
  const c = CARD_COLORS[index % CARD_COLORS.length];
  const pct = Math.round(parseFloat(match.score));
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${match.university}, ${pct}% match. View programme details`}
      style={({ pressed }) => [styles.uniCard, pressed && { opacity: 0.85 }]}
    >
      <View style={[styles.uniHero, { backgroundColor: c.hero }]}>
        <Text style={styles.uniHeroText}>campus</Text>
        <View style={styles.matchBadge}>
          <Text style={styles.matchText}>{pct}% match</Text>
        </View>
        <View style={[styles.uniAvatar, { backgroundColor: c.badge }]}>
          <Text style={styles.uniAvatarText}>{match.university.charAt(0)}</Text>
        </View>
      </View>
      <View style={styles.uniBody}>
        <Text style={styles.uniName} numberOfLines={1}>{match.university}</Text>
        <Text style={styles.uniMeta} numberOfLines={1}>
          {match.city} · {match.program_name}
        </Text>
        <View style={styles.uniStats}>
          <View>
            <Text style={styles.statLabel}>Tuition/yr</Text>
            <Text style={styles.statValue}>{euro(match.tuition_fee_eur)}</Text>
          </View>
          <View>
            <Text style={styles.statLabel}>Deadline</Text>
            <Text style={styles.statValue}>{shortDate(match.application_deadline)}</Text>
          </View>
        </View>
        <View style={styles.viewBtn}>
          <Text style={styles.viewBtnText}>View program</Text>
        </View>
      </View>
    </Pressable>
  );
}

type Props = NativeStackScreenProps<RootStackParamList, "Home">;

export default function HomeScreen({ navigation }: Props) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [aiMatches, setAiMatches] = useState<AiMatch[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // One fetcher for first load and pull-to-refresh. On refresh a failure keeps
  // the stale data on screen instead of swapping it for an error box.
  const fetch = useCallback(async (mode: "initial" | "refresh") => {
    mode === "initial" ? setLoading(true) : setRefreshing(true);
    try {
      const [p, m, t] = await Promise.all([getProfile(), getMatches(), getTasks()]);
      setProfile(p);
      setMatches(m);
      setTasks(t);
      setError(null);
    } catch {
      if (mode === "initial") {
        setError("Couldn't load your data. Check your connection and the server.");
      }
    } finally {
      mode === "initial" ? setLoading(false) : setRefreshing(false);
    }
    // AI showcase is additive: never block or fail the dashboard for it.
    // Until the AI-layer endpoint ships this 404s and the box stays hidden.
    getAiMatches()
      .then((ai) => setAiMatches(ai.slice(0, 3)))
      .catch(() => {});
    // Bell badge — additive too, never blocks the dashboard.
    getNotifications()
      .then((page) => setUnreadCount(page.unread_count))
      .catch(() => {});
  }, []);

  const load = useCallback(() => fetch("initial"), [fetch]);
  const onRefresh = useCallback(() => fetch("refresh"), [fetch]);

  useEffect(() => {
    load();
  }, [load]);

  // Coming back from the inbox: the badge should reflect what was just read.
  useEffect(() => {
    return navigation.addListener("focus", () => {
      getNotifications()
        .then((page) => setUnreadCount(page.unread_count))
        .catch(() => {});
    });
  }, [navigation]);

  // ── Derived view data ──────────────────────────────────────────────────────
  // Greet by first name; email prefix only as a last resort for legacy rows.
  const displayName = profile?.first_name || profile?.email.split("@")[0] || "there";

  const today = new Date().toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  // Journey progress: tasks grouped by phase, current phase first.
  const phaseProgress = useMemo(() => {
    const byPhase = new Map<number, { done: number; total: number }>();
    for (const t of tasks) {
      const e = byPhase.get(t.phase) ?? { done: 0, total: 0 };
      e.total += 1;
      if (t.status === "completed") e.done += 1;
      byPhase.set(t.phase, e);
    }
    return [...byPhase.entries()]
      .sort(([a], [b]) => a - b)
      .filter(([, v]) => v.total > 0)
      .slice(0, 3)
      .map(([phase, v]) => ({ phase, ...v }));
  }, [tasks]);

  const nextTask = useMemo(() => {
    const pending = tasks.filter((t) => t.status === "pending" && t.due_date);
    pending.sort((a, b) => (a.due_date! < b.due_date! ? -1 : 1));
    return pending[0] ?? null;
  }, [tasks]);

  const matchContext = [
    profile?.field_of_study,
    profile?.budget_eur_per_year != null
      ? `€${(profile.budget_eur_per_year / 1000).toFixed(0)}k budget`
      : null,
  ]
    .filter(Boolean)
    .join(" & ");

  return (
    <View style={styles.root}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollBody}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />
        }
      >
        <SafeAreaView edges={["top"]}>
          <View style={styles.pad}>
            {/* top bar */}
            <View style={styles.topBar}>
              <View style={{ flex: 1, paddingRight: 10 }}>
                <Text style={styles.date}>{today}</Text>
                <Text style={styles.greeting} numberOfLines={1}>
                  Welcome aboard, {displayName}
                </Text>
                <Text style={styles.greetingQuote}>
                  You are exactly where you need to be
                </Text>
              </View>
              <View style={styles.topActions}>
                <Pressable
                  onPress={() => navigation.navigate("Notifications")}
                  accessibilityRole="button"
                  accessibilityLabel={
                    unreadCount > 0
                      ? `Notifications, ${unreadCount} unread`
                      : "Notifications"
                  }
                  style={styles.iconBtn}
                >
                  <BellIcon size={20} color="#4A3D31" />
                  {unreadCount > 0 && (
                    <View style={styles.notifBadge}>
                      <Text style={styles.notifBadgeText}>
                        {unreadCount > 9 ? "9+" : unreadCount}
                      </Text>
                    </View>
                  )}
                </Pressable>
                <Pressable
                  onPress={() => navigation.navigate("Profile")}
                  accessibilityRole="button"
                  accessibilityLabel="Open your profile"
                >
                  <LinearGradient colors={["#FFB43A", colors.accent]} style={styles.avatar}>
                    <Text style={styles.avatarText}>
                      {displayName.charAt(0).toUpperCase()}
                    </Text>
                  </LinearGradient>
                </Pressable>
              </View>
            </View>

            {loading && (
              <View style={styles.loadingBox}>
                <ActivityIndicator color={colors.accent} />
                <Text style={styles.loadingText}>Loading your journey…</Text>
              </View>
            )}

            {error && !loading && (
              <Pressable style={styles.errorBox} onPress={load}>
                <Text style={styles.errorText}>{error}</Text>
                <Text style={styles.errorRetry}>Tap to retry</Text>
              </Pressable>
            )}

            {/* AI picks — the free AI-layer showcase, above the system matches */}
            {!loading && !error && aiMatches.length > 0 && (
              <View style={styles.aiCard}>
                <View style={styles.aiHead}>
                  <View style={styles.aiBadge}>
                    <SparkleIcon size={16} color="#fff" />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.aiTitle}>AI picks for you</Text>
                    <Text style={styles.aiSub}>Hand-picked from your full profile</Text>
                  </View>
                </View>
                {aiMatches.map((m, i) => (
                  <Pressable
                    key={m.id}
                    onPress={() => navigation.navigate("MatchDetail", { match: m })}
                    accessibilityRole="button"
                    accessibilityLabel={`AI pick: ${m.university}. View details`}
                    style={({ pressed }) => [
                      styles.aiRow,
                      i === aiMatches.length - 1 && { borderBottomWidth: 0 },
                      pressed && { opacity: 0.7 },
                    ]}
                  >
                    <View style={styles.aiRank}>
                      <Text style={styles.aiRankText}>{i + 1}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.aiUni} numberOfLines={1}>{m.university}</Text>
                      <Text style={styles.aiReason} numberOfLines={2}>
                        {m.reason || `${m.program_name} · ${m.city}`}
                      </Text>
                    </View>
                    <ChevronRightIcon size={16} color="#B9A5E8" />
                  </Pressable>
                ))}
              </View>
            )}

            {/* recommended header */}
            {!loading && !error && (
              <>
                <View style={styles.sectionHead}>
                  <Text style={styles.sectionTitle}>Recommended for you</Text>
                  {matches.length > 0 && (
                    <Pressable
                      onPress={() => navigation.navigate("Matches", { matches })}
                      accessibilityRole="button"
                      accessibilityLabel={`See all ${matches.length} matches`}
                      hitSlop={10}
                    >
                      <Text style={styles.seeAll}>See all</Text>
                    </Pressable>
                  )}
                </View>
                <Text style={styles.sectionSub}>
                  {matches.length > 0
                    ? matchContext
                      ? `Based on your ${matchContext}`
                      : "Matched to your profile"
                    : "We're matching universities to your profile — check back in a minute."}
                </Text>
              </>
            )}
          </View>

          {/* uni cards horizontal scroll */}
          {!loading && !error && matches.length > 0 && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.uniRow}
            >
              {matches.slice(0, 10).map((m, i) => (
                <UniCard
                  key={m.id}
                  match={m}
                  index={i}
                  onPress={() => navigation.navigate("MatchDetail", { match: m })}
                />
              ))}
            </ScrollView>
          )}

          {!loading && !error && (
            <View style={styles.pad}>
              {/* journey progress (from the timeline engine) */}
              {phaseProgress.length > 0 && (
                <View style={styles.appsCard}>
                  <View style={styles.appsHead}>
                    <Text style={styles.appsTitle}>Your journey</Text>
                    <View style={styles.activePill}>
                      <Text style={styles.activePillText}>
                        {tasks.filter((t) => t.status === "pending").length} to do
                      </Text>
                    </View>
                  </View>
                  <View style={styles.appsList}>
                    {phaseProgress.map(({ phase, done, total }, i) => {
                      const c = CARD_COLORS[i % CARD_COLORS.length].badge;
                      return (
                        <View key={phase}>
                          <View style={styles.appRow}>
                            <View style={styles.appRowLeft}>
                              <View style={[styles.appBadge, { backgroundColor: c }]}>
                                <Text style={styles.appBadgeText}>{phase}</Text>
                              </View>
                              <Text style={styles.appLabel}>Phase {phase}</Text>
                            </View>
                            <Text style={styles.appSteps}>
                              {done} / {total} tasks
                            </Text>
                          </View>
                          <View style={styles.track}>
                            <View
                              style={[
                                styles.trackFill,
                                { width: `${total ? (done / total) * 100 : 0}%`, backgroundColor: c },
                              ]}
                            />
                          </View>
                        </View>
                      );
                    })}
                  </View>
                </View>
              )}

              {/* next action */}
              {nextTask && (
                <Pressable style={styles.nextCard}>
                  <View style={styles.nextIcon}>
                    <UploadIcon size={20} color="#fff" />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.nextCaption}>
                      NEXT UP · DUE {shortDate(nextTask.due_date).toUpperCase()}
                    </Text>
                    <Text style={styles.nextTitle} numberOfLines={2}>
                      {nextTask.title}
                    </Text>
                  </View>
                  <ChevronRightIcon size={20} color="#B4841A" />
                </Pressable>
              )}

              {/* quick actions */}
              <Text style={styles.sectionTitleLoose}>Get it all done</Text>
              <View style={styles.grid}>
                {QUICK_ACTIONS.map((q) => (
                  <Pressable key={q.key} style={styles.gridCell}>
                    <View style={[styles.gridIcon, { backgroundColor: q.bg }]}>{q.icon}</View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.gridTitle}>{q.title}</Text>
                      <Text style={styles.gridSub}>{q.sub}</Text>
                    </View>
                  </Pressable>
                ))}
              </View>
            </View>
          )}
        </SafeAreaView>
      </ScrollView>

      {/* bottom tab bar */}
      <SafeAreaView edges={["bottom"]} style={styles.tabBarWrap}>
        <View style={styles.tabBar}>
          {TABS.map(({ key, label, Icon, active, target }) => {
            const enabled = active || target !== null;
            const color = active ? colors.accent : "#A99B8D";
            const onPress = () => {
              if (target === "matches") navigation.navigate("Matches", { matches });
              if (target === "profile") navigation.navigate("Profile");
              if (target === "applications") navigation.navigate("Applications");
            };
            return (
              <Pressable
                key={key}
                onPress={target === null ? undefined : onPress}
                disabled={!enabled}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected: active, disabled: !enabled }}
                style={({ pressed }) => [
                  styles.tab,
                  !enabled && { opacity: 0.45 },
                  pressed && { opacity: 0.6 },
                ]}
              >
                <Icon size={24} color={color} />
                <Text
                  style={[
                    styles.tabLabel,
                    { color, fontFamily: active ? fonts.bodyBold : fonts.bodySemi },
                  ]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },
  scrollBody: { paddingBottom: 20 },
  pad: { paddingHorizontal: 20 },

  topBar: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", paddingTop: 4 },
  date: { fontFamily: fonts.bodySemi, fontSize: 12.5, color: colors.textFaintest, letterSpacing: 0.2 },
  greeting: { fontFamily: fonts.welcomeSerif, fontSize: 26, color: colors.ink, marginTop: 3 },
  // Calligraphic fonts carry huge ascenders/descenders — the roomy lineHeight
  // keeps Zapfino/Great Vibes from clipping.
  greetingQuote: {
    fontFamily: fonts.welcomeScript,
    fontSize: 13.5,
    lineHeight: 30,
    color: colors.textFaint,
    marginTop: 1,
  },
  topActions: { flexDirection: "row", alignItems: "center", gap: 10 },
  iconBtn: {
    width: 44,
    height: 44,
    borderRadius: 13,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  notifBadge: {
    position: "absolute",
    top: 5,
    right: 5,
    minWidth: 17,
    height: 17,
    borderRadius: 9,
    paddingHorizontal: 4,
    backgroundColor: colors.accent,
    borderWidth: 1.5,
    borderColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  notifBadgeText: { fontFamily: fonts.bodyBold, fontSize: 9.5, color: "#fff" },
  avatar: { width: 44, height: 44, borderRadius: 13, alignItems: "center", justifyContent: "center" },
  avatarText: { fontFamily: fonts.display, fontSize: 16, color: "#fff" },

  loadingBox: { alignItems: "center", gap: 10, paddingVertical: 60 },
  loadingText: { fontFamily: fonts.bodySemi, fontSize: 13.5, color: colors.textFaint },
  errorBox: {
    marginTop: 24,
    backgroundColor: "#FCEBE7",
    borderWidth: 1,
    borderColor: "#F3C4B8",
    borderRadius: radius["2xl"],
    padding: 18,
    alignItems: "center",
    gap: 4,
  },
  errorText: { fontFamily: fonts.bodySemi, fontSize: 13.5, color: "#B3402A", textAlign: "center" },
  errorRetry: { fontFamily: fonts.bodyBold, fontSize: 13, color: colors.accent },

  aiCard: {
    marginTop: 24,
    backgroundColor: "#F6F1FC",
    borderWidth: 1,
    borderColor: "#E3D5F5",
    borderRadius: radius["2xl"],
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 4,
  },
  aiHead: { flexDirection: "row", alignItems: "center", gap: 11, paddingBottom: 6 },
  aiBadge: {
    width: 34,
    height: 34,
    borderRadius: 11,
    backgroundColor: "#7B4FD6",
    alignItems: "center",
    justifyContent: "center",
  },
  aiTitle: { fontFamily: fonts.display, fontSize: 15.5, color: colors.ink },
  aiSub: { fontFamily: fonts.bodyRegular, fontSize: 11.5, color: "#8A76B0", marginTop: 1 },
  aiRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#E3D5F5",
  },
  aiRank: {
    width: 26,
    height: 26,
    borderRadius: 9,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#E3D5F5",
    alignItems: "center",
    justifyContent: "center",
  },
  aiRankText: { fontFamily: fonts.display, fontSize: 12.5, color: "#7B4FD6" },
  aiUni: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.ink },
  aiReason: { fontFamily: fonts.bodyRegular, fontSize: 11.5, color: colors.textFaint, marginTop: 1, lineHeight: 15 },

  sectionHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 26 },
  sectionTitle: { fontFamily: fonts.display, fontSize: 18, letterSpacing: -0.3, color: colors.ink },
  sectionTitleLoose: { fontFamily: fonts.display, fontSize: 18, letterSpacing: -0.3, color: colors.ink, marginTop: 26 },
  seeAll: { fontFamily: fonts.bodySemi, fontSize: 13, color: colors.accent },
  sectionSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 2 },

  uniRow: { gap: 14, paddingHorizontal: 20, paddingTop: 14, paddingBottom: 6 },
  uniCard: {
    width: 236,
    backgroundColor: "#fff",
    borderRadius: radius["3xl"],
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    shadowColor: "#5A3719",
    shadowOpacity: 0.28,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 14 },
    elevation: 3,
  },
  uniHero: { height: 116, alignItems: "center", justifyContent: "center" },
  uniHeroText: { fontFamily: fonts.bodySemi, fontSize: 9.5, letterSpacing: 0.8, color: "#AD977E" },
  matchBadge: {
    position: "absolute",
    top: 10,
    right: 10,
    backgroundColor: "rgba(255,255,255,0.92)",
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: radius.pill,
  },
  matchText: { fontFamily: fonts.display, fontSize: 12, color: colors.success },
  uniAvatar: {
    position: "absolute",
    bottom: -18,
    left: 14,
    width: 42,
    height: 42,
    borderRadius: 12,
    borderWidth: 3,
    borderColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  uniAvatarText: { fontFamily: fonts.display, fontSize: 18, color: "#fff" },
  uniBody: { paddingTop: 26, paddingHorizontal: 15, paddingBottom: 16 },
  uniName: { fontFamily: fonts.display, fontSize: 15.5, color: colors.ink },
  uniMeta: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textFaint, marginTop: 2 },
  uniStats: { flexDirection: "row", gap: 14, marginTop: 13 },
  statLabel: { fontFamily: fonts.bodySemi, fontSize: 10.5, color: colors.textFaintest },
  statValue: { fontFamily: fonts.display, fontSize: 14, color: colors.ink },
  viewBtn: {
    height: 40,
    marginTop: 14,
    borderRadius: radius.md,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  viewBtnText: { fontFamily: fonts.displaySemi, fontSize: 13.5, color: colors.accent },

  appsCard: {
    marginTop: 22,
    backgroundColor: "#fff",
    borderRadius: radius["2xl"],
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  appsHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  appsTitle: { fontFamily: fonts.display, fontSize: 16, color: colors.ink },
  activePill: { backgroundColor: colors.accent, paddingVertical: 3, paddingHorizontal: 9, borderRadius: radius.pill },
  activePillText: { fontFamily: fonts.bodyBold, fontSize: 12, color: "#fff" },
  appsList: { marginTop: 16, gap: 16 },
  appRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  appRowLeft: { flexDirection: "row", alignItems: "center", gap: 9 },
  appBadge: { width: 26, height: 26, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  appBadgeText: { fontFamily: fonts.display, fontSize: 12, color: "#fff" },
  appLabel: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.ink },
  appSteps: { fontFamily: fonts.bodySemi, fontSize: 12, color: colors.textFaint },
  track: { height: 7, borderRadius: radius.pill, backgroundColor: "#F1E7DA", marginTop: 9, overflow: "hidden" },
  trackFill: { height: "100%", borderRadius: radius.pill },

  nextCard: {
    marginTop: 14,
    backgroundColor: colors.warningBg,
    borderWidth: 1,
    borderColor: colors.warningBorder,
    borderRadius: radius["2xl"],
    paddingVertical: 16,
    paddingHorizontal: 18,
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
  },
  nextIcon: { width: 40, height: 40, borderRadius: 12, backgroundColor: "#F49A1A", alignItems: "center", justifyContent: "center" },
  nextCaption: { fontFamily: fonts.bodyBold, fontSize: 11, color: colors.warningInkSoft, letterSpacing: 0.4 },
  nextTitle: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.warningInk, marginTop: 2 },

  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 14 },
  gridCell: {
    width: "48%",
    flexGrow: 1,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.xl,
    padding: 15,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  gridIcon: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  gridTitle: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.ink },
  gridSub: { fontFamily: fonts.bodyRegular, fontSize: 11, color: colors.textFaint },

  tabBarWrap: {
    backgroundColor: "rgba(251,246,239,0.96)",
    borderTopWidth: 1,
    borderTopColor: "#EBDDCB",
  },
  tabBar: { flexDirection: "row", justifyContent: "space-around", alignItems: "flex-start", paddingTop: 11, paddingHorizontal: 8 },
  tab: { alignItems: "center", gap: 4, minWidth: 56, paddingVertical: 2 },
  tabLabel: { fontSize: 10.5 },
});
