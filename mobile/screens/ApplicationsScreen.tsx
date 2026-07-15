/**
 * 08 — APPLICATIONS (the Apps tab)
 * Every programme the student is pursuing, ordered by their own priority:
 * status chip, document progress, deadline countdown. Tapping opens the
 * application workspace. Data: GET /api/v1/applications/.
 */
import React, { useCallback, useState } from "react";
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
import { useFocusEffect } from "@react-navigation/native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts, radius } from "../theme";
import { ChevronLeftIcon, ChevronRightIcon, AppsIcon } from "../components/icons";
import { getApplications, type Application, type ApplicationStatus } from "../lib/api";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Applications">;

export const STATUS_META: Record<ApplicationStatus, { label: string; ink: string; bg: string }> = {
  shortlisted: { label: "Shortlisted", ink: "#6B5CA5", bg: "#F3ECFB" },
  in_progress: { label: "Preparing", ink: "#B4841A", bg: "#FDF3DF" },
  submitted: { label: "Submitted", ink: "#2A6FDB", bg: "#E9F1FB" },
  offer_received: { label: "Offer 🎉", ink: "#1F8A5B", bg: "#E8F4EC" },
  waitlisted: { label: "Waitlisted", ink: "#B4841A", bg: "#FDF3DF" },
  rejected: { label: "Not accepted", ink: "#B3402A", bg: "#FCEBE7" },
  place_confirmed: { label: "Place confirmed 🇫🇮", ink: "#1F8A5B", bg: "#E8F4EC" },
  withdrawn: { label: "Withdrawn", ink: "#8C7B6B", bg: "#F1EAE0" },
};

function daysUntil(iso: string | null): string | null {
  if (!iso) return null;
  const days = Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000);
  if (days < 0) return "Deadline passed";
  if (days === 0) return "Deadline today";
  return `${days} day${days === 1 ? "" : "s"} to deadline`;
}

export default function ApplicationsScreen({ navigation }: Props) {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(async (mode: "initial" | "refresh") => {
    mode === "initial" ? setLoading(true) : setRefreshing(true);
    try {
      setApps(await getApplications());
      setError(false);
    } catch {
      if (mode === "initial") setError(true);
    } finally {
      mode === "initial" ? setLoading(false) : setRefreshing(false);
    }
  }, []);

  // Re-fetch on focus: status/docs change inside the workspace screen.
  useFocusEffect(
    useCallback(() => {
      load("initial");
    }, [load]),
  );

  const renderItem = ({ item }: { item: Application }) => {
    const meta = STATUS_META[item.status];
    const deadline = daysUntil(item.application_deadline);
    return (
      <Pressable
        onPress={() => navigation.navigate("ApplicationDetail", { id: item.id })}
        accessibilityRole="button"
        accessibilityLabel={`${item.university}, ${meta.label}. Open application`}
        style={({ pressed }) => [styles.card, pressed && { opacity: 0.85 }]}
      >
        <View style={styles.cardTop}>
          <View style={[styles.avatar, { backgroundColor: colors.accent }]}>
            <Text style={styles.avatarText}>{item.university.charAt(0)}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.uniName} numberOfLines={1}>{item.university}</Text>
            <Text style={styles.programName} numberOfLines={1}>{item.program_name}</Text>
          </View>
          <ChevronRightIcon size={18} color="#B9A99A" />
        </View>
        <View style={styles.cardBottom}>
          <View style={[styles.statusChip, { backgroundColor: meta.bg }]}>
            <Text style={[styles.statusChipText, { color: meta.ink }]}>{meta.label}</Text>
          </View>
          <Text style={styles.docsText}>
            {item.docs_ready}/{item.docs_total} documents
          </Text>
          {deadline !== null && <Text style={styles.deadlineText}>{deadline}</Text>}
        </View>
        {/* docs progress track */}
        <View style={styles.track}>
          <View
            style={[
              styles.trackFill,
              {
                width: `${item.docs_total ? (item.docs_ready / item.docs_total) * 100 : 0}%`,
              },
            ]}
          />
        </View>
      </Pressable>
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
        <Text style={styles.title}>My applications</Text>
      </View>

      {loading && (
        <View style={styles.centerBox}>
          <ActivityIndicator color={colors.accent} />
        </View>
      )}

      {error && !loading && (
        <Pressable style={styles.errorBox} onPress={() => load("initial")}>
          <Text style={styles.errorText}>Couldn't load your applications.</Text>
          <Text style={styles.errorRetry}>Tap to retry</Text>
        </Pressable>
      )}

      {!loading && !error && (
        <FlatList
          data={apps}
          keyExtractor={(a) => String(a.id)}
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
                <AppsIcon size={24} color={colors.accent} />
              </View>
              <Text style={styles.emptyTitle}>No applications yet</Text>
              <Text style={styles.emptyText}>
                Find a programme you like in your matches and tap "Add to my
                applications" — we'll build your document checklist for it.
              </Text>
              <Pressable
                onPress={() => navigation.navigate("Home")}
                style={({ pressed }) => [styles.emptyBtn, pressed && { opacity: 0.8 }]}
              >
                <Text style={styles.emptyBtnText}>Browse my matches</Text>
              </Pressable>
            </View>
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
  title: { fontFamily: fonts.display, fontSize: 20, letterSpacing: -0.4, color: colors.ink },

  centerBox: { alignItems: "center", paddingVertical: 60, paddingHorizontal: 32, gap: 8 },
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

  list: { padding: 16, gap: 12, flexGrow: 1 },
  card: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius["2xl"],
    padding: 15,
  },
  cardTop: { flexDirection: "row", alignItems: "center", gap: 12 },
  avatar: { width: 42, height: 42, borderRadius: 13, alignItems: "center", justifyContent: "center" },
  avatarText: { fontFamily: fonts.display, fontSize: 17, color: "#fff" },
  uniName: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  programName: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 1 },

  cardBottom: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 12 },
  statusChip: { paddingVertical: 4, paddingHorizontal: 10, borderRadius: radius.pill },
  statusChipText: { fontFamily: fonts.bodyBold, fontSize: 11.5 },
  docsText: { fontFamily: fonts.bodySemi, fontSize: 12, color: colors.textFaint },
  deadlineText: { fontFamily: fonts.bodySemi, fontSize: 11.5, color: "#B4841A", marginLeft: "auto" },

  track: { height: 6, borderRadius: radius.pill, backgroundColor: "#F1E7DA", marginTop: 11, overflow: "hidden" },
  trackFill: { height: "100%", borderRadius: radius.pill, backgroundColor: colors.accent },

  emptyBadge: {
    width: 54,
    height: 54,
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
  emptyBtn: {
    marginTop: 10,
    height: 46,
    paddingHorizontal: 22,
    borderRadius: radius.md,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyBtnText: { fontFamily: fonts.displaySemi, fontSize: 14, color: "#fff" },
});
