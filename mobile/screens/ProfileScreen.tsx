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
import {
  CertificateIcon,
  CheckIcon,
  ChevronRightIcon,
  GradCapIcon,
  IdCardIcon,
  LogOutIcon,
  WalletIcon,
} from "../components/icons";
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

/** Label for a value from a {value, label} options array. */
const labelOf = (options: { value: string; label: string }[], value: string) =>
  options.find((o) => o.value === value)?.label ?? "";

type SectionKey = "personal" | "academic" | "test" | "plan";

/** One collapsible settings category: icon tile + title + a live summary of
 *  its values while closed. Only one section is open at a time — the tidy
 *  state is the default state. */
function Section({
  icon,
  title,
  summary,
  open,
  onToggle,
  hasError,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  summary: string;
  open: boolean;
  onToggle: () => void;
  hasError?: boolean;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Pressable
        onPress={onToggle}
        accessibilityRole="button"
        accessibilityLabel={`${title}, ${open ? "collapse" : "expand"}`}
        style={({ pressed }) => [styles.sectionHead, pressed && { opacity: 0.75 }]}
      >
        <View style={styles.sectionIcon}>{icon}</View>
        <View style={{ flex: 1 }}>
          <Text style={styles.sectionHeadTitle}>{title}</Text>
          <Text style={styles.sectionHeadSummary} numberOfLines={1}>
            {summary}
          </Text>
        </View>
        {hasError && <View style={styles.errorDot} />}
        <View style={{ transform: [{ rotate: open ? "90deg" : "0deg" }] }}>
          <ChevronRightIcon size={17} color={colors.textFaintest} />
        </View>
      </Pressable>
      {open && <View style={styles.sectionBody}>{children}</View>}
    </View>
  );
}

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
  // Accordion: everything starts folded — the tidy state is the default.
  const [openSection, setOpenSection] = useState<SectionKey | null>(null);
  const toggle = (key: SectionKey) =>
    setOpenSection((current) => (current === key ? null : key));

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

  // A blocked save must show WHERE the problem is, not just refuse.
  const erroredSection: SectionKey | null = gradesErr
    ? "academic"
    : scoreErr
      ? "test"
      : budgetErr
        ? "plan"
        : null;

  const onSave = async () => {
    if (hasErrors && erroredSection) {
      setOpenSection(erroredSection);
      return;
    }
    if (!dirty || saving) return;
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

          {/* Categories, all folded by default — headers carry a live summary
              so the closed state still reads at a glance. */}
          <View style={styles.sections}>
            <Section
              icon={<IdCardIcon size={20} color={colors.accent} />}
              title="Personal info"
              summary={
                [displayName, form.phone, form.home_city].filter(Boolean).join(" · ") ||
                "Name, contact & nationality"
              }
              open={openSection === "personal"}
              onToggle={() => toggle("personal")}
            >
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
            </Section>

            <Section
              icon={<GradCapIcon size={20} color={colors.accent} />}
              title="Academic background"
              summary={
                [labelOf(EDUCATION_LEVELS, form.study_level), labelOf(FIELDS, form.field_of_study)]
                  .filter(Boolean)
                  .join(" · ") || "Education, field & grades"
              }
              open={openSection === "academic"}
              onToggle={() => toggle("academic")}
              hasError={!!gradesErr}
            >
              <Text style={styles.matchesHint}>
                Changing these updates your university matches.
              </Text>
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
            </Section>

            <Section
              icon={<CertificateIcon size={20} color={colors.accent} />}
              title="English test"
              summary={
                form.language_test_status === "taken" && form.language_test !== ""
                  ? `${labelOf(LANGUAGE_TESTS, form.language_test)}${form.language_test_score ? ` · ${form.language_test_score}` : ""}`
                  : labelOf(TEST_STATUSES, form.language_test_status) || "IELTS, TOEFL, PTE or Duolingo"
              }
              open={openSection === "test"}
              onToggle={() => toggle("test")}
              hasError={!!scoreErr}
            >
              <Text style={styles.matchesHint}>
                Changing these updates your university matches.
              </Text>
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
            </Section>

            <Section
              icon={<WalletIcon size={20} color={colors.accent} />}
              title="Budget & timeline"
              summary={
                [
                  form.budget
                    ? `€${parseInt(form.budget, 10).toLocaleString("en-US")}/yr`
                    : "Tuition-free only",
                  [labelOf(INTAKES, form.intake), form.intake_year].filter(Boolean).join(" "),
                ]
                  .filter(Boolean)
                  .join(" · ")
              }
              open={openSection === "plan"}
              onToggle={() => toggle("plan")}
              hasError={!!budgetErr}
            >
              <Text style={styles.matchesHint}>
                Changing these updates your university matches.
              </Text>
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
            </Section>
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
            icon={<CheckIcon size={16} color="#fff" />}
            onPress={onSave}
            style={dirty && !saving ? styles.saveBtn : { ...styles.saveBtn, opacity: 0.4 }}
          />

          {/* destructive, deliberately far from the form actions */}
          <Pressable
            onPress={onSignOut}
            accessibilityRole="button"
            style={({ pressed }) => [styles.signOutBtn, pressed && { opacity: 0.7 }]}
          >
            <LogOutIcon size={17} />
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

  sections: { marginTop: 22, gap: 12 },
  section: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius["2xl"],
    overflow: "hidden",
    ...shadow.card,
  },
  sectionHead: {
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    paddingHorizontal: 14,
    paddingVertical: 14,
    minHeight: 64,
  },
  sectionIcon: {
    width: 40,
    height: 40,
    borderRadius: 13,
    backgroundColor: colors.accentSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  sectionHeadTitle: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  sectionHeadSummary: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textFaint,
    marginTop: 2,
  },
  errorDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.accent },
  sectionBody: {
    gap: 16,
    paddingHorizontal: 14,
    paddingBottom: 18,
    paddingTop: 4,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSoft,
  },
  matchesHint: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textFaint,
    marginTop: 10,
  },

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
    flexDirection: "row",
    gap: 9,
    alignItems: "center",
    justifyContent: "center",
  },
  signOutText: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: "#B3402A" },
});
