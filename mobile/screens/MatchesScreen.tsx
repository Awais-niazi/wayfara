/**
 * 05 — EXPLORE · THE FULL RANKED LIST
 * The Explore tab: every matched programme, grouped by fit tier — good fits
 * first, then reaches, then safety picks — the order students shortlist in.
 * Fetches its own data (it's a persistent tab, reachable from anywhere);
 * each row opens the same MatchDetail screen as the Home cards.
 */
import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  SectionList,
  ActivityIndicator,
  Pressable,
  RefreshControl,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";

import { colors, fonts, radius, shadow, spacing } from "../theme";
import { ChevronRightIcon } from "../components/icons";
import { cityCode } from "../components/travel";
import { CityScape, CityTile } from "../components/scenery";
import { FadeInUp, PressableScale } from "../components/motion";

import { getMatches, type Match } from "../lib/api";
import type { TabScreenProps } from "../navigation/types";

type Props = TabScreenProps<"Explore">;

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
    <PressableScale
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${match.university}, ${match.program_name}, ${pct}% match`}
      style={styles.row}
    >
      <CityTile city={match.city} code={cityCode(match.city)} size={50} />
      <View style={{ flex: 1 }}>
        <Text style={styles.rowName} numberOfLines={1}>{match.university}</Text>
        <Text style={styles.rowMeta} numberOfLines={1}>
          {match.program_name} · {match.city}
        </Text>
        <Text style={styles.rowFee}>{euro(match.tuition_fee_eur)}/YR</Text>
      </View>
      <View style={styles.rowRight}>
        <Text style={styles.rowScore}>{pct}%</Text>
        <ChevronRightIcon size={16} color={colors.textFaintest} />
      </View>
    </PressableScale>
  );
}

export default function MatchesScreen({ navigation }: Props) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(async (mode: "initial" | "refresh") => {
    mode === "initial" ? setLoading(true) : setRefreshing(true);
    try {
      setMatches(await getMatches());
      setError(false);
    } catch {
      if (mode === "initial") setError(true);
    } finally {
      mode === "initial" ? setLoading(false) : setRefreshing(false);
    }
  }, []);

  // Re-fetch on focus: a profile edit re-matches in the background.
  useFocusEffect(
    useCallback(() => {
      load("initial");
    }, [load]),
  );

  const sections = FIT_SECTIONS.map((s) => ({
    ...s,
    data: matches.filter((m) => m.fit === s.fit),
  })).filter((s) => s.data.length > 0);

  const insets = useSafeAreaInsets();
  const bannerHeight = 148 + insets.top;

  return (
    <View style={styles.root}>
      {/* Arrivals banner: the harbour panorama runs full-bleed under the
          status bar; the cream counter-sign strip keeps the type on-contrast. */}
      <FadeInUp>
        <View style={[styles.banner, { height: bannerHeight }]}>
          <View style={StyleSheet.absoluteFill}>
            <CityScape scene="harbour" height={bannerHeight} />
          </View>
          <View style={styles.bannerSign}>
            <Text style={styles.overline}>ARRIVALS — RANKED BY FIT</Text>
            <Text style={styles.title}>Your matches</Text>
            {!loading && !error && (
              <Text style={styles.subtitle}>
                {matches.length} programme{matches.length === 1 ? "" : "s"}, best fit first
              </Text>
            )}
          </View>
        </View>
      </FadeInUp>

      {loading && (
        <View style={styles.centerBox}>
          <ActivityIndicator color={colors.accent} />
        </View>
      )}

      {error && !loading && (
        <Pressable style={styles.errorBox} onPress={() => load("initial")}>
          <Text style={styles.errorText}>Couldn't load your matches.</Text>
          <Text style={styles.errorRetry}>Tap to retry</Text>
        </Pressable>
      )}

      {!loading && !error && (
        <SectionList
          sections={sections}
          keyExtractor={(m) => String(m.id)}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.listBody}
          stickySectionHeadersEnabled={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => load("refresh")}
              tintColor={colors.accent}
            />
          }
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
              <Text style={styles.emptyTitle}>Nothing clears your filters</Text>
              <Text style={styles.emptyText}>
                No budget set means tuition-free programmes only — and those are
                rare. Adjust your budget or field in Profile; matches rebuild
                the moment you save.
              </Text>
              <PressableScale
                onPress={() => navigation.navigate("Profile")}
                accessibilityRole="button"
                style={styles.emptyBtn}
              >
                <Text style={styles.emptyBtnText}>Open my profile</Text>
              </PressableScale>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },

  banner: {
    justifyContent: "flex-end",
    overflow: "hidden",
  },
  bannerSign: {
    backgroundColor: "rgba(251,246,239,0.92)",
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 8,
  },
  overline: { fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: 1.6, color: colors.textFaintest },
  title: { fontFamily: fonts.display, fontSize: 24, letterSpacing: -0.5, color: colors.ink, marginTop: 4 },
  subtitle: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 2 },

  centerBox: { alignItems: "center", paddingVertical: 70 },
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

  listBody: { paddingHorizontal: 20, paddingBottom: spacing.tabClearance },

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
    ...shadow.card,
  },
  rowName: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  rowMeta: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textFaint, marginTop: 1 },
  rowFee: { fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: 0.5, color: colors.textMuted, marginTop: 5 },
  rowRight: { alignItems: "flex-end", gap: 4 },
  rowScore: { fontFamily: fonts.monoBold, fontSize: 14, color: colors.success },

  emptyBox: { alignItems: "center", paddingVertical: 70, paddingHorizontal: 30, gap: 6 },
  emptyBtn: {
    marginTop: 12,
    height: 44,
    paddingHorizontal: 22,
    borderRadius: radius.md,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    ...shadow.accent,
  },
  emptyBtnText: { fontFamily: fonts.displaySemi, fontSize: 13.5, color: "#fff" },
  emptyTitle: { fontFamily: fonts.display, fontSize: 17, color: colors.ink },
  emptyText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textFaint,
    textAlign: "center",
    lineHeight: 19,
  },
});
