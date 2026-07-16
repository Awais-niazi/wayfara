/**
 * 06 — PROFILE · VIEW & EDIT
 * Opened from the Home avatar. Loads GET /api/profile/, lets the student edit
 * the same fields the Get Started form collected (plus name/contact details),
 * and PATCHes only what changed. Sign out lives here — at the bottom, visually
 * separated from everything else, behind a confirm.
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";

import { colors, fonts, radius, shadow, spacing } from "../theme";
import { PrimaryButton } from "../components/ui";
import { Field, ChoiceRow, FormError } from "../components/form";
import { CheckIcon } from "../components/icons";
import { TicketDivider, TicketField } from "../components/travel";
import { FadeInUp } from "../components/motion";

import {
  firstErrorMessage,
  getProfile,
  updateProfile,
  type GradeScale,
  type Intake,
  type LanguageTest,
  type LanguageTestStatus,
  type Profile,
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
  TEST_STATUSES,
  budgetError,
  gradeError,
  testScoreError,
} from "../lib/profileOptions";
import { useAuth } from "../context/AuthContext";
import type { TabScreenProps } from "../navigation/types";

type Props = TabScreenProps<"Profile">;

/** Passport MRZ-style line: pure theatre, but it sells the ID page. */
function mrzLine(first: string, last: string): string {
  const clean = (s: string) => s.toUpperCase().replace(/[^A-Z]/g, "");
  return `P<PAK${clean(last) || "WAYFARER"}<<${clean(first) || "STUDENT"}`
    .padEnd(30, "<")
    .slice(0, 30);
}

/** Editable slice of the profile, all as form-friendly strings/enums. */
interface FormState {
  first_name: string;
  last_name: string;
  phone: string;
  home_city: string;
  nationality: string;
  study_level: StudyLevel | "";
  field_of_study: string;
  grade_scale: GradeScale | "";
  grades: string;
  language_test_status: LanguageTestStatus | "";
  language_test: LanguageTest | "";
  language_test_score: string;
  budget: string; // numeric text input; "" = unset
  intake: Intake | "";
  intake_year: string; // "" = unset
  stage: Stage | "";
}

function toForm(p: Profile): FormState {
  return {
    first_name: p.first_name,
    last_name: p.last_name,
    phone: p.phone,
    home_city: p.home_city,
    nationality: p.nationality,
    study_level: p.study_level,
    field_of_study: p.field_of_study,
    grade_scale: p.grade_scale,
    grades: p.grades,
    language_test_status: p.language_test_status,
    language_test: p.language_test,
    language_test_score: p.language_test_score,
    budget: p.budget_eur_per_year === null ? "" : String(p.budget_eur_per_year),
    intake: p.intake,
    intake_year: p.intake_year === null ? "" : String(p.intake_year),
    stage: p.stage,
  };
}

/** The PATCH body: only fields that differ from the loaded profile. */
function diff(form: FormState, base: FormState): Partial<Profile> {
  const patch: Partial<Profile> = {};
  if (form.first_name !== base.first_name) patch.first_name = form.first_name.trim();
  if (form.last_name !== base.last_name) patch.last_name = form.last_name.trim();
  if (form.phone !== base.phone) patch.phone = form.phone.trim();
  if (form.home_city !== base.home_city) patch.home_city = form.home_city.trim();
  if (form.nationality !== base.nationality) patch.nationality = form.nationality.trim();
  if (form.study_level !== base.study_level) patch.study_level = form.study_level;
  if (form.field_of_study !== base.field_of_study) patch.field_of_study = form.field_of_study;
  if (form.grade_scale !== base.grade_scale) patch.grade_scale = form.grade_scale;
  if (form.grades !== base.grades) patch.grades = form.grades.trim();
  if (form.language_test_status !== base.language_test_status)
    patch.language_test_status = form.language_test_status;
  if (form.language_test !== base.language_test) patch.language_test = form.language_test;
  if (form.language_test_score !== base.language_test_score)
    patch.language_test_score = form.language_test_score.trim();
  if (form.budget !== base.budget)
    patch.budget_eur_per_year = form.budget.trim() === "" ? null : parseInt(form.budget, 10);
  if (form.intake !== base.intake) patch.intake = form.intake;
  if (form.intake_year !== base.intake_year)
    patch.intake_year = form.intake_year === "" ? null : parseInt(form.intake_year, 10);
  if (form.stage !== base.stage) patch.stage = form.stage;
  return patch;
}

