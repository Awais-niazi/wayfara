/**
 * 02 — GET STARTED (onboarding wizard)
 * Form-first onboarding, per the product decision: no register wall. The same
 * profile questions as before, but split into short, progress-tracked steps so
 * the form doesn't read as one long intimidating page. All answers go to
 * POST /api/v1/onboarding/ on the final step, which creates a passwordless
 * account, kicks off university matching in the background, and emails a
 * 6-digit code — verified on the next screen.
 *
 * Steps: About you → Your education → Language → Study plan. The two required
 * fields (education level + field of study) live in step 2; steps 3–4 are
 * optional and only sharpen the match, so their "Continue" is never gated.
 */
import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  Animated,
  Easing,
  BackHandler,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts } from "../theme";
import { PrimaryButton, Wordmark } from "../components/ui";
import { Field, ChoiceRow, FormError } from "../components/form";
import { ChevronLeftIcon } from "../components/icons";
import {
  firstErrorMessage,
  submitOnboarding,
  type GradeScale,
  type Intake,
  type LanguageTest,
  type LanguageTestStatus,
  type Stage,
  type StudyLevel,
} from "../lib/api";
import {
  EDUCATION_LEVELS,
  FIELDS,
  GRADE_INPUT,
  GRADE_SCALES,
  INTAKES,
  INTAKE_YEARS,
  LANGUAGE_TESTS,
  STAGES,
  TEST_PLACEHOLDER,
  TEST_RANGE_HINT,
  TEST_STATUSES,
  budgetError,
  gradeError,
  testScoreError,
} from "../lib/profileOptions";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "GetStarted">;

const STEPS = [
  {
    key: "about",
    title: "About you",
    subtitle: "Free to start — we'll match you while you verify your email.",
  },
  {
    key: "education",
    title: "Your education",
    subtitle: "This decides which programmes you're eligible for.",
  },
  {
    key: "language",
    title: "Language",
    subtitle: "Optional, but it sharpens your matches.",
  },
  {
    key: "plan",
    title: "Study plan",
    subtitle: "Optional — budget and intake help us rank your fits.",
  },
] as const;

const TOTAL = STEPS.length;

