/**
 * 03 — HOME · UNIVERSITY MATCHES
 * The signed-in dashboard: greeting, savings banner, horizontally-scrolling
 * university match cards, application progress, the next-action nudge, a
 * quick-actions grid, and the bottom tab bar. Data is mock (from the mockup);
 * swap the arrays for `/api/matches` + `/api/tasks` when wiring the backend.
 */
import React from "react";
import { View, Text, StyleSheet, ScrollView, Pressable } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";

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

type Uni = {
  key: string;
  name: string;
  meta: string;
  match: string;
  tuition: string;
  intake: string;
  badge: string;
  badgeColor: string;
  hero: string;
};

const UNIVERSITIES: Uni[] = [
  { key: "aalto", name: "Aalto University", meta: "Espoo · MSc Computer Science", match: "94% match", tuition: "€15,000", intake: "Aug 2026", badge: "A", badgeColor: colors.accent, hero: "#EAD9C0" },
  { key: "helsinki", name: "Univ. of Helsinki", meta: "Helsinki · MSc Data Science", match: "91% match", tuition: "€18,000", intake: "Aug 2026", badge: "H", badgeColor: "#C7502F", hero: "#E4D2E8" },
  { key: "lut", name: "LUT University", meta: "Lappeenranta · MSc Software", match: "88% match", tuition: "€13,500", intake: "Aug 2026", badge: "L", badgeColor: "#F49A1A", hero: "#E2DFC6" },
];

type AppProgress = { key: string; badge: string; badgeColor: string; label: string; steps: string; pct: number };

const APPLICATIONS: AppProgress[] = [
  { key: "aalto", badge: "A", badgeColor: colors.accent, label: "Aalto · MSc CS", steps: "3 / 5 steps", pct: 0.6 },
  { key: "helsinki", badge: "H", badgeColor: "#C7502F", label: "Helsinki · MSc Data Sci", steps: "1 / 5 steps", pct: 0.2 },
];

type QuickAction = { key: string; title: string; sub: string; bg: string; icon: React.ReactNode };

const QUICK_ACTIONS: QuickAction[] = [
  { key: "visa", title: "Visa", sub: "Residence permit", bg: "#FBEEE7", icon: <VisaIcon color="#F8593C" /> },
  { key: "flights", title: "Flights", sub: "To Helsinki", bg: "#E9F1FB", icon: <PlaneIcon color="#2A6FDB" /> },
  { key: "housing", title: "Housing", sub: "Student rooms", bg: "#E8F4EC", icon: <HousingIcon color="#1F8A5B" /> },
  { key: "advisor", title: "Advisor", sub: "AI + human", bg: "#F3ECFB", icon: <SparkleIcon color="#7B4FD6" /> },
];

const TABS = [
  { key: "home", label: "Home", Icon: HomeIcon, active: true },
  { key: "explore", label: "Explore", Icon: CompassIcon, active: false },
  { key: "apps", label: "Apps", Icon: AppsIcon, active: false },
  { key: "chat", label: "Chat", Icon: ChatIcon, active: false },
  { key: "profile", label: "Profile", Icon: ProfileIcon, active: false },
];

function UniCard({ uni }: { uni: Uni }) {
  return (
    <View style={styles.uniCard}>
      <View style={[styles.uniHero, { backgroundColor: uni.hero }]}>
        <Text style={styles.uniHeroText}>campus</Text>
        <View style={styles.matchBadge}>
          <Text style={styles.matchText}>{uni.match}</Text>
        </View>
        <View style={[styles.uniAvatar, { backgroundColor: uni.badgeColor }]}>
          <Text style={styles.uniAvatarText}>{uni.badge}</Text>
        </View>
      </View>
      <View style={styles.uniBody}>
        <Text style={styles.uniName}>{uni.name}</Text>
        <Text style={styles.uniMeta}>{uni.meta}</Text>
        <View style={styles.uniStats}>
          <View>
            <Text style={styles.statLabel}>Tuition/yr</Text>
            <Text style={styles.statValue}>{uni.tuition}</Text>
          </View>
          <View>
            <Text style={styles.statLabel}>Intake</Text>
            <Text style={styles.statValue}>{uni.intake}</Text>
          </View>
        </View>
        <Pressable style={styles.viewBtn}>
          <Text style={styles.viewBtnText}>View program</Text>
        </Pressable>
      </View>
    </View>
  );
}

