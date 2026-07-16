/**
 * 03 — HOME · UNIVERSITY MATCHES
 * The signed-in dashboard, wired to the real API:
 *   - greeting        ← GET /api/profile/  (name/email)
 *   - match cards     ← GET /api/matches/  (best fit first)
 *   - journey card    ← GET /api/tasks/    (per-phase progress)
 *   - next action     ← first pending task by due date
 * Visual language: travel documents — match cards read as mini boarding
 * passes (route PAK → destination city), the AI picks ride in a dark
 * "first-class" card, progress is a flight plan. The tab dock is global
 * (navigation/MainTabs), not drawn here.
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

import type { TabScreenProps } from "../navigation/types";
import { colors, fonts, radius, shadow, spacing } from "../theme";
import {
  BellIcon,
  ChevronRightIcon,
  UploadIcon,
  VisaIcon,
  PlaneIcon,
  HousingIcon,
  SparkleIcon,
} from "../components/icons";
import { CodeBadge, RouteLine, Stamp, TicketDivider, TicketField, cityCode, uniCode } from "../components/travel";
import { FadeInUp, PressableScale, ProgressBar } from "../components/motion";

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

type QuickAction = { key: string; title: string; sub: string; icon: React.ReactNode };

// Static service tiles — honest about not being live yet (SOON tag).
const QUICK_ACTIONS: QuickAction[] = [
  { key: "visa", title: "Visa", sub: "Residence permit", icon: <VisaIcon color={colors.ink} /> },
  { key: "flights", title: "Flights", sub: "To Helsinki", icon: <PlaneIcon color={colors.ink} /> },
  { key: "housing", title: "Housing", sub: "Student rooms", icon: <HousingIcon color={colors.ink} /> },
  { key: "advisor", title: "Advisor", sub: "AI + human", icon: <SparkleIcon color={colors.ink} /> },
];

const euro = (v: string | null) =>
  v === null ? "—" : `€${Math.round(parseFloat(v)).toLocaleString("en-US")}`;

const shortDate = (iso: string | null) =>
  iso === null
    ? "—"
    : new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

const deadlineSoon = (iso: string | null) =>
  iso !== null && new Date(iso).getTime() - Date.now() < 30 * 86400000;

/** Mini boarding pass: code + match stamp, route to the destination city. */
function UniCard({ match, index, onPress }: { match: Match; index: number; onPress: () => void }) {
  const pct = Math.round(parseFloat(match.score));
  return (
    <FadeInUp delay={120 + index * 70}>
      <PressableScale
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={`${match.university}, ${pct}% match. View programme details`}
        style={styles.uniCard}
      >
        <View style={styles.uniTop}>
          <CodeBadge code={uniCode(match.university)} size={42} />
          <Stamp label={`${pct}% match`} ink={colors.success} tilt={2} />
        </View>
        <Text style={styles.uniName} numberOfLines={1}>{match.university}</Text>
        <Text style={styles.uniMeta} numberOfLines={1}>
          {match.program_name} · {match.city}
        </Text>
        <View style={styles.uniRoute}>
          <RouteLine from="PAK" to={cityCode(match.city)} progress={pct / 100} />
        </View>
        <TicketDivider inset={16} />
        <View style={styles.uniStats}>
          <TicketField label="Tuition / yr" value={euro(match.tuition_fee_eur)} />
          <TicketField
            label="Deadline"
            value={shortDate(match.application_deadline)}
            align="right"
            valueColor={deadlineSoon(match.application_deadline) ? colors.accent : colors.ink}
          />
        </View>
      </PressableScale>
    </FadeInUp>
  );
}

