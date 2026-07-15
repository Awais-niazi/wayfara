/**
 * 02a — LOG IN (returning user)
 * Two ways in via Supabase, password first:
 *   - email + password → supabase.auth.signInWithPassword → Home
 *   - email only       → supabase.auth.signInWithOtp → VerifyOtp (passwordless)
 * shouldCreateUser is false on the code path so logging in never silently
 * creates an account.
 */
import React, { useState } from "react";
import { View, Text, StyleSheet, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts } from "../theme";
import { PrimaryButton } from "../components/ui";
import { Field, FormError } from "../components/form";
import { ChevronLeftIcon } from "../components/icons";
import { isSupabaseConfigured, supabase } from "../lib/supabase";
import { useAuth } from "../context/AuthContext";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Login">;

type Mode = "password" | "otp";

export default function LoginScreen({ navigation }: Props) {
  const { refresh } = useAuth();
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
    if (!isSupabaseConfigured) {
      setError("Login isn't available yet — Supabase isn't configured.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "password") {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (signInError) {
          setError("Wrong email or password. You can log in with an email code instead.");
          return;
        }
        await refresh(); // auth state flips; the navigator swaps stacks
      } else {
        const { error: otpError } = await supabase.auth.signInWithOtp({
          email: email.trim(),
          options: { shouldCreateUser: false },
        });
        if (otpError) {
          setError("Couldn't send the code. Please try again in a minute.");
          return;
        }
        navigation.navigate("VerifyOtp", { email: email.trim(), mode: "login" });
      }
    } catch {
      setError("Can't reach the server. Please try again in a minute.");
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
