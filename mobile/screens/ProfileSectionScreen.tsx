/**
 * 06b — PROFILE SECTION · ONE CATEGORY, PUSHED
 * Native settings pattern: a row on the Profile tab pushes this screen with
 * just that category's fields. Owns its own load/edit/save cycle — Save
 * PATCHes the changed fields and pops back; the Profile tab re-reads on
 * focus, so its summaries are fresh the moment this screen closes.
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { colors, fonts, radius, spacing } from "../theme";
import { PrimaryButton } from "../components/ui";
import { Field, ChoiceRow, FormError } from "../components/form";
import {
  CertificateIcon,
  CheckIcon,
  ChevronLeftIcon,
  GradCapIcon,
  IdCardIcon,
  WalletIcon,
  type IconProps,
} from "../components/icons";
import { FadeInUp } from "../components/motion";

import { firstErrorMessage, getProfile, updateProfile, type Profile } from "../lib/api";
import { diff, toForm, type FormState } from "../lib/profileForm";
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
  TEST_STATUSES,
  budgetError,
  gradeError,
  testScoreError,
} from "../lib/profileOptions";
import type { ProfileSectionKey, RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "ProfileSection">;

const SECTION_META: Record<
  ProfileSectionKey,
  { overline: string; title: string; icon: (p: IconProps) => React.JSX.Element; affectsMatches: boolean }
> = {
  personal: { overline: "TRAVELLER ID — PAGE 1", title: "Personal info", icon: IdCardIcon, affectsMatches: false },
  academic: { overline: "TRAVELLER ID — PAGE 2", title: "Academic background", icon: GradCapIcon, affectsMatches: true },
  test: { overline: "TRAVELLER ID — PAGE 3", title: "English test", icon: CertificateIcon, affectsMatches: true },
  plan: { overline: "TRAVELLER ID — PAGE 4", title: "Budget & timeline", icon: WalletIcon, affectsMatches: true },
};

export default function ProfileSectionScreen({ navigation, route }: Props) {
  const { section } = route.params;
  const meta = SECTION_META[section];
  const Icon = meta.icon;

  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setLoadError(false);
    getProfile()
      .then((p) => {
        setProfile(p);
        setForm(toForm(p));
      })
      .catch(() => setLoadError(true))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  const patch = useMemo(
    () => (profile && form ? diff(form, toForm(profile)) : {}),
    [profile, form],
  );
  const dirty = Object.keys(patch).length > 0;

  // Only this section's fields are on screen, so only they can block Save.
  const gradesErr = section === "academic" && form ? gradeError(form.grade_scale, form.grades) : null;
  const scoreErr = section === "test" && form ? testScoreError(form.language_test, form.language_test_score) : null;
  const budgetErr = section === "plan" && form ? budgetError(form.budget) : null;
  const hasErrors = !!(gradesErr || scoreErr || budgetErr);

  const onSave = async () => {
    if (!dirty || saving || hasErrors) return;
    setSaving(true);
    setSaveError(null);
    try {
      await updateProfile(patch);
      navigation.goBack(); // the Profile tab refreshes on focus
    } catch (err) {
      setSaveError(firstErrorMessage(err));
      setSaving(false);
    }
  };

  return (
    <SafeAreaView edges={["top"]} style={styles.root}>
      <View style={styles.topBar}>
        <Pressable
          onPress={navigation.goBack}
          accessibilityRole="button"
          accessibilityLabel="Go back"
          hitSlop={8}
          style={({ pressed }) => [styles.backBtn, pressed && { opacity: 0.7 }]}
        >
          <ChevronLeftIcon size={20} />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.overline}>{meta.overline}</Text>
          <Text style={styles.title}>{meta.title}</Text>
        </View>
        <View style={styles.titleIcon}>
          <Icon size={20} color={colors.accent} />
        </View>
      </View>

      {loading && (
        <View style={styles.loadingBox}>
          <ActivityIndicator color={colors.accent} />
        </View>
      )}

      {loadError && !loading && (
        <Pressable
          onPress={load}
          accessibilityRole="button"
          style={({ pressed }) => [styles.errorBox, pressed && { opacity: 0.7 }]}
        >
          <Text style={styles.errorText}>Couldn't load your profile.</Text>
          <Text style={styles.errorRetry}>Tap to retry</Text>
        </Pressable>
      )}

      {!loading && !loadError && form && (
        <ScrollView
          contentContainerStyle={styles.body}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <FadeInUp>
            {meta.affectsMatches && (
              <Text style={styles.matchesHint}>
                Changing these updates your university matches.
              </Text>
            )}

            <View style={styles.fields}>
              {section === "personal" && (
                <>
                  <Field
                    label="First name"
                    value={form.first_name}
                    onChangeText={(t) => set("first_name", t)}
                    placeholder="Ayesha"
                    autoCapitalize="words"
                  />
                  <Field
                    label="Last name"
                    value={form.last_name}
                    onChangeText={(t) => set("last_name", t)}
                    placeholder="Khan"
                    autoCapitalize="words"
                  />
                  <Field
                    label="Phone"
                    value={form.phone}
                    onChangeText={(t) => set("phone", t)}
                    placeholder="+92 300 1234567"
                    keyboardType="phone-pad"
                  />
                  <Field
                    label="Home city"
                    value={form.home_city}
                    onChangeText={(t) => set("home_city", t)}
                    placeholder="Lahore"
                    autoCapitalize="words"
                  />
                  <Field
                    label="Nationality"
                    value={form.nationality}
                    onChangeText={(t) => set("nationality", t)}
                    placeholder="Pakistani"
                    autoCapitalize="words"
                  />
                </>
              )}

              {section === "academic" && (
                <>
                  <ChoiceRow
                    label="Last completed education"
                    options={EDUCATION_LEVELS}
                    value={form.study_level}
                    onChange={(v) => set("study_level", v)}
                  />
                  <ChoiceRow
                    label="Field of study"
                    options={FIELDS}
                    value={form.field_of_study}
                    onChange={(v) => set("field_of_study", v)}
                  />
                  <ChoiceRow
                    label="Grade type"
                    options={GRADE_SCALES}
                    value={form.grade_scale}
                    onChange={(v) => {
                      set("grade_scale", v);
                      set("grades", "");
                    }}
                  />
                  {form.grade_scale !== "" && (
                    <Field
                      label="Your grade"
                      value={form.grades}
                      onChangeText={(t) => set("grades", t)}
                      placeholder={GRADE_INPUT[form.grade_scale].placeholder}
                      keyboardType={GRADE_INPUT[form.grade_scale].keyboardType}
                      autoCapitalize={form.grade_scale === "letter" ? "characters" : "none"}
                      maxLength={GRADE_INPUT[form.grade_scale].maxLength}
                      error={gradesErr}
                      hint={GRADE_INPUT[form.grade_scale].hint}
                    />
                  )}
                </>
              )}

              {section === "test" && (
                <>
                  <ChoiceRow
                    label="English test"
                    options={TEST_STATUSES}
                    value={form.language_test_status}
                    onChange={(v) => set("language_test_status", v)}
                  />
                  {form.language_test_status === "taken" && (
                    <ChoiceRow
                      label="Which test?"
                      options={LANGUAGE_TESTS}
                      value={form.language_test}
                      onChange={(v) => set("language_test", v)}
                    />
                  )}
                  {form.language_test_status === "taken" && form.language_test !== "" && (
                    <Field
                      label="Your score"
                      value={form.language_test_score}
                      onChangeText={(t) => set("language_test_score", t)}
                      placeholder={TEST_PLACEHOLDER[form.language_test]}
                      keyboardType="decimal-pad"
                      error={scoreErr}
                    />
                  )}
                </>
              )}

              {section === "plan" && (
                <>
                  <Field
                    label="Budget per year (EUR)"
                    value={form.budget}
                    onChangeText={(t) => set("budget", t.replace(/[^0-9]/g, ""))}
                    placeholder="18000"
                    keyboardType="number-pad"
                    maxLength={6}
                    error={budgetErr}
                  />
                  <ChoiceRow
                    label="Target intake"
                    options={INTAKES}
                    value={form.intake}
                    onChange={(v) => set("intake", v)}
                  />
                  <ChoiceRow
                    label="Intake year"
                    options={INTAKE_YEARS}
                    value={form.intake_year}
                    onChange={(v) => set("intake_year", v)}
                  />
                  <ChoiceRow
                    label="Where are you in the journey?"
                    options={STAGES}
                    value={form.stage}
                    onChange={(v) => set("stage", v)}
                  />
                </>
              )}
            </View>

            {saveError !== null && (
              <View style={{ marginTop: 16 }}>
                <FormError message={saveError} />
              </View>
            )}

            <PrimaryButton
              label={saving ? "Saving…" : "Save changes"}
              icon={<CheckIcon size={16} color="#fff" />}
              onPress={onSave}
              style={dirty && !saving && !hasErrors ? styles.saveBtn : { ...styles.saveBtn, opacity: 0.4 }}
            />
          </FadeInUp>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },

  topBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 6,
  },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  overline: { fontFamily: fonts.mono, fontSize: 9, letterSpacing: 1.6, color: colors.textFaintest },
  title: { fontFamily: fonts.display, fontSize: 20, letterSpacing: -0.4, color: colors.ink, marginTop: 2 },
  titleIcon: {
    width: 40,
    height: 40,
    borderRadius: 13,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
  },

  loadingBox: { paddingVertical: 80, alignItems: "center" },
  errorBox: {
    marginTop: 24,
    marginHorizontal: 20,
    backgroundColor: "#FCEBE7",
    borderWidth: 1,
    borderColor: "#F3C4B8",
    borderRadius: radius["2xl"],
    padding: 18,
    alignItems: "center",
    gap: 4,
  },
  errorText: { fontFamily: fonts.bodySemi, fontSize: 13.5, color: "#B3402A", textAlign: "center" },
  errorRetry: { fontFamily: fonts.bodyBold, fontSize: 13, color: colors.accent },

  body: { paddingHorizontal: 20, paddingBottom: spacing.tabClearance },
  matchesHint: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12.5,
    color: colors.textFaint,
    marginTop: 8,
  },
  fields: { gap: 16, marginTop: 14 },
  saveBtn: { marginTop: 22 },
});