export default function GetStartedScreen({ navigation }: Props) {
  const [step, setStep] = useState(0);

  const [email, setEmail] = useState("");
  const [studyLevel, setStudyLevel] = useState<StudyLevel | "">("");
  const [fieldOfStudy, setFieldOfStudy] = useState("");
  const [gradeScale, setGradeScale] = useState<GradeScale | "">("");
  const [grades, setGrades] = useState("");
  const [testStatus, setTestStatus] = useState<LanguageTestStatus | "">("");
  const [languageTest, setLanguageTest] = useState<LanguageTest | "">("");
  const [testScore, setTestScore] = useState("");
  const [budget, setBudget] = useState("");
  const [intake, setIntake] = useState<Intake | "">("");
  const [intakeYear, setIntakeYear] = useState<string | "">("");
  const [stage, setStage] = useState<Stage | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Directional slide on step change: forward enters from the right, back from
  // the left, so the motion reinforces where you are in the flow.
  const anim = useRef(new Animated.Value(1)).current;
  const dir = useRef(1);

  const isLast = step === TOTAL - 1;

  // Inline semantic errors (mirror the server). Empty optional values pass.
  const gradesErr = gradeError(gradeScale, grades);
  const scoreErr = testScoreError(languageTest, testScore);
  const budgetErr = budgetError(budget);

  const stepValid = (s: number) => {
    if (s === 0) return email.trim().includes("@");
    // Required education fields + no illogical grade value.
    if (s === 1) return studyLevel !== "" && fieldOfStudy.trim().length > 0 && !gradesErr;
    if (s === 2) return !scoreErr; // language is optional but must be sane
    return !budgetErr; // study plan is optional but must be sane
  };
  const canAdvance = stepValid(step) && !submitting;

  const goTo = (next: number) => {
    dir.current = next > step ? 1 : -1;
    setStep(next);
    anim.setValue(0);
    Animated.timing(anim, {
      toValue: 1,
      duration: 220,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  };

  const goBack = () => {
    if (step === 0) navigation.goBack();
    else goTo(step - 1);
  };

  // Android hardware back walks the wizard, not out of it (no-op on web/iOS).
  useEffect(() => {
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      if (step > 0) {
        goTo(step - 1);
        return true;
      }
      return false;
    });
    return () => sub.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  const onSubmit = async () => {
    if (!stepValid(0) || !stepValid(1) || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitOnboarding({
        email: email.trim(),
        study_level: studyLevel as StudyLevel,
        field_of_study: fieldOfStudy.trim(),
        ...(grades.trim() !== "" && { grade_scale: gradeScale as GradeScale, grades: grades.trim() }),
        ...(testStatus !== "" && { language_test_status: testStatus }),
        ...(testStatus === "taken" &&
          languageTest !== "" && { language_test: languageTest }),
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

  const onPrimary = () => {
    if (!canAdvance) return;
    if (isLast) onSubmit();
    else goTo(step + 1);
  };

  const translateX = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [dir.current * 26, 0],
  });

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Header: back walks the wizard; brand only when this is the stack root. */}
        {step === 0 && !navigation.canGoBack() ? (
          <Wordmark size={21} />
        ) : (
          <Pressable
            style={styles.backBtn}
            onPress={goBack}
            accessibilityRole="button"
            accessibilityLabel={step === 0 ? "Go back" : "Previous step"}
            hitSlop={8}
          >
            <ChevronLeftIcon size={18} color="#4A3D31" />
          </Pressable>
        )}

        {/* Progress */}
        <View style={styles.stepperRow}>
          {STEPS.map((s, i) => (
            <View
              key={s.key}
              style={[styles.segment, i <= step ? styles.segmentOn : styles.segmentOff]}
            />
          ))}
        </View>
        <Text style={styles.stepMeta}>
          Step {step + 1} of {TOTAL}
        </Text>

        <View style={styles.titleBlock}>
          <Text style={styles.title}>{STEPS[step].title}</Text>
          <Text style={styles.subtitle}>{STEPS[step].subtitle}</Text>
        </View>

        <Animated.View style={[styles.fields, { opacity: anim, transform: [{ translateX }] }]}>
          {step === 0 && (
            <>
              <Field
                label="Email"
                value={email}
                onChangeText={setEmail}
                placeholder="you@example.com"
                keyboardType="email-address"
              />
              <ChoiceRow
                label="Where are you now?"
                options={STAGES}
                value={stage}
                onChange={setStage}
              />
            </>
          )}

          {step === 1 && (
            <>
              <ChoiceRow
                label="Last completed education"
                options={EDUCATION_LEVELS}
                value={studyLevel}
                onChange={setStudyLevel}
              />
              <ChoiceRow
                label="Field of study"
                options={FIELDS}
                value={fieldOfStudy}
                onChange={setFieldOfStudy}
              />
              <ChoiceRow
                label="Grade type (optional)"
                options={GRADE_SCALES}
                value={gradeScale}
                onChange={(v) => {
                  setGradeScale(v);
                  setGrades(""); // clear so an old value can't linger on a new scale
                }}
              />
              {gradeScale !== "" && (
                <Field
                  label="Your grade"
                  value={grades}
                  onChangeText={setGrades}
                  placeholder={GRADE_INPUT[gradeScale].placeholder}
                  keyboardType={GRADE_INPUT[gradeScale].keyboardType}
                  autoCapitalize={gradeScale === "letter" ? "characters" : "none"}
                  maxLength={GRADE_INPUT[gradeScale].maxLength}
                  error={gradesErr}
                  hint={GRADE_INPUT[gradeScale].hint}
                />
              )}
            </>
          )}

          {step === 2 && (
            <>
              <ChoiceRow
                label="English proficiency test"
                options={TEST_STATUSES}
                value={testStatus}
                onChange={setTestStatus}
              />
              {testStatus === "taken" && (
                <ChoiceRow
                  label="Which test?"
                  options={LANGUAGE_TESTS}
                  value={languageTest}
                  onChange={setLanguageTest}
                />
              )}
              {testStatus === "taken" && languageTest !== "" && (
                <Field
                  label="Your score"
                  value={testScore}
                  onChangeText={setTestScore}
                  placeholder={TEST_PLACEHOLDER[languageTest]}
                  keyboardType="decimal-pad"
                  error={scoreErr}
                  hint={`Range ${TEST_RANGE_HINT[languageTest]}`}
                />
              )}
            </>
          )}

          {step === 3 && (
            <>
              <Field
                label="Budget per year (EUR, optional)"
                value={budget}
                onChangeText={(t) => setBudget(t.replace(/[^0-9]/g, ""))}
                placeholder="18000"
                keyboardType="number-pad"
                maxLength={6}
                error={budgetErr}
                hint="Leave blank for tuition-free only"
              />
              <ChoiceRow
                label="Preferred intake"
                options={INTAKES}
                value={intake}
                onChange={setIntake}
              />
              {intake !== "" && (
                <ChoiceRow
                  label="Intake year"
                  options={INTAKE_YEARS}
                  value={intakeYear}
                  onChange={setIntakeYear}
                />
              )}
            </>
          )}

          {isLast && <FormError message={error} />}
        </Animated.View>

        <View style={styles.footer}>
          <PrimaryButton
            label={
              isLast
                ? submitting
                  ? "Creating your account…"
                  : "Create account"
                : "Continue"
            }
            onPress={onPrimary}
            style={canAdvance ? undefined : styles.btnDisabled}
          />
          {step === 0 && (
            <Pressable onPress={() => navigation.navigate("Login")} hitSlop={6}>
              <Text style={styles.loginRow}>
                Already registered? <Text style={styles.loginLink}>Log in</Text>
              </Text>
            </Pressable>
          )}
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

  stepperRow: { flexDirection: "row", gap: 7, marginTop: 22 },
  segment: { flex: 1, height: 6, borderRadius: 3 },
  segmentOn: { backgroundColor: colors.accent },
  segmentOff: { backgroundColor: "#EEE2D2" },
  stepMeta: {
    marginTop: 10,
    fontFamily: fonts.bodySemi,
    fontSize: 12.5,
    color: colors.textFaint,
    letterSpacing: 0.2,
  },

  titleBlock: { marginTop: 14 },
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
