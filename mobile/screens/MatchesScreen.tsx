/**
 * 05 — ALL MATCHES · THE FULL RANKED LIST
 * Opened from "See all" on Home. Receives the already-fetched matches via
 * route params (no refetch, instant render) and groups them by fit tier:
 * good fits first, then reaches, then safety picks — the order students
 * shortlist in. Each row opens the same MatchDetail screen as the Home cards.
 */
import React, { useMemo } from "react";
import { View, Text, StyleSheet, SectionList, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts, radius } from "../theme";
import { ChevronLeftIcon, ChevronRightIcon } from "../components/icons";
import type { Match } from "../lib/api";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Matches">;

// Same rotation as the Home cards, keyed by match id so a university keeps
// its tile color between the carousel, this list, and the detail hero.
const TILE_COLORS = [colors.accent, "#C7502F", "#F49A1A", "#1F8A5B", "#2A6FDB"];

const FIT_SECTIONS: { fit: Match["fit"]; title: string; sub: string }[] = [
  { fit: "good_fit", title: "Good fits", sub: "Strong overlap with your profile" },
  { fit: "reach", title: "Reach", sub: "Ambitious but worth a shot" },
  { fit: "safety", title: "Safety picks", sub: "You clear the bar comfortably" },
];

const euro = (v: string | null) =>
  v === null ? "—" : `€${Math.round(parseFloat(v)).toLocaleString("en-US")}`;

function MatchRow({ match, onPress }: { match: Match; onPress: () => void }) {
  const pct = Math.round(parseFloat(match.score));
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${match.university}, ${match.program_name}, ${pct}% match`}
      style={({ pressed }) => [styles.row, pressed && { opacity: 0.8 }]}
    >
      <View style={[styles.tile, { backgroundColor: TILE_COLORS[match.id % TILE_COLORS.length] }]}>
        <Text style={styles.tileText}>{match.university.charAt(0)}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.rowName} numberOfLines={1}>{match.university}</Text>
        <Text style={styles.rowMeta} numberOfLines={1}>
          {match.program_name} · {match.city}
        </Text>
        <Text style={styles.rowFee}>{euro(match.tuition_fee_eur)}/yr</Text>
      </View>
      <View style={styles.rowRight}>
        <Text style={styles.rowScore}>{pct}%</Text>
        <ChevronRightIcon size={16} color={colors.textFaintest} />
      </View>
    </Pressable>
  );
}

export default function MatchesScreen({ navigation, route }: Props) {
  const { matches } = route.params;

  const sections = useMemo(
    () =>
      FIT_SECTIONS.map((s) => ({
        ...s,
        data: matches.filter((m) => m.fit === s.fit),
      })).filter((s) => s.data.length > 0),
    [matches],
  );

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
        <View>
          <Text style={styles.title}>Your matches</Text>
          <Text style={styles.subtitle}>
            {matches.length} programme{matches.length === 1 ? "" : "s"}, best fit first
          </Text>
        </View>
      </View>

      <SectionList
        sections={sections}
        keyExtractor={(m) => String(m.id)}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.listBody}
        stickySectionHeadersEnabled={false}
        renderSectionHeader={({ section }) => (
          <View style={styles.sectionHead}>
            <Text style={styles.sectionTitle}>{section.title}</Text>
            <Text style={styles.sectionSub}>{section.sub}</Text>
          </View>
        )}
        renderItem={({ item }) => (
          <MatchRow
            match={item}
            onPress={() => navigation.navigate("MatchDetail", { match: item })}
          />
        )}
        ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>No matches yet</Text>
            <Text style={styles.emptyText}>
              We're matching universities to your profile — check back in a minute.
            </Text>
          </View>
        }
      />
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
  subtitle: { fontFamily: fonts.bodySemi, fontSize: 12, color: colors.textFaint, marginTop: 1 },

  listBody: { paddingHorizontal: 20, paddingBottom: 28 },

  sectionHead: { marginTop: 22, marginBottom: 12 },
  sectionTitle: { fontFamily: fonts.display, fontSize: 16.5, letterSpacing: -0.2, color: colors.ink },
  sectionSub: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textFaint, marginTop: 1 },

  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.xl,
    padding: 14,
  },
  tile: {
    width: 46,
    height: 46,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  tileText: { fontFamily: fonts.display, fontSize: 19, color: "#fff" },
  rowName: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  rowMeta: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textFaint, marginTop: 1 },
  rowFee: { fontFamily: fonts.displaySemi, fontSize: 12.5, color: colors.textMuted, marginTop: 4 },
  rowRight: { alignItems: "flex-end", gap: 4 },
  rowScore: { fontFamily: fonts.display, fontSize: 15, color: colors.success },

  emptyBox: { alignItems: "center", paddingVertical: 70, paddingHorizontal: 30, gap: 6 },
  emptyTitle: { fontFamily: fonts.display, fontSize: 17, color: colors.ink },
  emptyText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textFaint,
    textAlign: "center",
    lineHeight: 19,
  },
});