export default function ProfileScreen(_props: Props) {
  const { signOut } = useAuth();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

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

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => (f ? { ...f, [key]: value } : f));
    setSaved(false);
  };

  const patch = useMemo(
    () => (profile && form ? diff(form, toForm(profile)) : {}),
    [profile, form],
  );
  const dirty = Object.keys(patch).length > 0;

  // Inline semantic errors (mirror the server); block Save while any is present.
  const gradesErr = form ? gradeError(form.grade_scale, form.grades) : null;
  const scoreErr = form ? testScoreError(form.language_test, form.language_test_score) : null;
  const budgetErr = form ? budgetError(form.budget) : null;
  const hasErrors = !!(gradesErr || scoreErr || budgetErr);

  const onSave = async () => {
    if (!dirty || saving || hasErrors) return;
    setSaving(true);
    setSaveError(null);
    try {
      const next = await updateProfile(patch);
      setProfile(next);
      setForm(toForm(next));
      setSaved(true);
    } catch (err) {
      setSaveError(firstErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const onSignOut = () => {
    // RN-web's Alert is a no-op — confirm() is the web equivalent.
    if (Platform.OS === "web") {
      // eslint-disable-next-line no-alert
      if (window.confirm("Sign out?\n\nYou can sign back in with your email and password anytime.")) {
        signOut();
      }
      return;
    }
    Alert.alert("Sign out?", "You can sign back in with your email and password anytime.", [
      { text: "Cancel", style: "cancel" },
      { text: "Sign out", style: "destructive", onPress: signOut },
    ]);
  };

  const displayName =
    profile && (profile.first_name || profile.last_name)
      ? `${profile.first_name} ${profile.last_name}`.trim()
      : profile?.email.split("@")[0] ?? "";

  return (
    <SafeAreaView edges={["top"]} style={styles.root}>
      <FadeInUp>
        <View style={styles.topBar}>
          <Text style={styles.overline}>TRAVELLER ID</Text>
          <Text style={styles.title}>Your profile</Text>
        </View>
      </FadeInUp>

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

      {!loading && !loadError && profile && form && (
        <ScrollView
          contentContainerStyle={styles.body}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* passport ID page — email is the account key, not editable */}
          <FadeInUp delay={60}>
            <View style={styles.identityCard}>
              <View style={styles.passportHead}>
                <Text style={styles.passportHeadText}>WAYFARA · TRAVELLER ID</Text>
                <View style={styles.tierChip}>
                  <Text style={styles.tierChipText}>
                    {profile.tier.toUpperCase()}
                  </Text>
                </View>
              </View>
              <View style={styles.identityRow}>
                <LinearGradient colors={["#FFB43A", colors.accent]} style={styles.avatar}>
                  <Text style={styles.avatarText}>
                    {(displayName || "W").charAt(0).toUpperCase()}
                  </Text>
                </LinearGradient>
                <View style={{ flex: 1 }}>
                  <Text style={styles.identityName} numberOfLines={1}>
                    {displayName || "Add your name"}
                  </Text>
                  <Text style={styles.identityEmail} numberOfLines={1}>{profile.email}</Text>
                </View>
              </View>
              <View style={styles.identityFields}>
                <TicketField label="Nationality" value={profile.nationality || "—"} />
                <TicketField label="Home city" value={profile.home_city || "—"} />
                <TicketField label="Destination" value="FINLAND" align="right" valueColor={colors.accent} />
              </View>
              <TicketDivider inset={16} />
              <Text style={styles.mrz} numberOfLines={1}>
                {mrzLine(profile.first_name, profile.last_name)}
              </Text>
            </View>
          </FadeInUp>

          <Text style={styles.sectionTitle}>About you</Text>
          <View style={styles.fields}>
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
          </View>

          <Text style={styles.sectionTitle}>Your study plan</Text>
          <Text style={styles.sectionSub}>
            Changing these updates your university matches.
          </Text>
          <View style={styles.fields}>
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
          </View>

          {saveError !== null && (
            <View style={{ marginTop: 16 }}>
              <FormError message={saveError} />
            </View>
          )}

          {saved && !dirty && (
            <View style={styles.savedRow}>
              <CheckIcon size={15} />
              <Text style={styles.savedText}>Profile saved</Text>
            </View>
          )}

          <PrimaryButton
            label={saving ? "Saving…" : "Save changes"}
            onPress={onSave}
            style={dirty && !saving ? styles.saveBtn : { ...styles.saveBtn, opacity: 0.4 }}
          />

          {/* destructive, deliberately far from the form actions */}
          <Pressable
            onPress={onSignOut}
            accessibilityRole="button"
            style={({ pressed }) => [styles.signOutBtn, pressed && { opacity: 0.7 }]}
          >
            <Text style={styles.signOutText}>Sign out</Text>
          </Pressable>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },

  topBar: { paddingHorizontal: 20, paddingTop: 14, paddingBottom: 6 },
  overline: { fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: 1.6, color: colors.textFaintest },
  title: { fontFamily: fonts.display, fontSize: 24, letterSpacing: -0.5, color: colors.ink, marginTop: 4 },

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

  body: { paddingHorizontal: 20, paddingBottom: spacing.tabClearance, gap: 0 },

  identityCard: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius["2xl"],
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 12,
    marginTop: 8,
    overflow: "hidden",
    ...shadow.card,
  },
  passportHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  passportHeadText: { fontFamily: fonts.mono, fontSize: 9, letterSpacing: 1.6, color: colors.textFaintest },
  identityRow: { flexDirection: "row", alignItems: "center", gap: 13, marginTop: 12 },
  avatar: { width: 50, height: 50, borderRadius: 15, alignItems: "center", justifyContent: "center" },
  avatarText: { fontFamily: fonts.display, fontSize: 20, color: "#fff" },
  identityName: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.ink },
  identityEmail: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 1 },
  identityFields: { flexDirection: "row", justifyContent: "space-between", marginTop: 14, marginBottom: 2 },
  mrz: { fontFamily: fonts.mono, fontSize: 11, letterSpacing: 2, color: "#C4B29B", marginTop: 2 },
  tierChip: {
    borderWidth: 1.4,
    borderColor: colors.accent,
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 6,
    transform: [{ rotate: "2deg" }],
  },
  tierChipText: { fontFamily: fonts.monoBold, fontSize: 9.5, letterSpacing: 1, color: colors.accent },

  sectionTitle: { fontFamily: fonts.display, fontSize: 18, letterSpacing: -0.3, color: colors.ink, marginTop: 26 },
  sectionSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 2 },
  fields: { gap: 16, marginTop: 14 },

  savedRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, marginTop: 16 },
  savedText: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.success },

  saveBtn: { marginTop: 18 },

  signOutBtn: {
    marginTop: 28,
    height: 52,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: "#F3C4B8",
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  signOutText: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: "#B3402A" },
});
