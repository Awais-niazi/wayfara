/**
 * Small shared primitives used across the Wayfara screens. Kept intentionally
 * thin — the screens own their layout; these just standardize the wordmark,
 * buttons and chips so the accent/type stay consistent.
 */
import React from "react";
import { Pressable, Text, View, StyleSheet, ViewStyle, TextStyle } from "react-native";
import { LinearGradient } from "expo-linear-gradient";

import { colors, fonts, radius, shadow } from "../theme";
import { WayfaraPin } from "./icons";
import { PressableScale } from "./motion";

/**
 * The Wayfara logo lockup: the Pin Waypoint mark inside a coral-gradient
 * rounded-square badge, next to the "wayfara" wordmark. `size` drives the
 * wordmark text; the badge scales from it (≈36px badge / 20px pin at size 21,
 * matching the brand header lockup).
 */
export function Wordmark({ size = 21 }: { size?: number }) {
  const badge = Math.round(size * 1.71);
  const badgeRadius = Math.round(badge * 0.3);
  return (
    <View style={styles.wordmarkRow}>
      <LinearGradient
        colors={["#FA6B4F", "#C7502F"]}
        start={{ x: 0.2, y: 0 }}
        end={{ x: 0.8, y: 1 }}
        style={{
          width: badge,
          height: badge,
          borderRadius: badgeRadius,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <WayfaraPin size={Math.round(badge * 0.56)} />
      </LinearGradient>
      <Text style={[styles.wordmarkText, { fontSize: size }]}>wayfara</Text>
    </View>
  );
}

export function PrimaryButton({
  label,
  onPress,
  style,
}: {
  label: string;
  onPress?: () => void;
  style?: ViewStyle;
}) {
  return (
    <PressableScale onPress={onPress} style={[styles.primaryBtn, style]}>
      <Text style={styles.primaryLabel}>{label}</Text>
    </PressableScale>
  );
}

export function GhostButton({
  label,
  onPress,
  style,
  labelStyle,
}: {
  label: string;
  onPress?: () => void;
  style?: ViewStyle;
  labelStyle?: TextStyle;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.ghostBtn, pressed && styles.pressed, style]}
    >
      <Text style={[styles.ghostLabel, labelStyle]}>{label}</Text>
    </Pressable>
  );
}

export function Chip({ label }: { label: string }) {
  return (
    <View style={styles.chip}>
      <Text style={styles.chipText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wordmarkRow: { flexDirection: "row", alignItems: "center", gap: 9 },
  wordmarkText: {
    fontFamily: fonts.display,
    letterSpacing: -0.4,
    color: colors.ink,
  },
  primaryBtn: {
    width: "100%",
    height: 56,
    borderRadius: radius.xl,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    ...shadow.accent,
  },
  primaryLabel: {
    fontFamily: fonts.displaySemi,
    fontSize: 17,
    letterSpacing: -0.2,
    color: colors.white,
  },
  ghostBtn: {
    width: "100%",
    height: 50,
    borderRadius: radius.lg,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "transparent",
  },
  ghostLabel: {
    fontFamily: fonts.bodySemi,
    fontSize: 15,
    color: colors.textMuted,
  },
  chip: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 6,
    paddingHorizontal: 11,
    borderRadius: radius.pill,
  },
  chipText: {
    fontFamily: fonts.bodySemi,
    fontSize: 12,
    color: "#8A7669",
  },
  pressed: { opacity: 0.85 },
});
