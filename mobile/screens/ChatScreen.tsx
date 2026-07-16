/**
 * 09 — CHAT (advisor console placeholder)
 * Advisor chat ships with the advisor console phase. Until then the tab is a
 * proper destination, not a dead button: a departures-board "gate not open"
 * state in the travel-doc voice.
 */
import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, fonts, radius, shadow, spacing } from "../theme";
import { ChatIcon } from "../components/icons";
import { RouteLine, Stamp } from "../components/travel";
import { FadeInUp } from "../components/motion";


export default function ChatScreen() {
  return (
    <SafeAreaView edges={["top"]} style={styles.root}>
      <View style={styles.center}>
        <FadeInUp>
          <View style={styles.card}>
            <View style={styles.iconBadge}>
              <ChatIcon size={26} color={colors.accent} />
            </View>
            <Text style={styles.title}>Advisor chat</Text>
            <Text style={styles.text}>
              A real human (plus our AI) on the other end for visa questions,
              SOP reviews and everything in between. We're staffing the desk now.
            </Text>
            <View style={styles.routeBox}>
              <RouteLine from="YOU" to="ADV" progress={0.55} />
            </View>
            <Stamp label="Gate opens soon" ink={colors.warningInkSoft} tilt={-2.5} style={{ alignSelf: "center", marginTop: 18 }} />
          </View>
        </FadeInUp>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },
  center: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 24,
    paddingBottom: spacing.tabClearance,
  },
  card: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.card,
    padding: 26,
    alignItems: "center",
    ...shadow.card,
  },
  iconBadge: {
    width: 56,
    height: 56,
    borderRadius: 18,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { fontFamily: fonts.display, fontSize: 19, color: colors.ink, marginTop: 14 },
  text: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13.5,
    lineHeight: 20,
    color: colors.textFaint,
    textAlign: "center",
    marginTop: 8,
  },
  routeBox: { alignSelf: "stretch", marginTop: 22 },
});
