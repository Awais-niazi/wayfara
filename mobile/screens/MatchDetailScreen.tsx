/**
 * 04 — MATCH DETAIL · ONE UNIVERSITY, ONE PROGRAMME
 * Opened from a match card on Home. Renders instantly from the Match passed
 * as a route param (name, city, fee, deadline, score), then enriches with the
 * curated catalog record:
 *   - overview / description  ← GET /api/universities/<id>/  (public, cached)
 *   - matched programme extras (language, intake, IELTS, scholarship)
 *   - other active programmes at the same university
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Linking,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts, radius, shadow } from "../theme";
import { ChevronLeftIcon, ChevronRightIcon, CheckIcon, GlobeIcon } from "../components/icons";
import { CodeBadge, Stamp, cityCode, uniCode } from "../components/travel";
import {
  createApplication,
  firstErrorMessage,
  getApplications,
  getUniversity,
  type CatalogProgram,
  type UniversityDetail,
} from "../lib/api";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "MatchDetail">;

// One warm sand hero for every university — the destination code carries the
// identity now, not a rotating tint.
const HERO_TINT = "#EFE0CC";

const FIT_LABELS: Record<string, { label: string; ink: string; bg: string }> = {
  safety: { label: "Safety pick", ink: colors.success, bg: "#E8F4EC" },
  good_fit: { label: "Good fit", ink: colors.accent, bg: colors.accentSoft },
  reach: { label: "Reach", ink: "#B4841A", bg: "#FDF3DF" },
};

const euro = (v: string | null) =>
  v === null ? "—" : `€${Math.round(parseFloat(v)).toLocaleString("en-US")}`;

const longDate = (iso: string | null) =>
  iso === null
    ? "—"
    : new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

const years = (v: string | null) => {
  if (v === null) return "—";
  const n = parseFloat(v);
  return `${n % 1 === 0 ? n.toFixed(0) : n} yr${n === 1 ? "" : "s"}`;
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

function ProgramRow({ program, tint, last }: { program: CatalogProgram; tint: string; last: boolean }) {
  return (
    <View style={[styles.programRow, last && { borderBottomWidth: 0 }]}>
      <View style={[styles.programDot, { backgroundColor: tint }]} />
      <View style={{ flex: 1 }}>
        <Text style={styles.programName} numberOfLines={2}>{program.name}</Text>
        <Text style={styles.programMeta} numberOfLines={1}>
          {program.degree_level === "masters" ? "Master's" : "Bachelor's"} · {euro(program.tuition_fee_eur)}/yr
          {program.scholarship_available ? " · Scholarship" : ""}
        </Text>
      </View>
    </View>
  );
}

export default function MatchDetailScreen({ navigation, route }: Props) {
  const { match } = route.params;
  const fit = FIT_LABELS[match.fit] ?? FIT_LABELS.good_fit;
  const pct = Math.round(parseFloat(match.score));

  const [uni, setUni] = useState<UniversityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  // The application for THIS programme, if the student already started one.
  const [applicationId, setApplicationId] = useState<number | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(false);
    getUniversity(match.university_id)
      .then(setUni)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
    // Additive: is there already an application for this programme?
    getApplications()
      .then((apps) => {
        const existing = apps.find((a) => a.program === match.program);
        setApplicationId(existing ? existing.id : null);
      })
      .catch(() => {});
  };

  useEffect(load, [match.university_id]);

  const onApply = async () => {
    if (applying) return;
    if (applicationId !== null) {
      navigation.navigate("ApplicationDetail", { id: applicationId });
      return;
    }
    setApplying(true);
    setApplyError(null);
    try {
      const application = await createApplication(match.program);
      setApplicationId(application.id);
      navigation.navigate("ApplicationDetail", { id: application.id });
    } catch (err) {
      setApplyError(firstErrorMessage(err));
    } finally {
      setApplying(false);
    }
  };

  // Catalog record of the matched programme — carries fields the match doesn't.
  const catalogProgram = useMemo(
    () => uni?.programs.find((p) => p.id === match.program) ?? null,
    [uni, match.program],
  );

  const otherPrograms = useMemo(
    () => (uni?.programs ?? []).filter((p) => p.id !== match.program),
    [uni, match.program],
  );

  const about = uni ? uni.overview || uni.description : "";

  return (
    <View style={styles.root}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollBody}>
        {/* hero — destination header */}
        <View style={[styles.hero, { backgroundColor: HERO_TINT }]}>
          <Text style={styles.heroWatermark} numberOfLines={1}>
            {cityCode(match.city)}
          </Text>
          <SafeAreaView edges={["top"]}>
            <View style={styles.heroBar}>
              <Pressable
                onPress={navigation.goBack}
                accessibilityRole="button"
                accessibilityLabel="Go back"
                hitSlop={8}
                style={({ pressed }) => [styles.backBtn, pressed && styles.pressed]}
              >
                <ChevronLeftIcon size={20} />
              </Pressable>
              <Stamp label={`${pct}% match`} ink={colors.success} tilt={2} style={{ backgroundColor: "rgba(255,255,255,0.85)" }} />
            </View>
          </SafeAreaView>
        </View>

        <View style={styles.pad}>
          {/* identity — the code badge straddles the hero edge */}
          <View style={styles.heroBadge}>
            <CodeBadge code={uniCode(match.university)} size={56} ink={colors.accent} bg="#fff" />
          </View>
          <Text style={styles.uniName}>{match.university}</Text>
          <Text style={styles.uniMeta}>
            {match.city}
            {match.campus ? ` · ${match.campus} campus` : ""}
          </Text>

          <View style={styles.chipRow}>
            <View style={[styles.fitChip, { backgroundColor: fit.bg }]}>
              <Text style={[styles.fitChipText, { color: fit.ink }]}>{fit.label}</Text>
            </View>
            {match.world_ranking !== null && (
              <View style={styles.rankChip}>
                <Text style={styles.rankChipText}>
                  #{match.world_ranking}{uni?.ranking_system ? ` ${uni.ranking_system}` : " world ranking"}
                </Text>
              </View>
            )}
            {match.data_verified && (
              <View style={styles.verifiedChip}>
                <CheckIcon size={12} />
                <Text style={styles.verifiedChipText}>Verified data</Text>
              </View>
            )}
          </View>

          {/* matched programme */}
          <View style={styles.programCard}>
            <Text style={styles.cardCaption}>YOUR MATCHED PROGRAMME</Text>
            <Text style={styles.programTitle}>{match.program_name}</Text>
            <View style={styles.statsGrid}>
              <Stat label="Tuition / yr" value={euro(match.tuition_fee_eur)} />
              <Stat label="Duration" value={years(match.duration_years)} />
              <Stat label="Deadline" value={longDate(match.application_deadline)} />
              <Stat
                label="Level"
                value={match.degree_level === "masters" ? "Master's" : "Bachelor's"}
              />
              {catalogProgram && (
                <>
                  <Stat label="Language" value={catalogProgram.language || "—"} />
                  <Stat
                    label="Min IELTS"
                    value={catalogProgram.min_ielts_score ? String(parseFloat(catalogProgram.min_ielts_score)) : "—"}
                  />
                </>
              )}
            </View>
            {catalogProgram?.scholarship_available && (
              <View style={styles.scholarshipNote}>
                <CheckIcon size={13} />
                <Text style={styles.scholarshipText}>Scholarships available for this programme</Text>
              </View>
            )}
          </View>

          {/* about — enriched from the catalog, loads behind the fold */}
          {loading && (
            <View style={styles.loadingBox}>
              <ActivityIndicator color={colors.accent} />
            </View>
          )}

          {error && !loading && (
            <Pressable
              onPress={load}
              accessibilityRole="button"
              style={({ pressed }) => [styles.errorBox, pressed && styles.pressed]}
            >
              <Text style={styles.errorText}>Couldn't load university details.</Text>
              <Text style={styles.errorRetry}>Tap to retry</Text>
            </Pressable>
          )}

          {!loading && !error && !!about && (
            <>
              <Text style={styles.sectionTitle}>About {match.university}</Text>
              <Text style={styles.aboutText}>{about}</Text>
            </>
          )}

          {!loading && !error && otherPrograms.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>
                More programmes here ({otherPrograms.length})
              </Text>
              <View style={styles.programList}>
                {otherPrograms.map((p, i) => (
                  <ProgramRow key={p.id} program={p} tint={colors.accent} last={i === otherPrograms.length - 1} />
                ))}
              </View>
            </>
          )}
        </View>
      </ScrollView>

      {/* pinned actions */}
      <SafeAreaView edges={["bottom"]} style={styles.footer}>
        {!!uni?.website && (
          <Pressable
            onPress={() => Linking.openURL(uni.website)}
            accessibilityRole="link"
            accessibilityLabel={`Open ${match.university} website`}
            style={({ pressed }) => [styles.websiteBtn, pressed && styles.pressed]}
          >
            <GlobeIcon size={18} color={colors.accent} />
            <Text style={styles.websiteBtnText}>Website</Text>
          </Pressable>
        )}
        <Pressable
          onPress={onApply}
          accessibilityRole="button"
          accessibilityLabel={
            applicationId !== null ? "View your application" : "Add to my applications"
          }
          style={({ pressed }) => [styles.ctaBtn, pressed && styles.pressed]}
        >
          <Text style={styles.ctaBtnText}>
            {applying
              ? "Starting…"
              : applicationId !== null
                ? "View application"
                : "Add to my applications"}
          </Text>
          <ChevronRightIcon size={18} color="#fff" />
        </Pressable>
      </SafeAreaView>
      {applyError !== null && (
        <View style={styles.applyErrorBar}>
          <Text style={styles.applyErrorText}>{applyError}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },
  applyErrorBar: {
    backgroundColor: "#FCEBE7",
    borderTopWidth: 1,
    borderTopColor: "#F3C4B8",
    paddingVertical: 8,
    paddingHorizontal: 20,
  },
  applyErrorText: { fontFamily: fonts.bodySemi, fontSize: 12.5, color: "#B3402A", textAlign: "center" },
  scrollBody: { paddingBottom: 24 },
  pad: { paddingHorizontal: 20 },
  pressed: { opacity: 0.7 },

  hero: { paddingBottom: 34, overflow: "hidden" },
  // The destination code as a giant printed watermark behind the hero bar.
  heroWatermark: {
    position: "absolute",
    right: -8,
    bottom: -26,
    fontFamily: fonts.monoBold,
    fontSize: 110,
    letterSpacing: 4,
    color: "rgba(255,255,255,0.5)",
  },
  heroBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 40,
  },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.85)",
    alignItems: "center",
    justifyContent: "center",
  },
  heroBadge: { marginTop: -28, alignSelf: "flex-start", borderRadius: 17, ...shadow.card },

  uniName: { fontFamily: fonts.display, fontSize: 24, letterSpacing: -0.6, color: colors.ink, marginTop: 12 },
  uniMeta: { fontFamily: fonts.bodyRegular, fontSize: 13.5, color: colors.textFaint, marginTop: 3 },

  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 },
  fitChip: { paddingVertical: 6, paddingHorizontal: 12, borderRadius: radius.pill },
  fitChipText: { fontFamily: fonts.bodyBold, fontSize: 12 },
  rankChip: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: radius.pill,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.border,
  },
  rankChipText: { fontFamily: fonts.bodyBold, fontSize: 12, color: colors.textMuted },
  verifiedChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: radius.pill,
    backgroundColor: "#E8F4EC",
  },
  verifiedChipText: { fontFamily: fonts.bodyBold, fontSize: 12, color: colors.success },

  programCard: {
    marginTop: 20,
    backgroundColor: "#fff",
    borderRadius: radius["2xl"],
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: 18,
    ...shadow.card,
  },
  cardCaption: { fontFamily: fonts.mono, fontSize: 9, letterSpacing: 1.6, color: colors.textFaintest },
  programTitle: { fontFamily: fonts.display, fontSize: 17, color: colors.ink, marginTop: 6 },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", marginTop: 8 },
  stat: { width: "33.33%", marginTop: 12 },
  statLabel: { fontFamily: fonts.mono, fontSize: 8.5, letterSpacing: 1.1, color: colors.textFaintest },
  statValue: { fontFamily: fonts.monoBold, fontSize: 13.5, color: colors.ink, marginTop: 2 },
  scholarshipNote: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    marginTop: 16,
    backgroundColor: "#E8F4EC",
    borderRadius: radius.md,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  scholarshipText: { fontFamily: fonts.bodySemi, fontSize: 12.5, color: colors.success, flex: 1 },

  loadingBox: { paddingVertical: 28, alignItems: "center" },
  errorBox: {
    marginTop: 22,
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

  sectionTitle: { fontFamily: fonts.display, fontSize: 18, letterSpacing: -0.3, color: colors.ink, marginTop: 26 },
  aboutText: { fontFamily: fonts.bodyRegular, fontSize: 14, lineHeight: 22, color: colors.textMuted, marginTop: 8 },

  programList: {
    marginTop: 12,
    backgroundColor: "#fff",
    borderRadius: radius["2xl"],
    borderWidth: 1,
    borderColor: colors.borderSoft,
    paddingHorizontal: 16,
    ...shadow.card,
  },
  programRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderSoft,
  },
  programDot: { width: 10, height: 10, borderRadius: 5 },
  programName: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.ink },
  programMeta: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textFaint, marginTop: 2 },

  footer: {
    flexDirection: "row",
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: "rgba(251,246,239,0.96)",
    borderTopWidth: 1,
    borderTopColor: "#EBDDCB",
  },
  websiteBtn: {
    height: 52,
    paddingHorizontal: 18,
    borderRadius: radius.lg,
    backgroundColor: colors.accentSoft,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  websiteBtnText: { fontFamily: fonts.displaySemi, fontSize: 14.5, color: colors.accent },
  ctaBtn: {
    flex: 1,
    height: 52,
    borderRadius: radius.lg,
    backgroundColor: colors.accent,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    ...shadow.accent,
  },
  ctaBtnText: { fontFamily: fonts.displaySemi, fontSize: 14.5, color: "#fff" },
});
