/**
 * 06 — PROFILE · THE TRAVELLER ID PAGE
 * The passport identity card up top, then native settings rows — each
 * category (Personal info, Academic background, English test, Budget &
 * timeline) pushes its own ProfileSection screen for editing. This tab only
 * reads; it re-fetches on focus so the row summaries are fresh the moment a
 * section screen saves and pops back. Sign out lives at the bottom, visually
 * separated, behind a confirm.
 */
import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { useFocusEffect } from "@react-navigation/native";

import { colors, fonts, radius, shadow, spacing } from "../theme";
import {
  CertificateIcon,
  ChevronRightIcon,
  GradCapIcon,
  IdCardIcon,
  LogOutIcon,
  WalletIcon,
  type IconProps,
} from "../components/icons";
import { TicketDivider, TicketField } from "../components/travel";
import { FadeInUp, PressableScale } from "../components/motion";

import { getProfile, type Profile } from "../lib/api";
import { labelOf } from "../lib/profileForm";
import {
  EDUCATION_LEVELS,
  FIELDS,
  INTAKES,
  LANGUAGE_TESTS,
  TEST_STATUSES,
} from "../lib/profileOptions";
import { useAuth } from "../context/AuthContext";
import type { ProfileSectionKey, TabScreenProps } from "../navigation/types";

type Props = TabScreenProps<"Profile">;

/** Passport MRZ-style line: pure theatre, but it sells the ID page. */
function mrzLine(first: string, last: string): string {
  const clean = (s: string) => s.toUpperCase().replace(/[^A-Z]/g, "");
  return `P<PAK${clean(last) || "WAYFARER"}<<${clean(first) || "STUDENT"}`
    .padEnd(30, "<")
    .slice(0, 30);
}

/** One settings row: icon tile, title, live summary, chevron → pushes the
 *  category's own screen. */