type Props = TabScreenProps<"Home">;

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

  const today = new Date()
    .toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short" })
    .toUpperCase();

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
            <FadeInUp>
              <View style={styles.topBar}>
                <View style={{ flex: 1, paddingRight: 10 }}>
                  <Text style={styles.date}>{today} · PAK → FIN</Text>
                  <Text style={styles.greeting} numberOfLines={1}>
                    Welcome aboard, {displayName}
                  </Text>
                  <Text style={styles.greetingQuote}>
                    You are exactly where you need to be
                  </Text>
                </View>
                <View style={styles.topActions}>
                  <PressableScale
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
                  </PressableScale>
                  <PressableScale
                    onPress={() => navigation.navigate("Profile")}
                    accessibilityRole="button"
                    accessibilityLabel="Open your profile"
                  >
                    <LinearGradient colors={["#FFB43A", colors.accent]} style={styles.avatar}>
                      <Text style={styles.avatarText}>
                        {displayName.charAt(0).toUpperCase()}
                      </Text>
                    </LinearGradient>
                  </PressableScale>
                </View>
              </View>
            </FadeInUp>

            {loading && (
              <View style={styles.loadingBox}>
                <ActivityIndicator color={colors.accent} />
                <Text style={styles.loadingText}>PREPARING YOUR JOURNEY…</Text>
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
              <FadeInUp delay={60}>
                <View style={styles.aiCard}>
                  <View style={styles.aiHead}>
                    <View style={styles.aiBadge}>
                      <SparkleIcon size={16} color={colors.ink} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.aiTitle}>AI picks for you</Text>
                      <Text style={styles.aiSub}>Hand-picked from your full profile</Text>
                    </View>
                    <Text style={styles.aiTag}>FIRST CLASS</Text>
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
                      <Text style={styles.aiRank}>{String(i + 1).padStart(2, "0")}</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.aiUni} numberOfLines={1}>{m.university}</Text>
                        <Text style={styles.aiReason} numberOfLines={2}>
                          {m.reason || `${m.program_name} · ${m.city}`}
                        </Text>
                      </View>
                      <ChevronRightIcon size={16} color="#C9B490" />
                    </Pressable>
                  ))}
                </View>
              </FadeInUp>
            )}

            {/* recommended header */}
            {!loading && !error && (
              <FadeInUp delay={100}>
                <Text style={styles.overline}>DEPARTURES — FINLAND</Text>
                <View style={styles.sectionHead}>
                  <Text style={styles.sectionTitle}>Recommended for you</Text>
                  {matches.length > 0 && (
                    <Pressable
                      onPress={() => navigation.navigate("Explore")}
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
              </FadeInUp>
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
                <FadeInUp delay={180}>
                  <View style={styles.appsCard}>
                    <View style={styles.appsHead}>
                      <View>
                        <Text style={styles.overlineTight}>FLIGHT PLAN</Text>
                        <Text style={styles.appsTitle}>Your journey</Text>
                      </View>
                      <View style={styles.activePill}>
                        <Text style={styles.activePillText}>
                          {tasks.filter((t) => t.status === "pending").length} TO DO
                        </Text>
                      </View>
                    </View>
                    <View style={styles.appsList}>
                      {phaseProgress.map(({ phase, done, total }) => (
                        <View key={phase}>
                          <View style={styles.appRow}>
                            <View style={styles.appRowLeft}>
                              <Text style={styles.appLeg}>LEG {String(phase).padStart(2, "0")}</Text>
                              <Text style={styles.appLabel}>Phase {phase}</Text>
                            </View>
                            <Text style={styles.appSteps}>
                              {done}/{total} TASKS
                            </Text>
                          </View>
                          <ProgressBar
                            progress={total ? done / total : 0}
                            tint={colors.accent}
                            style={{ marginTop: 9 }}
                          />
                        </View>
                      ))}
                    </View>
                  </View>
                </FadeInUp>
              )}

              {/* next action */}
              {nextTask && (
                <FadeInUp delay={240}>
                  <PressableScale style={styles.nextCard}>
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
                  </PressableScale>
                </FadeInUp>
              )}

              {/* services */}
              <FadeInUp delay={300}>
                <Text style={styles.overlineLoose}>SERVICES</Text>
                <Text style={styles.sectionTitleTight}>Get it all done</Text>
                <View style={styles.grid}>
                  {QUICK_ACTIONS.map((q) => (
                    <View key={q.key} style={styles.gridCell}>
                      <View style={styles.gridIcon}>{q.icon}</View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.gridTitle}>{q.title}</Text>
                        <Text style={styles.gridSub}>{q.sub}</Text>
                      </View>
                      <Text style={styles.soonTag}>SOON</Text>
                    </View>
                  ))}
                </View>
              </FadeInUp>
            </View>
          )}
        </SafeAreaView>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },
  scrollBody: { paddingBottom: spacing.tabClearance },
  pad: { paddingHorizontal: 20 },

  topBar: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", paddingTop: 4 },
  date: { fontFamily: fonts.mono, fontSize: 10.5, color: colors.textFaintest, letterSpacing: 1.2 },
  greeting: { fontFamily: fonts.welcomeSerif, fontSize: 26, color: colors.ink, marginTop: 4 },
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

  loadingBox: { alignItems: "center", gap: 12, paddingVertical: 60 },
  loadingText: { fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: 1.4, color: colors.textFaint },
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

  // The dark "first-class" card — the one non-cream surface on the screen.
  aiCard: {
    marginTop: 24,
    backgroundColor: colors.ink,
    borderRadius: radius["2xl"],
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 4,
    ...shadow.raised,
  },
  aiHead: { flexDirection: "row", alignItems: "center", gap: 11, paddingBottom: 6 },
  aiBadge: {
    width: 34,
    height: 34,
    borderRadius: 11,
    backgroundColor: "#F4C664",
    alignItems: "center",
    justifyContent: "center",
  },
  aiTitle: { fontFamily: fonts.display, fontSize: 15.5, color: "#FBF6EF" },
  aiSub: { fontFamily: fonts.bodyRegular, fontSize: 11.5, color: "#B9A88F", marginTop: 1 },
  aiTag: { fontFamily: fonts.monoBold, fontSize: 8.5, letterSpacing: 1.4, color: "#F4C664" },
  aiRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#4A3D31",
  },
  aiRank: { fontFamily: fonts.monoBold, fontSize: 13, color: "#F4C664" },
  aiUni: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: "#FBF6EF" },
  aiReason: { fontFamily: fonts.bodyRegular, fontSize: 11.5, color: "#B9A88F", marginTop: 1, lineHeight: 15 },

  overline: {
    fontFamily: fonts.mono,
    fontSize: 9.5,
    letterSpacing: 1.6,
    color: colors.textFaintest,
    marginTop: 28,
  },
  overlineTight: { fontFamily: fonts.mono, fontSize: 9, letterSpacing: 1.6, color: colors.textFaintest },
  overlineLoose: {
    fontFamily: fonts.mono,
    fontSize: 9.5,
    letterSpacing: 1.6,
    color: colors.textFaintest,
    marginTop: 30,
  },
  sectionHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 3 },
  sectionTitle: { fontFamily: fonts.display, fontSize: 18, letterSpacing: -0.3, color: colors.ink },
  sectionTitleTight: { fontFamily: fonts.display, fontSize: 18, letterSpacing: -0.3, color: colors.ink, marginTop: 3 },
  seeAll: { fontFamily: fonts.bodySemi, fontSize: 13, color: colors.accent },
  sectionSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 2 },

  uniRow: { gap: 14, paddingHorizontal: 20, paddingTop: 14, paddingBottom: 10 },
  uniCard: {
    width: 250,
    backgroundColor: "#fff",
    borderRadius: radius["3xl"],
    borderWidth: 1,
    borderColor: colors.borderSoft,
    paddingHorizontal: 16,
    paddingTop: 15,
    paddingBottom: 14,
    overflow: "hidden",
    ...shadow.card,
  },
  uniTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  uniName: { fontFamily: fonts.display, fontSize: 15.5, color: colors.ink, marginTop: 12 },
  uniMeta: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textFaint, marginTop: 2 },
  uniRoute: { marginTop: 13 },
  uniStats: { flexDirection: "row", justifyContent: "space-between", marginTop: 2 },

  appsCard: {
    marginTop: 22,
    backgroundColor: "#fff",
    borderRadius: radius["2xl"],
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  appsHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  appsTitle: { fontFamily: fonts.display, fontSize: 16, color: colors.ink, marginTop: 2 },
  activePill: {
    borderWidth: 1.4,
    borderColor: colors.accent,
    paddingVertical: 3,
    paddingHorizontal: 9,
    borderRadius: 6,
    transform: [{ rotate: "2deg" }],
  },
  activePillText: { fontFamily: fonts.monoBold, fontSize: 10, letterSpacing: 1, color: colors.accent },
  appsList: { marginTop: 16, gap: 16 },
  appRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  appRowLeft: { flexDirection: "row", alignItems: "baseline", gap: 9 },
  appLeg: { fontFamily: fonts.monoBold, fontSize: 10, letterSpacing: 1, color: colors.accent },
  appLabel: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.ink },
  appSteps: { fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: 0.6, color: colors.textFaint },

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
  nextCaption: { fontFamily: fonts.monoBold, fontSize: 9.5, color: colors.warningInkSoft, letterSpacing: 1 },
  nextTitle: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.warningInk, marginTop: 3 },

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
  gridIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: "#F6EFE6",
    alignItems: "center",
    justifyContent: "center",
  },
  gridTitle: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.ink },
  gridSub: { fontFamily: fonts.bodyRegular, fontSize: 11, color: colors.textFaint },
  soonTag: { fontFamily: fonts.mono, fontSize: 8, letterSpacing: 1, color: colors.textFaintest },
});
