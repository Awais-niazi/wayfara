/**
 * 02 — CREATE ACCOUNT
 * Social (Apple/Google) sign-up, an "or with email" divider, and name/email/
 * password fields. The fields are presentational here (static values from the
 * mockup); wiring them to the OTP backend is a follow-up.
 */
import React, { useState } from "react";
import { View, Text, StyleSheet, Pressable, TextInput, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, fonts, radius } from "../theme";
import { PrimaryButton } from "../components/ui";
import { ChevronLeftIcon, AppleIcon, GoogleDot, EyeIcon } from "../components/icons";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "CreateAccount">;

function Field({
  label,
  value,
  onChangeText,
  placeholder,
  focused,
  secure,
  keyboardType,
}: {
  label: string;
  value: string;
  onChangeText: (t: string) => void;
  placeholder?: string;
  focused?: boolean;
  secure?: boolean;
  keyboardType?: "email-address" | "default";
}) {
  return (
    <View style={styles.fieldGroup}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={[styles.field, focused && styles.fieldFocused]}>
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.textFaintest}
          secureTextEntry={secure}
          autoCapitalize={keyboardType === "email-address" ? "none" : "words"}
          keyboardType={keyboardType}
          style={styles.fieldInput}
        />
        {secure && <EyeIcon size={20} color={colors.textFaintest} />}
      </View>
    </View>
  );
}

export default function CreateAccountScreen({ navigation }: Props) {
  const [name, setName] = useState("Aarav Menon");
  const [email, setEmail] = useState("aarav.menon@email.com");
  const [password, setPassword] = useState("password12");

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Pressable style={styles.backBtn} onPress={() => navigation.goBack()}>
          <ChevronLeftIcon size={18} color="#4A3D31" />
        </Pressable>

        <View style={styles.titleBlock}>
          <Text style={styles.title}>Create your account</Text>
          <Text style={styles.subtitle}>Free to start — no card, no commitment.</Text>
        </View>

        {/* social */}
        <Pressable style={[styles.socialBtn, styles.appleBtn]}>
          <AppleIcon size={17} color="#fff" />
          <Text style={styles.appleLabel}>Continue with Apple</Text>
        </Pressable>
        <Pressable style={[styles.socialBtn, styles.googleBtn]}>
          <GoogleDot size={19} />
          <Text style={styles.googleLabel}>Continue with Google</Text>
        </Pressable>

        {/* divider */}
        <View style={styles.divider}>
          <View style={styles.rule} />
          <Text style={styles.dividerText}>or with email</Text>
          <View style={styles.rule} />
        </View>

        {/* fields */}
        <View style={styles.fields}>
          <Field label="Full name" value={name} onChangeText={setName} />
          <Field
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            focused
          />
          <Field label="Password" value={password} onChangeText={setPassword} secure />
        </View>

        <View style={styles.spacer} />

        <Text style={styles.terms}>
          By continuing you agree to Wayfara's <Text style={styles.link}>Terms</Text> &{" "}
          <Text style={styles.link}>Privacy Policy</Text>.
        </Text>

        <PrimaryButton label="Continue" onPress={() => navigation.navigate("Home")} />
        <Text style={styles.loginRow}>
          Already registered? <Text style={styles.loginLink}>Log in</Text>
        </Text>
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
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  titleBlock: { marginTop: 24 },
  title: { fontFamily: fonts.display, fontSize: 28, letterSpacing: -0.7, color: colors.ink },
  subtitle: { marginTop: 8, fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textSubtle },
  socialBtn: {
    width: "100%",
    height: 54,
    borderRadius: radius.lg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
  },
  appleBtn: { marginTop: 26, backgroundColor: "#221B15" },
  appleLabel: { fontFamily: fonts.bodySemi, fontSize: 15.5, color: "#fff" },
  googleBtn: {
    marginTop: 11,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#E6D6C3",
  },
  googleLabel: { fontFamily: fonts.bodySemi, fontSize: 15.5, color: colors.ink },
  divider: { flexDirection: "row", alignItems: "center", gap: 12, marginVertical: 22 },
  rule: { flex: 1, height: 1, backgroundColor: "#EBDBC8" },
  dividerText: { fontFamily: fonts.bodySemi, fontSize: 12, color: colors.textFaintest, letterSpacing: 0.3 },
  fields: { gap: 14 },
  fieldGroup: { gap: 6 },
  fieldLabel: { fontFamily: fonts.bodySemi, fontSize: 12.5, color: colors.textFaint, letterSpacing: 0.2 },
  field: {
    height: 52,
    borderWidth: 1,
    borderColor: "#E6D6C3",
    borderRadius: 14,
    backgroundColor: "#fff",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 15,
  },
  fieldFocused: {
    borderWidth: 1.5,
    borderColor: colors.accent,
  },
  fieldInput: {
    flex: 1,
    fontFamily: fonts.body,
    fontSize: 15.5,
    color: colors.ink,
    padding: 0,
  },
  spacer: { flex: 1, minHeight: 20 },
  terms: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textFaintest,
    lineHeight: 18,
    textAlign: "center",
    marginBottom: 14,
  },
  link: { color: colors.accent, fontFamily: fonts.bodySemi },
  loginRow: {
    textAlign: "center",
    marginTop: 14,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSubtle,
  },
  loginLink: { color: colors.accent, fontFamily: fonts.bodyBold },
});
