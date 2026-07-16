/**
 * Travel-document primitives — the Wayfara visual identity.
 *
 * The app reads as a journey: applications are boarding passes, statuses are
 * passport stamps, progress is a flight route. These pieces keep that language
 * consistent everywhere. All type in here is Space Mono (fonts.mono) — the
 * "printed ticket" voice, distinct from the editorial Grotesk/Manrope voice.
 */
import React from "react";
import { View, Text, StyleSheet, ViewStyle } from "react-native";
import Svg, { Line, Circle } from "react-native-svg";

import { colors, fonts } from "../theme";
import { PlaneSideIcon } from "./icons";

// ─── Airport-style codes ──────────────────────────────────────────────────────
const CODE_STOPWORDS = new Set(["university", "of", "the", "for", "applied", "sciences"]);

/** "Aalto University" → AAL · "University of Helsinki" → HEL · "LUT University" → LUT */
export function uniCode(name: string): string {
  const words = name.split(/[\s,–-]+/).filter((w) => w && !CODE_STOPWORDS.has(w.toLowerCase()));
  const base = (words[0] ?? name).replace(/[^A-Za-z]/g, "");
  return (base || "UNI").slice(0, 3).toUpperCase();
}

/** City → 3-letter destination code (Helsinki → HEL, Tampere → TAM). */
export function cityCode(city: string | null | undefined): string {
  if (!city) return "FIN";
  return (city.replace(/[^A-Za-z]/g, "") || "FIN").slice(0, 3).toUpperCase();
}

// ─── Passport stamp ───────────────────────────────────────────────────────────
export function Stamp({
  label,
  ink,
  tilt = -2,
  style,
}: {
  label: string;
  ink: string;
  /** degrees — a hair of rotation sells the rubber-stamp read */
  tilt?: number;
  style?: ViewStyle;
}) {
  return (
    <View
      style={[
        styles.stamp,
        { borderColor: ink, transform: [{ rotate: `${tilt}deg` }] },
        style,
      ]}
    >
      <Text style={[styles.stampText, { color: ink }]} numberOfLines={1}>
        {label.toUpperCase()}
      </Text>
    </View>
  );
}

// ─── Flight route line ────────────────────────────────────────────────────────
/**
 * ISB ✈┄┄┄┄●┄┄┄┄○ HEL — progress moves the plane along the dashes.
 * Codes render outside the track so the dashes stretch to fill.
 */
export function RouteLine({
  from,
  to,
  progress = 0,
  tint = colors.accent,
  codeColor = colors.textFaint,
}: {
  from: string;
  to: string;
  /** 0..1 — how far along the journey the plane sits */
  progress?: number;
  tint?: string;
  codeColor?: string;
}) {
  const pct = Math.max(0, Math.min(1, progress));
  return (
    <View style={styles.routeRow}>
      <Text style={[styles.routeCode, { color: codeColor }]}>{from}</Text>
      <View style={styles.routeTrack}>
        <Svg height={4} width="100%" style={styles.routeDashes}>
          <Line
            x1="2"
            y1="2"
            x2="100%"
            y2="2"
            stroke={colors.border}
            strokeWidth={2.4}
            strokeDasharray="0.1, 7"
            strokeLinecap="round"
          />
        </Svg>
        <View style={[styles.routeEndDot, { left: 0, backgroundColor: tint }]} />
        <View style={[styles.routeEndRing, { right: 0, borderColor: tint }]} />
        <View style={[styles.routePlane, { left: `${8 + pct * 78}%` }]}>
          <PlaneSideIcon size={16} color={tint} />
        </View>
      </View>
      <Text style={[styles.routeCode, { color: codeColor }]}>{to}</Text>
    </View>
  );
}

