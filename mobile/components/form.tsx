/**
 * Shared form primitives for the auth/onboarding screens, styled after the
 * "Create Account" mockup fields (warm white inputs, coral focus ring).
 */
import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  type KeyboardTypeOptions,
} from "react-native";

import { colors, fonts } from "../theme";
import { EyeIcon } from "./icons";

export function Field({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  autoCapitalize = "none",
  maxLength,
  secure = false,
  error = null,
  hint,
}: {
  label: string;
  value: string;
  onChangeText: (t: string) => void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  maxLength?: number;
  secure?: boolean;
  error?: string | null;
  hint?: string;
}) {
  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(secure);
  return (
    <View style={styles.group}>
      <Text style={styles.label}>{label}</Text>
      <View
        style={[
          styles.field,
          focused && styles.fieldFocused,
          !!error && styles.fieldError,
        ]}
      >
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.textFaintest}
          keyboardType={keyboardType}
          autoCapitalize={autoCapitalize}
          maxLength={maxLength}
          secureTextEntry={hidden}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={styles.input}
        />
        {secure && (
          <Pressable onPress={() => setHidden((h) => !h)} hitSlop={8}>
            <EyeIcon size={20} color={hidden ? colors.textFaintest : colors.accent} />
          </Pressable>
        )}
      </View>
      {error ? (
        <Text style={styles.fieldErrorText}>{error}</Text>
      ) : hint ? (
        <Text style={styles.fieldHint}>{hint}</Text>
      ) : null}
    </View>
  );
}

/** Single-select chip row for enum fields (study level, intake, stage…). */
export function ChoiceRow<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T | "";
  onChange: (v: T) => void;
}) {
  return (
    <View style={styles.group}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.chipRow}>
        {options.map((opt) => {
          const active = opt.value === value;
          return (
            <Pressable
              key={opt.value}
              onPress={() => onChange(opt.value)}
              style={[styles.chip, active && styles.chipActive]}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>
                {opt.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

/** Inline error banner under a form. */
export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <View style={styles.errorBox}>
      <Text style={styles.errorText}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: 6 },
  label: {
    fontFamily: fonts.bodySemi,
    fontSize: 12.5,
    color: colors.textFaint,
    letterSpacing: 0.2,
  },
  field: {
    height: 52,
    borderWidth: 1,
    borderColor: colors.borderField,
    borderRadius: 14,
    backgroundColor: colors.surface,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 15,
  },
  fieldFocused: { borderWidth: 1.5, borderColor: colors.accent },
  fieldError: { borderWidth: 1.5, borderColor: "#D6543A" },
  fieldErrorText: {
    fontFamily: fonts.bodySemi,
    fontSize: 12,
    color: "#B3402A",
    marginTop: 2,
  },
  fieldHint: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textFaintest,
    marginTop: 2,
  },
  input: {
    flex: 1,
    fontFamily: fonts.body,
    fontSize: 15.5,
    color: colors.ink,
    padding: 0,
  },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.borderField,
    backgroundColor: colors.surface,
  },
  chipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { fontFamily: fonts.bodySemi, fontSize: 13.5, color: colors.textMuted },
  chipTextActive: { color: colors.white },
  errorBox: {
    backgroundColor: "#FCEBE7",
    borderWidth: 1,
    borderColor: "#F3C4B8",
    borderRadius: 12,
    padding: 12,
  },
  errorText: { fontFamily: fonts.bodySemi, fontSize: 13, color: "#B3402A" },
});