function SectionRow({
  icon: Icon,
  title,
  summary,
  onPress,
}: {
  icon: (p: IconProps) => React.JSX.Element;
  title: string;
  summary: string;
  onPress: () => void;
}) {
  return (
    <PressableScale
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${summary}`}
      style={styles.row}
    >
      <View style={styles.rowIcon}>
        <Icon size={20} color={colors.accent} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.rowTitle}>{title}</Text>
        <Text style={styles.rowSummary} numberOfLines={1}>
          {summary}
        </Text>
      </View>
      <ChevronRightIcon size={17} color={colors.textFaintest} />
    </PressableScale>
  );
}

export default function ProfileScreen({ navigation }: Props) {
  const { signOut } = useAuth();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(() => {
    setLoadError(false);
    getProfile()
      .then(setProfile)
      .catch(() => setLoadError(true))
      .finally(() => setLoading(false));
  }, []);

  // Re-read whenever the tab regains focus — a section screen just saved.
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const open = (section: ProfileSectionKey) =>
    navigation.navigate("ProfileSection", { section });

  const onSignOut = () => {
    // RN-web's Alert is a no-op — confirm() is the web equivalent.
    if (Platform.OS === "web") {
      // eslint-disable-next-line no-alert
      if (window.confirm("Sign out?\n\nYou can sign back in with your email and password anytime.")) {
        signOut();
      }
      return;
    }
    Alert.alert("Sign out?", "You can sign back in with your email and password anytime.", [
      { text: "Cancel", style: "cancel" },
      { text: "Sign out", style: "destructive", onPress: signOut },
    ]);
  };

  const displayName =
    profile && (profile.first_name || profile.last_name)
      ? `${profile.first_name} ${profile.last_name}`.trim()
      : profile?.email.split("@")[0] ?? "";

  return (
    <SafeAreaView edges={["top"]} style={styles.root}>
      <FadeInUp>
        <View style={styles.topBar}>
          <Text style={styles.overline}>TRAVELLER ID</Text>
          <Text style={styles.title}>Your profile</Text>
        </View>
      </FadeInUp>

      {loading && (
        <View style={styles.loadingBox}>
          <ActivityIndicator color={colors.accent} />
        </View>
      )}

      {loadError && !loading && (
        <Pressable
          onPress={load}
          accessibilityRole="button"
          style={({ pressed }) => [styles.errorBox, pressed && { opacity: 0.7 }]}
        >
          <Text style={styles.errorText}>Couldn't load your profile.</Text>
          <Text style={styles.errorRetry}>Tap to retry</Text>
        </Pressable>
      )}

      {!loading && !loadError && profile && (
        <ScrollView contentContainerStyle={styles.body} showsVerticalScrollIndicator={false}>
          {/* passport ID page — email is the account key, not editable */}
          <FadeInUp delay={60}>
            <View style={styles.identityCard}>
              <View style={styles.passportHead}>
                <Text style={styles.passportHeadText}>WAYFARA · TRAVELLER ID</Text>
                <View style={styles.tierChip}>
                  <Text style={styles.tierChipText}>{profile.tier.toUpperCase()}</Text>
                </View>
              </View>
              <View style={styles.identityRow}>
                <LinearGradient colors={["#FFB43A", colors.accent]} style={styles.avatar}>
                  <Text style={styles.avatarText}>
                    {(displayName || "W").charAt(0).toUpperCase()}
                  </Text>
                </LinearGradient>
                <View style={{ flex: 1 }}>
                  <Text style={styles.identityName} numberOfLines={1}>
                    {displayName || "Add your name"}
                  </Text>
                  <Text style={styles.identityEmail} numberOfLines={1}>{profile.email}</Text>
                </View>
              </View>
              <View style={styles.identityFields}>
                <TicketField label="Nationality" value={profile.nationality || "—"} />
                <TicketField label="Home city" value={profile.home_city || "—"} />
                <TicketField label="Destination" value="FINLAND" align="right" valueColor={colors.accent} />
              </View>
              <TicketDivider inset={16} />
              <Text style={styles.mrz} numberOfLines={1}>
                {mrzLine(profile.first_name, profile.last_name)}
              </Text>
            </View>
          </FadeInUp>

          {/* categories — each pushes its own editing screen */}
          <FadeInUp delay={120}>
            <View style={styles.rows}>
              <SectionRow
                icon={IdCardIcon}
                title="Personal info"
                summary={
                  [displayName, profile.phone, profile.home_city].filter(Boolean).join(" · ") ||
                  "Name, contact & nationality"
                }
                onPress={() => open("personal")}
              />
              <SectionRow
                icon={GradCapIcon}
                title="Academic background"
                summary={
                  [
                    labelOf(EDUCATION_LEVELS, profile.study_level),
                    labelOf(FIELDS, profile.field_of_study),
                  ]
                    .filter(Boolean)
                    .join(" · ") || "Education, field & grades"
                }
                onPress={() => open("academic")}
              />
              <SectionRow
                icon={CertificateIcon}
                title="English test"
                summary={
                  profile.language_test_status === "taken" && profile.language_test !== ""
                    ? `${labelOf(LANGUAGE_TESTS, profile.language_test)}${profile.language_test_score ? ` · ${profile.language_test_score}` : ""}`
                    : labelOf(TEST_STATUSES, profile.language_test_status) ||
                      "IELTS, TOEFL, PTE or Duolingo"
                }
                onPress={() => open("test")}
              />
              <SectionRow
                icon={WalletIcon}
                title="Budget & timeline"
                summary={[
                  profile.budget_eur_per_year
                    ? `€${profile.budget_eur_per_year.toLocaleString("en-US")}/yr`
                    : "Tuition-free only",
                  [labelOf(INTAKES, profile.intake), profile.intake_year]
                    .filter(Boolean)
                    .join(" "),
                ]
                  .filter(Boolean)
                  .join(" · ")}
                onPress={() => open("plan")}
              />
            </View>
          </FadeInUp>

          {/* destructive, deliberately far from everything else */}
          <Pressable
            onPress={onSignOut}
            accessibilityRole="button"
            style={({ pressed }) => [styles.signOutBtn, pressed && { opacity: 0.7 }]}
          >
            <LogOutIcon size={17} />
            <Text style={styles.signOutText}>Sign out</Text>
          </Pressable>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },

  topBar: { paddingHorizontal: 20, paddingTop: 14, paddingBottom: 6 },
  overline: { fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: 1.6, color: colors.textFaintest },
  title: { fontFamily: fonts.display, fontSize: 24, letterSpacing: -0.5, color: colors.ink, marginTop: 4 },

  loadingBox: { paddingVertical: 80, alignItems: "center" },
  errorBox: {
    marginTop: 24,
    marginHorizontal: 20,
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

  body: { paddingHorizontal: 20, paddingBottom: spacing.tabClearance },

  identityCard: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius["2xl"],
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 12,
    marginTop: 8,
    overflow: "hidden",
    ...shadow.card,
  },
  passportHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  passportHeadText: { fontFamily: fonts.mono, fontSize: 9, letterSpacing: 1.6, color: colors.textFaintest },
  identityRow: { flexDirection: "row", alignItems: "center", gap: 13, marginTop: 12 },
  avatar: { width: 50, height: 50, borderRadius: 15, alignItems: "center", justifyContent: "center" },
  avatarText: { fontFamily: fonts.display, fontSize: 20, color: "#fff" },
  identityName: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.ink },
  identityEmail: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 1 },
  identityFields: { flexDirection: "row", justifyContent: "space-between", marginTop: 14, marginBottom: 2 },
  mrz: { fontFamily: fonts.mono, fontSize: 11, letterSpacing: 2, color: "#C4B29B", marginTop: 2 },
  tierChip: {
    borderWidth: 1.4,
    borderColor: colors.accent,
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 6,
    transform: [{ rotate: "2deg" }],
  },
  tierChipText: { fontFamily: fonts.monoBold, fontSize: 9.5, letterSpacing: 1, color: colors.accent },

  rows: { marginTop: 18, gap: 12 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius["2xl"],
    paddingHorizontal: 14,
    paddingVertical: 14,
    minHeight: 64,
    ...shadow.card,
  },
  rowIcon: {
    width: 40,
    height: 40,
    borderRadius: 13,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  rowTitle: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  rowSummary: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textFaint, marginTop: 2 },

  signOutBtn: {
    marginTop: 28,
    height: 52,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: "#F3C4B8",
    backgroundColor: "#fff",
    flexDirection: "row",
    gap: 9,
    alignItems: "center",
    justifyContent: "center",
  },
  signOutText: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: "#B3402A" },
});
