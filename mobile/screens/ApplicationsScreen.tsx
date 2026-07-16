/**
 * 08 — APPLICATIONS (the Apps tab)
 * Every programme the student is pursuing, each one rendered as a boarding
 * pass: uni code + passport-stamp status, the route to its city with the
 * plane at the journey stage, then below the tear line the document count
 * and deadline. Tapping opens the application workspace.
 * Data: GET /api/v1/applications/.
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

import { colors, fonts, radius, shadow, spacing } from "../theme";
import { AppsIcon } from "../components/icons";
import { Barcode, CodeBadge, RouteLine, Stamp, TicketDivider, TicketField, cityCode, uniCode } from "../components/travel";
import { FadeInUp, PressableScale, ProgressBar } from "../components/motion";

import { getApplications, type Application, type ApplicationStatus } from "../lib/api";
import type { TabScreenProps } from "../navigation/types";

type Props = TabScreenProps<"Apps">;

export const STATUS_META: Record<ApplicationStatus, { label: string; ink: string; bg: string }> = {
  shortlisted: { label: "Shortlisted", ink: "#6B5CA5", bg: "#F3ECFB" },
  in_progress: { label: "Preparing", ink: "#B4841A", bg: "#FDF3DF" },
  submitted: { label: "Submitted", ink: "#2A6FDB", bg: "#E9F1FB" },
  offer_received: { label: "Offer", ink: "#1F8A5B", bg: "#E8F4EC" },
  waitlisted: { label: "Waitlisted", ink: "#B4841A", bg: "#FDF3DF" },
  rejected: { label: "Not accepted", ink: "#B3402A", bg: "#FCEBE7" },
  place_confirmed: { label: "Confirmed", ink: "#1F8A5B", bg: "#E8F4EC" },
  withdrawn: { label: "Withdrawn", ink: "#8C7B6B", bg: "#F1EAE0" },
};

/** Where the plane sits on the route for each status. */
const STATUS_PROGRESS: Record<ApplicationStatus, number> = {
  shortlisted: 0.08,
  in_progress: 0.3,
  submitted: 0.55,
  waitlisted: 0.68,
  offer_received: 0.85,
  rejected: 0.55,
  place_confirmed: 1,
  withdrawn: 0,
};

function daysUntil(iso: string | null): string | null {
  if (!iso) return null;
  const days = Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000);
  if (days < 0) return "PASSED";
  if (days === 0) return "TODAY";
  return `${days} DAY${days === 1 ? "" : "S"}`;
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

  const renderItem = ({ item, index }: { item: Application; index: number }) => {
    const meta = STATUS_META[item.status];
    const deadline = daysUntil(item.application_deadline);
    const settled = ["rejected", "withdrawn"].includes(item.status);
    return (
      <FadeInUp delay={index * 60}>
        <PressableScale
          onPress={() => navigation.navigate("ApplicationDetail", { id: item.id })}
          accessibilityRole="button"
          accessibilityLabel={`${item.university}, ${meta.label}. Open application`}
          style={[styles.card, settled && { opacity: 0.62 }]}
        >
          <View style={styles.cardTop}>
            <CodeBadge code={uniCode(item.university)} size={44} />
            <View style={{ flex: 1 }}>
              <Text style={styles.uniName} numberOfLines={1}>{item.university}</Text>
              <Text style={styles.programName} numberOfLines={1}>{item.program_name}</Text>
            </View>
            <Stamp label={meta.label} ink={meta.ink} tilt={2} />
          </View>

          <View style={styles.routeBox}>
            <RouteLine
              from="PAK"
              to={cityCode(item.city)}
              progress={STATUS_PROGRESS[item.status]}
              tint={settled ? colors.textFaintest : colors.accent}
            />
          </View>

          <TicketDivider inset={16} />

          <View style={styles.cardBottom}>
            <View style={{ flex: 1 }}>
              <TicketField label="Documents" value={`${item.docs_ready}/${item.docs_total}`} />
              <ProgressBar
                progress={item.docs_total ? item.docs_ready / item.docs_total : 0}
                tint={colors.accent}
                height={5}
                style={{ marginTop: 7, maxWidth: 120 }}
              />
            </View>
            {deadline !== null && (
              <TicketField
                label="Deadline in"
                value={deadline}
                align="right"
                valueColor={deadline === "PASSED" ? colors.textFaintest : colors.warningInkSoft}
              />
            )}
          </View>

          <View style={styles.barcodeRow}>
            <Barcode seed={item.id * 7919} height={16} color="#CDBBA4" />
            <Text style={styles.gateText}>GATE · STUDYINFO.FI</Text>
          </View>
        </PressableScale>
      </FadeInUp>
    );
  };

  return (
    <SafeAreaView edges={["top"]} style={styles.root}>
      <FadeInUp>
        <View style={styles.topBar}>
          <Text style={styles.overline}>BOARDING PASSES</Text>
          <Text style={styles.title}>My applications</Text>
        </View>
      </FadeInUp>

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
          showsVerticalScrollIndicator={false}
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
              <Text style={styles.emptyTitle}>No boarding passes yet</Text>
              <Text style={styles.emptyText}>
                Find a programme you like in your matches and tap "Add to my
                applications" — we'll build your document checklist for it.
              </Text>
              <PressableScale
                onPress={() => navigation.navigate("Explore")}
                style={styles.emptyBtn}
              >
                <Text style={styles.emptyBtnText}>Browse my matches</Text>
              </PressableScale>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },
  topBar: { paddingHorizontal: 20, paddingTop: 14, paddingBottom: 6 },
  overline: { fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: 1.6, color: colors.textFaintest },
  title: { fontFamily: fonts.display, fontSize: 24, letterSpacing: -0.5, color: colors.ink, marginTop: 4 },

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

  list: { padding: 20, paddingTop: 12, gap: 14, flexGrow: 1, paddingBottom: spacing.tabClearance },
  card: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius["2xl"],
    paddingHorizontal: 16,
    paddingTop: 15,
    paddingBottom: 12,
    overflow: "hidden",
    ...shadow.card,
  },
  cardTop: { flexDirection: "row", alignItems: "center", gap: 12 },
  uniName: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  programName: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 1 },

  routeBox: { marginTop: 14, marginBottom: 2 },

  cardBottom: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", marginTop: 2 },

  barcodeRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 12,
  },
  gateText: { fontFamily: fonts.mono, fontSize: 8.5, letterSpacing: 1.2, color: colors.textFaintest },

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
    ...shadow.accent,
  },
  emptyBtnText: { fontFamily: fonts.displaySemi, fontSize: 14, color: "#fff" },
});
