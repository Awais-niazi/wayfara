/**
 * 02a — LOG IN (returning user)
 * Email entry → POST /api/auth/otp/request/ → VerifyOtp. The backend never
 * reveals whether an account exists, so the CTA copy stays neutral.
 */
import React, { useState } from "react";
import { View, Text, StyleSheet, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts } from "../theme";
import { PrimaryButton } from "../components/ui";
import { Field, FormError } from "../components/form";
import { ChevronLeftIcon } from "../components/icons";
import { requestOtp } from "../lib/api";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Login">;

export default function LoginScreen({ navigation }: Props) {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = email.includes("@") && !submitting;

  const onSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await requestOtp(email.trim());
      navigation.navigate("VerifyOtp", { email: email.trim() });
    } catch (err) {
      setError(
        err instanceof Error && err.message === "Network request failed"
          ? "Can't reach the server. Is the backend running?"
          : "Couldn't send the code. Please try again in a minute.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Pressable style={styles.backBtn} onPress={() => navigation.goBack()}>
          <ChevronLeftIcon size={18} color="#4A3D31" />
        </Pressable>

        <View style={styles.titleBlock}>
          <Text style={styles.title}>Welcome back</Text>
          <Text style={styles.subtitle}>
            Enter your email and we'll send you a 6-digit login code — no password.
          </Text>
        </View>

        <View style={styles.fields}>
          <Field
            label="Email"
            value={email}
            onChangeText={setEmail}
            placeholder="you@example.com"
            keyboardType="email-address"
          />
          <FormError message={error} />
        </View>

        <View style={styles.footer}>
          <PrimaryButton
            label={submitting ? "Sending code…" : "Send login code"}
            onPress={onSubmit}
            style={canSubmit ? undefined : styles.btnDisabled}
          />
          <Pressable onPress={() => navigation.navigate("GetStarted")}>
            <Text style={styles.altRow}>
              New here? <Text style={styles.altLink}>Create a free account</Text>
            </Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.canvas },
  container: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 24, flexGrow: 1 },
  backBtn: {
    width: 42,
    height: 42,
    borderRadius: 13,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  titleBlock: { marginTop: 24 },
  title: { fontFamily: fonts.display, fontSize: 28, letterSpacing: -0.7, color: colors.ink },
  subtitle: {
    marginTop: 8,
    fontFamily: fonts.bodyRegular,
    fontSize: 14.5,
    color: colors.textSubtle,
    lineHeight: 21,
  },
  fields: { marginTop: 26, gap: 16 },
  footer: { marginTop: 28, gap: 14 },
  btnDisabled: { opacity: 0.45 },
  altRow: {
    textAlign: "center",
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSubtle,
  },
  altLink: { color: colors.accent, fontFamily: fonts.bodyBold },
});
