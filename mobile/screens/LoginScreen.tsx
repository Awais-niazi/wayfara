/**
 * 02a — LOG IN (returning user)
 * Two ways in, password first since returning users have one (onboarding
 * step 3 sets it):
 *   - email + password → POST /auth/token/  (JWT pair, straight to Home)
 *   - email only       → POST /auth/otp/request/ → VerifyOtp  (passwordless)
 * The backend never reveals whether an account exists, so the CTA copy for
 * the code path stays neutral.
 */
import React, { useState } from "react";
import { View, Text, StyleSheet, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts } from "../theme";
import { PrimaryButton } from "../components/ui";
import { Field, FormError } from "../components/form";
import { ChevronLeftIcon } from "../components/icons";
import { ApiError, loginWithPassword, requestOtp } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Login">;

type Mode = "password" | "otp";

export default function LoginScreen({ navigation }: Props) {
  const { signIn } = useAuth();
  const [mode, setMode] = useState<Mode>("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const emailOk = email.includes("@");
  const canSubmit =
    emailOk && (mode === "otp" || password.length > 0) && !submitting;

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
  };

  const onSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "password") {
        const tokens = await loginWithPassword(email.trim(), password);
        await signIn(tokens); // auth state flips; the navigator swaps stacks
      } else {
        await requestOtp(email.trim());
        navigation.navigate("VerifyOtp", { email: email.trim() });
      }
    } catch (err) {
      if (mode === "password" && err instanceof ApiError && err.status === 401) {
        setError("Wrong email or password. You can log in with an email code instead.");
      } else if (err instanceof Error && err.message === "Network request failed") {
        setError("Can't reach the server. Is the backend running?");
      } else if (mode === "password") {
        setError("Couldn't log you in. Please try again in a minute.");
      } else {
        setError("Couldn't send the code. Please try again in a minute.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const buttonLabel =
    mode === "password"
      ? submitting
        ? "Logging in…"
        : "Log in"
      : submitting
        ? "Sending code…"
        : "Send login code";

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Pressable
          style={styles.backBtn}
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel="Go back"
          hitSlop={8}
        >
          <ChevronLeftIcon size={18} color="#4A3D31" />
        </Pressable>

        <View style={styles.titleBlock}>
          <Text style={styles.title}>Welcome back</Text>
          <Text style={styles.subtitle}>
            {mode === "password"
              ? "Log in with your email and password."
              : "Enter your email and we'll send you a 6-digit login code — no password."}
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
          {mode === "password" && (
            <Field
              label="Password"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secure
              maxLength={20}
            />
          )}
          <FormError message={error} />
        </View>

        <View style={styles.footer}>
          <PrimaryButton
            label={buttonLabel}
            onPress={onSubmit}
            style={canSubmit ? undefined : styles.btnDisabled}
          />
          <Pressable
            onPress={() => switchMode(mode === "password" ? "otp" : "password")}
            accessibilityRole="button"
            hitSlop={6}
          >
            <Text style={styles.altRow}>
              {mode === "password" ? (
                <>
                  Forgot it? <Text style={styles.altLink}>Email me a login code</Text>
                </>
              ) : (
                <>
                  Have a password? <Text style={styles.altLink}>Log in with it</Text>
                </>
              )}
            </Text>
          </Pressable>
          <Pressable onPress={() => navigation.navigate("GetStarted")} hitSlop={6}>
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
    width: 44,
    height: 44,
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
