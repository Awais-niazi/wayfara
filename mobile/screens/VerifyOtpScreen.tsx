/**
 * 02b — VERIFY CODE
 * Six-digit email code, verified with Supabase. On the "signup" path it also
 * runs the final onboarding call (storing the profile + starting matching)
 * once the session exists; on the "login" path it just refreshes the session.
 * Either way the root navigator then switches to the Home stack.
 */
import React, { useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  TextInput,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts } from "../theme";
import { PrimaryButton } from "../components/ui";
import { FormError } from "../components/form";
import { ChevronLeftIcon } from "../components/icons";
import { firstErrorMessage, submitOnboarding } from "../lib/api";
import { supabase } from "../lib/supabase";
import { useAuth } from "../context/AuthContext";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "VerifyOtp">;

const CODE_LENGTH = 6;

export default function VerifyOtpScreen({ navigation, route }: Props) {
  const { email, mode, onboarding } = route.params;
  const { refresh } = useAuth();
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resent, setResent] = useState(false);
  const inputRef = useRef<TextInput>(null);

  const digits = code.padEnd(CODE_LENGTH).split("").slice(0, CODE_LENGTH);

  const onVerify = async (value: string) => {
    if (value.length !== CODE_LENGTH || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { error: verifyError } = await supabase.auth.verifyOtp({
        email,
        token: value,
        type: mode === "signup" ? "signup" : "email",
      });
      if (verifyError) {
        setError("Invalid or expired code. Check your email and try again.");
        setCode("");
        setSubmitting(false);
        return;
      }
      // Session now exists. On signup, finish onboarding before flipping to Home.
      if (mode === "signup" && onboarding) {
        await submitOnboarding(onboarding);
      }
      await refresh(); // flips the navigator to the Home stack
    } catch (err) {
      setError(firstErrorMessage(err));
      setSubmitting(false);
    }
  };

  const onChange = (t: string) => {
    const clean = t.replace(/[^0-9]/g, "").slice(0, CODE_LENGTH);
    setCode(clean);
    setError(null);
    if (clean.length === CODE_LENGTH) onVerify(clean);
  };

  const onResend = async () => {
    setResent(true);
    setError(null);
    try {
      if (mode === "signup") {
        await supabase.auth.resend({ type: "signup", email });
      } else {
        await supabase.auth.signInWithOtp({ email, options: { shouldCreateUser: false } });
      }
    } catch {
      // Throttled or offline — the neutral copy below still applies.
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Pressable style={styles.backBtn} onPress={() => navigation.goBack()}>
          <ChevronLeftIcon size={18} color="#4A3D31" />
        </Pressable>

        <View style={styles.titleBlock}>
          <Text style={styles.title}>Check your email</Text>
          <Text style={styles.subtitle}>
            We sent a 6-digit code to{" "}
            <Text style={styles.emailText}>{email}</Text>. It's also your login —
            no password needed.
          </Text>
        </View>

        {/* code boxes over one invisible input, so paste & autofill work */}
        <Pressable style={styles.codeRow} onPress={() => inputRef.current?.focus()}>
          {digits.map((d, i) => (
            <View
              key={i}
              style={[styles.codeBox, i === code.length && styles.codeBoxActive]}
            >
              <Text style={styles.codeDigit}>{d.trim()}</Text>
            </View>
          ))}
          <TextInput
            ref={inputRef}
            value={code}
            onChangeText={onChange}
            keyboardType="number-pad"
            autoFocus
            maxLength={CODE_LENGTH}
            style={styles.hiddenInput}
          />
        </Pressable>

        <FormError message={error} />

        <View style={styles.footer}>
          <PrimaryButton
            label={submitting ? "Verifying…" : "Verify"}
            onPress={() => onVerify(code)}
            style={code.length === CODE_LENGTH && !submitting ? undefined : styles.btnDisabled}
          />
          <Pressable onPress={onResend} disabled={resent}>
            <Text style={styles.resendRow}>
              {resent ? "Code re-sent — check your inbox." : (
                <>Didn't get it? <Text style={styles.resendLink}>Resend code</Text></>
              )}
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
  emailText: { fontFamily: fonts.bodyBold, color: colors.ink },
  codeRow: {
    flexDirection: "row",
    gap: 9,
    marginTop: 30,
    marginBottom: 18,
    position: "relative",
  },
  codeBox: {
    flex: 1,
    height: 58,
    borderWidth: 1,
    borderColor: colors.borderField,
    borderRadius: 14,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  codeBoxActive: { borderWidth: 1.5, borderColor: colors.accent },
  codeDigit: { fontFamily: fonts.monoBold, fontSize: 24, color: colors.ink },
  hiddenInput: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    opacity: 0.01,
    fontSize: 1,
    color: "transparent",
  },
  footer: { marginTop: 18, gap: 14 },
  btnDisabled: { opacity: 0.45 },
  resendRow: {
    textAlign: "center",
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSubtle,
  },
  resendLink: { color: colors.accent, fontFamily: fonts.bodyBold },
});