// ─── Ticket tear line (perforation with edge notches) ────────────────────────
export function TicketDivider({
  notch = colors.canvas,
  border = colors.borderSoft,
  inset = 16,
}: {
  /** the canvas color behind the card — the notches "cut into" it */
  notch?: string;
  border?: string;
  /** the parent card's horizontal padding, so the notches reach its edge */
  inset?: number;
}) {
  return (
    <View style={styles.tearRow}>
      <Svg height={2} width="100%" style={{ alignSelf: "center" }}>
        <Line
          x1="10"
          y1="1"
          x2="100%"
          y2="1"
          stroke={border}
          strokeWidth={1.6}
          strokeDasharray="5, 6"
          strokeLinecap="round"
        />
      </Svg>
      <View style={[styles.notch, { left: -(inset + 10), backgroundColor: notch, borderColor: border }]} />
      <View style={[styles.notch, { right: -(inset + 10), backgroundColor: notch, borderColor: border }]} />
    </View>
  );
}

// ─── Ticket field (label over value, printed-form style) ─────────────────────
export function TicketField({
  label,
  value,
  align = "left",
  valueColor = colors.ink,
}: {
  label: string;
  value: string;
  align?: "left" | "right" | "center";
  valueColor?: string;
}) {
  return (
    <View>
      <Text style={[styles.fieldLabel, { textAlign: align }]}>{label.toUpperCase()}</Text>
      <Text style={[styles.fieldValue, { textAlign: align, color: valueColor }]} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

// ─── Barcode strip (deterministic per seed) ───────────────────────────────────
export function Barcode({ seed, height = 22, color = colors.ink }: { seed: number; height?: number; color?: string }) {
  const bars: number[] = [];
  let x = Math.abs(seed) + 7;
  for (let i = 0; i < 28; i++) {
    x = (x * 1103515245 + 12345) % 2147483648;
    bars.push(1 + (x % 3));
  }
  return (
    <View style={[styles.barcode, { height }]} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {bars.map((w, i) => (
        <View key={i} style={{ width: w, height: "100%", backgroundColor: color, opacity: 0.82 }} />
      ))}
    </View>
  );
}

// ─── Uni roundel (replaces the letter-avatar) ────────────────────────────────
/** The airport-code monogram: mono 3-letter code in a bordered roundel. */
export function CodeBadge({
  code,
  size = 44,
  ink = colors.accent,
  bg = colors.accentSoft,
}: {
  code: string;
  size?: number;
  ink?: string;
  bg?: string;
}) {
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.3,
        backgroundColor: bg,
        borderWidth: 1.4,
        borderColor: ink,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Text style={{ fontFamily: fonts.monoBold, fontSize: size * 0.3, color: ink, letterSpacing: 0.5 }}>
        {code}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  stamp: {
    alignSelf: "flex-start",
    borderWidth: 1.6,
    borderRadius: 6,
    paddingVertical: 4,
    paddingHorizontal: 9,
    backgroundColor: "transparent",
  },
  stampText: { fontFamily: fonts.monoBold, fontSize: 10, letterSpacing: 1.2 },

  routeRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  routeCode: { fontFamily: fonts.monoBold, fontSize: 12, letterSpacing: 1 },
  routeTrack: { flex: 1, height: 18, justifyContent: "center" },
  routeDashes: { position: "absolute", left: 0, right: 0 },
  routeEndDot: {
    position: "absolute",
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  routeEndRing: {
    position: "absolute",
    width: 8,
    height: 8,
    borderRadius: 4,
    borderWidth: 2,
    backgroundColor: "#fff",
  },
  routePlane: { position: "absolute", marginLeft: -8 },

  tearRow: { height: 20, justifyContent: "center", marginHorizontal: -1 },
  notch: {
    position: "absolute",
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1,
    top: 1,
  },

  fieldLabel: {
    fontFamily: fonts.mono,
    fontSize: 8.5,
    letterSpacing: 1.1,
    color: colors.textFaintest,
  },
  fieldValue: { fontFamily: fonts.monoBold, fontSize: 13, marginTop: 2 },

  barcode: { flexDirection: "row", alignItems: "stretch", gap: 2 },
});
