/**
 * 02 — GET STARTED (onboarding form)
 * Form-first onboarding, per the product decision: no register wall. The
 * profile questions + email go to POST /api/onboarding/, which creates a
 * passwordless account, kicks off university matching in the background,
 * and emails a 6-digit code — verified on the next screen.
 *
 * Visually this inherits the "Create Account" mockup language (back button,
 * title block, warm fields, coral CTA); the password/social affordances are
 * dropped because the backend is OTP-only.
 */
import React, { useState } from "react";
import { View, Text, StyleSheet, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts } from "../theme";
import { PrimaryButton, Wordmark } from "../components/ui";
import { Field, ChoiceRow, FormError } from "../components/form";
import { ChevronLeftIcon } from "../components/icons";
import {
  firstErrorMessage,
  submitOnboarding,
  type Intake,
  type LanguageTestStatus,
  type Stage,
  type StudyLevel,
} from "../lib/api";
import {
  EDUCATION_LEVELS,
  FIELDS,
  INTAKES,
  INTAKE_YEARS,
  STAGES,
  TEST_STATUSES,
} from "../lib/profileOptions";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "GetStarted">;

export default function GetStartedScreen({ navigation }: Props) {
  const [email, setEmail] = useState("");
  const [studyLevel, setStudyLevel] = useState<StudyLevel | "">("");
  const [fieldOfStudy, setFieldOfStudy] = useState("");
  const [grades, setGrades] = useState("");
  const [testStatus, setTestStatus] = useState<LanguageTestStatus | "">("");
  const [testScore, setTestScore] = useState("");
  const [budget, setBudget] = useState("");
  const [intake, setIntake] = useState<Intake | "">("");
  const [intakeYear, setIntakeYear] = useState<string | "">("");
  const [stage, setStage] = useState<Stage | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    email.includes("@") && studyLevel !== "" && fieldOfStudy.trim().length > 0 && !submitting;

  const onSubmit = async () => {
    if (!canSubmit) return; // canSubmit already narrows studyLevel !== ""
    setSubmitting(true);
    setError(null);
    try {
      await submitOnboarding({
        email: email.trim(),
        study_level: studyLevel,
        field_of_study: fieldOfStudy.trim(),
        ...(grades.trim() !== "" && { grades: grades.trim() }),
        ...(testStatus !== "" && { language_test_status: testStatus }),
        ...(testStatus === "taken" &&
          testScore.trim() !== "" && { language_test_score: testScore.trim() }),
        ...(budget.trim() !== "" && { budget_eur_per_year: parseInt(budget, 10) }),
        ...(intake !== "" && { intake }),
        ...(intakeYear !== "" && { intake_year: parseInt(intakeYear, 10) }),
        ...(stage !== "" && { stage }),
      });
      navigation.navigate("VerifyOtp", { email: email.trim() });
    } catch (err) {
      setError(firstErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Root of the signed-out stack: show the brand, not a dead back button. */}
        {navigation.canGoBack() ? (
          <Pressable style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeftIcon size={18} color="#4A3D31" />
          </Pressable>
        ) : (
          <Wordmark size={21} />
        )}

        <View style={styles.titleBlock}>
          <Text style={styles.title}>Get started</Text>
          <Text style={styles.subtitle}>
            Tell us about yourself — free to start, and we'll match you to Finnish
            programs while you verify your email.
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
          <ChoiceRow
            label="Last completed education"
            options={EDUCATION_LEVELS}
            value={studyLevel}
            onChange={setStudyLevel}
          />
          <Field
            label="Grades (GPA, percentage, or A-Level grades)"
            value={grades}
            onChangeText={setGrades}
            placeholder="3.4 GPA / 85% / AAB"
            autoCapitalize="none"
          />
          <ChoiceRow
            label="English proficiency test (IELTS/TOEFL)"
            options={TEST_STATUSES}
            value={testStatus}
            onChange={setTestStatus}
          />
          {testStatus === "taken" && (
            <Field
              label="Test score"
              value={testScore}
              onChangeText={setTestScore}
              placeholder="7.0"
              keyboardType="default"
            />
          )}
          <ChoiceRow
            label="Field of study"
            options={FIELDS}
            value={fieldOfStudy}
            onChange={setFieldOfStudy}
          />
          <Field
            label="Budget per year (EUR, optional)"
            value={budget}
            onChangeText={(t) => setBudget(t.replace(/[^0-9]/g, ""))}
            placeholder="18000"
            keyboardType="number-pad"
            maxLength={6}
          />
          <ChoiceRow label="Preferred intake" options={INTAKES} value={intake} onChange={setIntake} />
          {intake !== "" && (
            <ChoiceRow
              label="Intake year"
              options={INTAKE_YEARS}
              value={intakeYear}
              onChange={setIntakeYear}
            />
          )}
          <ChoiceRow label="Where are you now?" options={STAGES} value={stage} onChange={setStage} />
          <FormError message={error} />
        </View>

        <View style={styles.footer}>
          <PrimaryButton
            label={submitting ? "Creating your account…" : "Continue"}
            onPress={onSubmit}
            style={canSubmit ? undefined : styles.btnDisabled}
          />
          <Pressable onPress={() => navigation.navigate("Login")}>
            <Text style={styles.loginRow}>
              Already registered? <Text style={styles.loginLink}>Log in</Text>
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
  fields: { marginTop: 24, gap: 16 },
  footer: { marginTop: 28, gap: 14 },
  btnDisabled: { opacity: 0.45 },
  loginRow: {
    textAlign: "center",
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSubtle,
  },
  loginLink: { color: colors.accent, fontFamily: fonts.bodyBold },
});
