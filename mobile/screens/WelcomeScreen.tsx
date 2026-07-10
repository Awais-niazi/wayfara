/**
 * 01 — WELCOME
 * The landing screen: wordmark, hero image slot, value headline, trust chips,
 * and the primary "Create free account" CTA. Faithful to the design mockup.
 */
import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, fonts, radius } from "../theme";
import { Wordmark, PrimaryButton, GhostButton, Chip } from "../components/ui";
import { PinIcon } from "../components/icons";
import { HeroIllustration } from "../components/HeroIllustration";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Welcome">;

const TRUST = ["Aalto", "Helsinki", "LUT", "1,200+ programs"];

export default function WelcomeScreen({ navigation }: Props) {
  return (
    <LinearGradient
      colors={["#FDEDE5", "#FBF4EC", "#FBF6EF"]}
      locations={[0, 0.62, 1]}
      style={styles.flex}
    >
      <SafeAreaView style={styles.flex}>
        <View style={styles.container}>
          <Wordmark size={21} />

          {/* hero */}
          <View style={styles.hero}>
            <HeroIllustration />
            <View style={styles.locationPill}>
              <PinIcon size={12} color="#fff" />
              <Text style={styles.locationText}>Helsinki, Finland</Text>
            </View>
            <View style={styles.savingsBadge}>
              <Text style={styles.savingsBig}>80% less</Text>
              <Text style={styles.savingsSub}>than a €1000 agent</Text>
            </View>
          </View>

          {/* headline */}
          <View style={styles.headlineBlock}>
            <Text style={styles.headline}>Everything an agent does. Minus the €5,000.</Text>
            <Text style={styles.subhead}>
              We match you to Finnish master's programs, then handle admissions, visa,
              flights and housing — start to boarding pass.
            </Text>
          </View>

          <View style={styles.spacer} />

          {/* trust chips */}
          <View style={styles.chipRow}>
            {TRUST.map((t) => (
              <Chip key={t} label={t} />
            ))}
          </View>

          <PrimaryButton
            label="Get Started"
            onPress={() => navigation.navigate("GetStarted")}
          />
          <GhostButton
            label="I already have an account"
            onPress={() => navigation.navigate("Login")}
            style={styles.loginBtn}
          />
        </View>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { flex: 1, paddingHorizontal: 24, paddingTop: 16, paddingBottom: 12 },
  hero: {
    marginTop: 22,
    height: 258,
    borderRadius: radius.card,
    overflow: "hidden",
    backgroundColor: "#EDDCC9",
  },
  locationPill: {
    position: "absolute",
    top: 16,
    left: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "rgba(42,33,25,0.72)",
    paddingVertical: 7,
    paddingHorizontal: 12,
    borderRadius: radius.pill,
  },
  locationText: { fontFamily: fonts.bodySemi, fontSize: 12, color: "#fff" },
  savingsBadge: {
    position: "absolute",
    bottom: 14,
    right: 14,
    backgroundColor: "#fff",
    paddingVertical: 11,
    paddingHorizontal: 14,
    borderRadius: radius.lg,
    shadowColor: "#783C1E",
    shadowOpacity: 0.5,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
    elevation: 4,
  },
  savingsBig: { fontFamily: fonts.display, fontSize: 20, color: colors.accent, lineHeight: 20 },
  savingsSub: { fontFamily: fonts.bodySemi, fontSize: 10.5, color: colors.textFaint, marginTop: 3 },
  headlineBlock: { marginTop: 26 },
  headline: {
    fontFamily: fonts.display,
    fontSize: 31,
    lineHeight: 35,
    letterSpacing: -0.9,
    color: colors.ink,
  },
  subhead: {
    marginTop: 14,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    lineHeight: 23,
    color: colors.textMuted,
  },
  spacer: { flex: 1, minHeight: 16 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 7, marginBottom: 16 },
  loginBtn: { marginTop: 10 },
});