export default function HomeScreen() {
  return (
    <View style={styles.root}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollBody}>
        <SafeAreaView edges={["top"]}>
          <View style={styles.pad}>
            {/* top bar */}
            <View style={styles.topBar}>
              <View>
                <Text style={styles.date}>Monday, 8 July</Text>
                <Text style={styles.greeting}>Good morning, Aarav</Text>
              </View>
              <View style={styles.topActions}>
                <Pressable style={styles.iconBtn}>
                  <BellIcon size={20} color="#4A3D31" />
                  <View style={styles.notifDot} />
                </Pressable>
                <LinearGradient colors={["#FFB43A", colors.accent]} style={styles.avatar}>
                  <Text style={styles.avatarText}>A</Text>
                </LinearGradient>
              </View>
            </View>

            {/* savings banner */}
            <LinearGradient colors={["#2A2119", "#3A2C20"]} style={styles.savingsBanner}>
              <View style={{ flex: 1 }}>
                <Text style={styles.savingsCaption}>You've saved so far</Text>
                <Text style={styles.savingsAmount}>€4,320</Text>
                <Text style={styles.savingsNote}>
                  that's <Text style={styles.savingsAccent}>80% less</Text> than a €5,400 agent
                </Text>
              </View>
              <View style={styles.savingsRing}>
                <Text style={styles.savingsRingText}>80%</Text>
              </View>
            </LinearGradient>

            {/* recommended header */}
            <View style={styles.sectionHead}>
              <Text style={styles.sectionTitle}>Recommended for you</Text>
              <Text style={styles.seeAll}>See all</Text>
            </View>
            <Text style={styles.sectionSub}>Based on your CS background & €18k budget</Text>
          </View>

          {/* uni cards horizontal scroll */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.uniRow}
          >
            {UNIVERSITIES.map((u) => (
              <UniCard key={u.key} uni={u} />
            ))}
          </ScrollView>

          <View style={styles.pad}>
            {/* applications progress */}
            <View style={styles.appsCard}>
              <View style={styles.appsHead}>
                <Text style={styles.appsTitle}>Your applications</Text>
                <View style={styles.activePill}>
                  <Text style={styles.activePillText}>2 active</Text>
                </View>
              </View>
              <View style={styles.appsList}>
                {APPLICATIONS.map((a) => (
                  <View key={a.key}>
                    <View style={styles.appRow}>
                      <View style={styles.appRowLeft}>
                        <View style={[styles.appBadge, { backgroundColor: a.badgeColor }]}>
                          <Text style={styles.appBadgeText}>{a.badge}</Text>
                        </View>
                        <Text style={styles.appLabel}>{a.label}</Text>
                      </View>
                      <Text style={styles.appSteps}>{a.steps}</Text>
                    </View>
                    <View style={styles.track}>
                      <View
                        style={[styles.trackFill, { width: `${a.pct * 100}%`, backgroundColor: a.badgeColor }]}
                      />
                    </View>
                  </View>
                ))}
              </View>
            </View>

            {/* next action */}
            <Pressable style={styles.nextCard}>
              <View style={styles.nextIcon}>
                <UploadIcon size={20} color="#fff" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.nextCaption}>NEXT UP · DUE JUL 20</Text>
                <Text style={styles.nextTitle}>Upload your bachelor's transcript</Text>
              </View>
              <ChevronRightIcon size={20} color="#B4841A" />
            </Pressable>

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
        </SafeAreaView>
      </ScrollView>

      {/* bottom tab bar */}
      <SafeAreaView edges={["bottom"]} style={styles.tabBarWrap}>
        <View style={styles.tabBar}>
          {TABS.map(({ key, label, Icon, active }) => {
            const color = active ? colors.accent : "#A99B8D";
            return (
              <Pressable key={key} style={styles.tab}>
                <Icon size={24} color={color} />
                <Text style={[styles.tabLabel, { color, fontFamily: active ? fonts.bodyBold : fonts.bodySemi }]}>
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

  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingTop: 4 },
  date: { fontFamily: fonts.bodySemi, fontSize: 12.5, color: colors.textFaintest, letterSpacing: 0.2 },
  greeting: { fontFamily: fonts.display, fontSize: 24, letterSpacing: -0.6, color: colors.ink, marginTop: 2 },
  topActions: { flexDirection: "row", alignItems: "center", gap: 10 },
  iconBtn: {
    width: 42,
    height: 42,
    borderRadius: 13,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  notifDot: {
    position: "absolute",
    top: 8,
    right: 9,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.accent,
    borderWidth: 1.5,
    borderColor: "#fff",
  },
  avatar: { width: 42, height: 42, borderRadius: 13, alignItems: "center", justifyContent: "center" },
  avatarText: { fontFamily: fonts.display, fontSize: 16, color: "#fff" },

  savingsBanner: {
    marginTop: 18,
    borderRadius: radius["2xl"],
    paddingVertical: 16,
    paddingHorizontal: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  savingsCaption: { fontFamily: fonts.bodySemi, fontSize: 12.5, color: "#D8C4AE" },
  savingsAmount: { fontFamily: fonts.display, fontSize: 26, color: "#fff", marginTop: 3, lineHeight: 26 },
  savingsNote: { fontFamily: fonts.bodyRegular, fontSize: 12, color: "#B7A48E", marginTop: 5 },
  savingsAccent: { color: colors.accent, fontFamily: fonts.bodyBold },
  savingsRing: {
    width: 62,
    height: 62,
    borderRadius: 31,
    borderWidth: 5,
    borderColor: "rgba(248,89,60,0.25)",
    alignItems: "center",
    justifyContent: "center",
  },
  savingsRingText: { fontFamily: fonts.display, fontSize: 15, color: "#fff" },

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
  tab: { alignItems: "center", gap: 4 },
  tabLabel: { fontSize: 10.5 },
});
