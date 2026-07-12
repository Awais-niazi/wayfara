/**
 * 02c — CREATE PASSWORD (onboarding step 3)
 * Rendered by the navigator whenever the session's account has no usable
 * password yet (me.has_password === false) — right after OTP verification.
 * Setting one completes onboarding and drops the user on the dashboard.
 */
import React, { useState } from "react";
import { View, Text, StyleSheet, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, fonts } from "../theme";
import { PrimaryButton, Wordmark } from "../components/ui";
import { Field, FormError } from "../components/form";
import { ApiError, setPassword } from "../lib/api";
import { useAuth } from "../context/AuthContext";

function passwordErrorMessage(err: unknown): string {
  if (err instanceof ApiError && typeof err.body === "object" && err.body !== null) {
    const msgs = (err.body as Record<string, unknown>).password;
    const msg = Array.isArray(msgs) ? msgs[0] : msgs;
    if (typeof msg === "string") return msg;
  }
  return "Couldn't set the password. Please try again.";
}

export default function CreatePasswordScreen() {
  const { me, completePasswordStep, signOut } = useAuth();
  const [password, setPasswordValue] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = password.length >= 8 && !submitting;

  const onSubmit = async () => {
    if (!canSubmit) return;
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await setPassword(password);
      await completePasswordStep(); // flips the navigator to the dashboard
    } catch (err) {
      setError(passwordErrorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Wordmark size={21} />

        <View style={styles.titleBlock}>
          <Text style={styles.title}>Create a password</Text>
          <Text style={styles.subtitle}>
            Your email {me?.email ? <Text style={styles.emailText}>{me.email}</Text> : null} is
            verified. Set a password to secure your account — then your dashboard is ready.
          </Text>
        </View>

        <View style={styles.fields}>
          <Field
            label="Password (8–20 characters)"
            value={password}
            onChangeText={setPasswordValue}
            placeholder="••••••••"
            secure
            maxLength={20}
          />
          <Field
            label="Confirm password"
            value={confirm}
            onChangeText={setConfirm}
            placeholder="••••••••"
            secure
            maxLength={20}
          />
          <FormError message={error} />
        </View>

        <View style={styles.footer}>
          <PrimaryButton
            label={submitting ? "Securing your account…" : "Create password"}
            onPress={onSubmit}
            style={canSubmit ? undefined : styles.btnDisabled}
          />
          <Pressable onPress={signOut}>
            <Text style={styles.altRow}>
              Wrong account? <Text style={styles.altLink}>Start over</Text>
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
  titleBlock: { marginTop: 24 },
  title: { fontFamily: fonts.display, fontSize: 28, letterSpacing: -0.7, color: colors.ink },
  subtitle: {
    marginTop: 8,
    fontFamily: fonts.bodyRegular,
    fontSize: 14.5,
    color: colors.textSubtle,
    lineHeight: 21,
  },
  emailText: { fontFamily: fonts.bodyBold, color: colors.ink },
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
