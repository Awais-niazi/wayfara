/**
 * 09 — APPLICATION WORKSPACE
 * One application, end to end: status stepper, the programme's document
 * checklist (upload/view per item), the motivation-letter editor with static
 * guidance, and the Studyinfo hand-off (Wayfara can't submit on the student's
 * behalf — Studyinfo.fi is Finland's official portal).
 */
import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
  Linking,
  Platform,
  TextInput,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import * as DocumentPicker from "expo-document-picker";

import { colors, fonts, radius, shadow } from "../theme";
import { ChevronLeftIcon, CheckIcon, GlobeIcon, UploadIcon } from "../components/icons";
import { Stamp } from "../components/travel";
import {
  documentDownloadUrl,
  firstErrorMessage,
  getApplication,
  setApplicationStatus,
  updateApplication,
  uploadDocument,
  type ApplicationDetail,
  type ApplicationStatus,
  type ChecklistItem,
} from "../lib/api";
import { supabase } from "../lib/supabase";
import { STATUS_META } from "./ApplicationsScreen";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "ApplicationDetail">;

// The happy-path ladder shown as the stepper; other outcomes live under "more".
const LADDER: ApplicationStatus[] = [
  "shortlisted",
  "in_progress",
  "submitted",
  "offer_received",
  "place_confirmed",
];

const NEXT_LABEL: Record<string, string> = {
  shortlisted: "Start preparing",
  in_progress: "Mark as submitted on Studyinfo",
  submitted: "I received an offer",
  offer_received: "I confirmed my study place",
};

const SOP_TIPS = [
  "Name THIS programme and university — a letter that could go anywhere goes nowhere.",
  "Specific beats general: one real project you built says more than five adjectives.",
  "Answer 'why Finland, why now' in one honest paragraph.",
  "Skip the clichés — 'since childhood', 'esteemed institution', 'quench my thirst for knowledge'.",
  "500–700 words. Admissions tutors read hundreds of these.",
];

/** RN-web's Alert is a no-op — confirm() is the web equivalent. */
function confirmDialog(title: string, message: string, onConfirm: () => void) {
  if (Platform.OS === "web") {
    // eslint-disable-next-line no-alert
    if (window.confirm(`${title}\n\n${message}`)) onConfirm();
    return;
  }
  Alert.alert(title, message, [
    { text: "Cancel", style: "cancel" },
    { text: "Confirm", onPress: onConfirm },
  ]);
}

export default function ApplicationDetailScreen({ navigation, route }: Props) {
  const { id } = route.params;
  const [app, setApp] = useState<ApplicationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState<string | null>(null); // doc_type being uploaded / "status" / "sop"
  const [actionError, setActionError] = useState<string | null>(null);
  const [sop, setSop] = useState("");
  const [sopDirty, setSopDirty] = useState(false);
  const [reference, setReference] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const detail = await getApplication(id);
      setApp(detail);
      setSop(detail.motivation_letter);
      setReference(detail.studyinfo_reference);
      setSopDirty(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const advance = (next: ApplicationStatus) => {
    const meta = STATUS_META[next];
    confirmDialog("Update status?", `Move this application to "${meta.label}".`, async () => {
      setBusy("status");
      setActionError(null);
      try {
        setApp(await setApplicationStatus(id, next));
      } catch (err) {
        setActionError(firstErrorMessage(err));
      } finally {
        setBusy(null);
      }
    });
  };

  const pickAndUpload = async (item: ChecklistItem) => {
    setActionError(null);
    const result = await DocumentPicker.getDocumentAsync({
      type: ["application/pdf", "image/jpeg", "image/png"],
      copyToCacheDirectory: true,
    });
    if (result.canceled || result.assets.length === 0) return;
    const asset = result.assets[0];
    setBusy(item.doc_type);
    try {
      await uploadDocument(item.doc_type, {
        uri: asset.uri,
        name: asset.name,
        mimeType: asset.mimeType,
      });
      await load(); // checklist flips
    } catch (err) {
      setActionError(firstErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const viewDocument = async (documentId: number) => {
    // The download endpoint needs the bearer token; fetch it ourselves, then
    // open the result (R2: the redirect's signed URL / web: a blob URL).
    try {
      const { data } = await supabase.auth.getSession();
      const res = await fetch(documentDownloadUrl(documentId), {
        headers: { Authorization: `Bearer ${data.session?.access_token ?? ""}` },
      });
      if (!res.ok) return;
      if (Platform.OS === "web") {
        const blob = await res.blob();
        window.open(URL.createObjectURL(blob), "_blank");
      } else if (res.url && res.url !== documentDownloadUrl(documentId)) {
        Linking.openURL(res.url); // followed redirect → signed URL
      }
    } catch {
      // Non-fatal; the row stays tappable.
    }
  };

  const saveSop = async () => {
    if (!sopDirty || busy) return;
    setBusy("sop");
    setActionError(null);
    try {
      setApp(await updateApplication(id, { motivation_letter: sop }));
      setSopDirty(false);
    } catch (err) {
      setActionError(firstErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const saveReference = async () => {
    if (!app || reference === app.studyinfo_reference) return;
    try {
      setApp(await updateApplication(id, { studyinfo_reference: reference.trim() }));
    } catch {
      // Keep local value; next save retries.
    }
  };

  if (loading || error || !app) {
    return (
      <SafeAreaView edges={["top"]} style={styles.root}>
        <View style={styles.topBar}>
          <Pressable onPress={navigation.goBack} style={styles.backBtn} hitSlop={8}>
            <ChevronLeftIcon size={20} />
          </Pressable>
          <Text style={styles.title}>Application</Text>
        </View>
        {loading ? (
          <View style={styles.centerBox}>
            <ActivityIndicator color={colors.accent} />
          </View>
        ) : (
          <Pressable style={styles.errorBox} onPress={load}>
            <Text style={styles.errorText}>Couldn't load this application.</Text>
            <Text style={styles.errorRetry}>Tap to retry</Text>
          </Pressable>
        )}
      </SafeAreaView>
    );
  }

  const meta = STATUS_META[app.status];
  const ladderIndex = LADDER.indexOf(app.status);
  const next = ladderIndex >= 0 && ladderIndex < LADDER.length - 1 ? LADDER[ladderIndex + 1] : null;
  const terminal = ["rejected", "withdrawn", "place_confirmed"].includes(app.status);

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
          <Text style={styles.title} numberOfLines={1}>{app.university}</Text>
          <Text style={styles.subtitle} numberOfLines={1}>{app.program_name}</Text>
        </View>
        <Stamp label={meta.label} ink={meta.ink} tilt={2} />
      </View>

      <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
        {/* deadline banner */}
        {app.application_deadline !== null && (
          <View style={styles.deadlineBanner}>
            <Text style={styles.deadlineCaption}>DEADLINE</Text>
            <Text style={styles.deadlineText}>
              {new Date(app.application_deadline).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </Text>
          </View>
        )}

        {/* stepper */}
        <View style={styles.stepperCard}>
          <Text style={styles.overline}>ITINERARY</Text>
          {LADDER.map((step, i) => {
            const stepMeta = STATUS_META[step];
            const reached = ladderIndex >= i;
            return (
              <View key={step} style={styles.stepRow}>
                <View style={[styles.stepDot, reached && styles.stepDotOn]}>
                  {reached && <CheckIcon size={11} color="#fff" strokeWidth={3} />}
                </View>
                {i < LADDER.length - 1 && (
                  <View style={[styles.stepLine, ladderIndex > i && styles.stepLineOn]} />
                )}
                <Text style={[styles.stepLabel, reached && styles.stepLabelOn]}>
                  {stepMeta.label}
                </Text>
              </View>
            );
          })}
          {next !== null && !terminal && (
            <Pressable
              onPress={() => advance(next)}
              disabled={busy === "status"}
              style={({ pressed }) => [styles.advanceBtn, pressed && { opacity: 0.85 }]}
            >
              <Text style={styles.advanceBtnText}>
                {busy === "status" ? "Updating…" : NEXT_LABEL[app.status] ?? "Next step"}
              </Text>
            </Pressable>
          )}
          {!terminal && (
            <View style={styles.moreRow}>
              {app.status === "submitted" && (
                <Pressable onPress={() => advance("waitlisted")} hitSlop={6}>
                  <Text style={styles.moreLink}>Waitlisted</Text>
                </Pressable>
              )}
              {app.status === "submitted" && (
                <Pressable onPress={() => advance("rejected")} hitSlop={6}>
                  <Text style={styles.moreLink}>Rejected</Text>
                </Pressable>
              )}
              <Pressable onPress={() => advance("withdrawn")} hitSlop={6}>
                <Text style={styles.moreLink}>Withdraw</Text>
              </Pressable>
            </View>
          )}
        </View>

        {/* Studyinfo hand-off */}
        <View style={styles.sectionCard}>
          <Text style={styles.overline}>GATE</Text>
          <Text style={styles.sectionTitle}>Submit on Studyinfo.fi</Text>
          <Text style={styles.sectionSub}>
            Finnish applications are submitted on the official portal — Wayfara
            preps everything, you press the button there.
          </Text>
          <Pressable
            onPress={() => Linking.openURL("https://opintopolku.fi/konfo/en/")}
            accessibilityRole="link"
            style={({ pressed }) => [styles.linkBtn, pressed && { opacity: 0.8 }]}
          >
            <GlobeIcon size={16} color={colors.accent} />
            <Text style={styles.linkBtnText}>Open Studyinfo.fi</Text>
          </Pressable>
          <TextInput
            value={reference}
            onChangeText={setReference}
            onBlur={saveReference}
            placeholder="Studyinfo application reference (optional)"
            placeholderTextColor={colors.textFaintest}
            style={styles.referenceInput}
          />
        </View>

        {/* document checklist */}
        <View style={styles.sectionCard}>
          <Text style={styles.overline}>TRAVEL DOCUMENTS</Text>
          <Text style={styles.sectionTitle}>Documents</Text>
          <Text style={styles.sectionSub}>
            What this programme asks for. Uploads are stored securely and reused
            across your applications.
          </Text>
          {app.checklist.map((item) => (
            <View key={item.doc_type} style={styles.checkRow}>
              <View style={[styles.checkDot, item.fulfilled && styles.checkDotOn]}>
                {item.fulfilled && <CheckIcon size={12} color="#fff" strokeWidth={3} />}
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.checkLabel}>
                  {item.label}
                  {!item.required && <Text style={styles.optional}>  optional</Text>}
                </Text>
                {item.notes !== "" && <Text style={styles.checkNotes}>{item.notes}</Text>}
              </View>
              {item.document_id !== null && (
                <Pressable onPress={() => viewDocument(item.document_id!)} hitSlop={6}>
                  <Text style={styles.viewLink}>View</Text>
                </Pressable>
              )}
              <Pressable
                onPress={() => pickAndUpload(item)}
                disabled={busy === item.doc_type}
                accessibilityRole="button"
                accessibilityLabel={`Upload ${item.label}`}
                style={({ pressed }) => [styles.uploadBtn, pressed && { opacity: 0.8 }]}
              >
                {busy === item.doc_type ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <UploadIcon size={15} color="#fff" />
                )}
              </Pressable>
            </View>
          ))}
        </View>

        {/* motivation letter */}
        <View style={styles.sectionCard}>
          <Text style={styles.overline}>IN YOUR OWN WORDS</Text>
          <Text style={styles.sectionTitle}>Motivation letter</Text>
          <View style={styles.tipsBox}>
            {SOP_TIPS.map((tip, i) => (
              <Text key={i} style={styles.tip}>•  {tip}</Text>
            ))}
          </View>
          <TextInput
            value={sop}
            onChangeText={(t) => {
              setSop(t);
              setSopDirty(true);
            }}
            multiline
            textAlignVertical="top"
            placeholder={`Why ${app.program_name} at ${app.university}? Start writing…`}
            placeholderTextColor={colors.textFaintest}
            style={styles.sopInput}
          />
          <View style={styles.sopFooter}>
            <Text style={styles.wordCount}>
              {sop.trim() === "" ? 0 : sop.trim().split(/\s+/).length} words
            </Text>
            <Pressable
              onPress={saveSop}
              disabled={!sopDirty || busy === "sop"}
              style={({ pressed }) => [
                styles.sopSaveBtn,
                (!sopDirty || busy === "sop") && { opacity: 0.4 },
                pressed && { opacity: 0.8 },
              ]}
            >
              <Text style={styles.sopSaveText}>
                {busy === "sop" ? "Saving…" : sopDirty ? "Save draft" : "Saved"}
              </Text>
            </Pressable>
          </View>
        </View>

        {actionError !== null && (
          <View style={styles.actionErrorBox}>
            <Text style={styles.actionErrorText}>{actionError}</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 8,
  },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  title: { fontFamily: fonts.display, fontSize: 17, letterSpacing: -0.3, color: colors.ink },
  subtitle: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textFaint },
  overline: { fontFamily: fonts.mono, fontSize: 9, letterSpacing: 1.6, color: colors.textFaintest, marginBottom: 6 },

  centerBox: { alignItems: "center", paddingVertical: 70 },
  errorBox: {
    margin: 20,
    backgroundColor: "#FCEBE7",
    borderWidth: 1,
    borderColor: "#F3C4B8",
    borderRadius: radius["2xl"],
    padding: 18,
    alignItems: "center",
    gap: 4,
  },
  errorText: { fontFamily: fonts.bodySemi, fontSize: 13.5, color: "#B3402A" },
  errorRetry: { fontFamily: fonts.bodyBold, fontSize: 13, color: colors.accent },

  body: { padding: 16, paddingBottom: 40, gap: 14 },

  deadlineBanner: {
    backgroundColor: colors.warningBg,
    borderWidth: 1,
    borderColor: colors.warningBorder,
    borderRadius: radius.xl,
    paddingVertical: 11,
    paddingHorizontal: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  deadlineCaption: { fontFamily: fonts.monoBold, fontSize: 9.5, letterSpacing: 1.2, color: colors.warningInkSoft },
  deadlineText: { fontFamily: fonts.bodyBold, fontSize: 13, color: colors.warningInk },

  stepperCard: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius["2xl"],
    padding: 16,
    ...shadow.card,
  },
  stepRow: { flexDirection: "row", alignItems: "center", gap: 10, position: "relative", paddingVertical: 7 },
  stepDot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: "#E8DCCB",
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  stepDotOn: { backgroundColor: colors.accent, borderColor: colors.accent },
  stepLine: {
    position: "absolute",
    left: 10,
    top: 30,
    width: 2,
    height: 14,
    backgroundColor: "#E8DCCB",
  },
  stepLineOn: { backgroundColor: colors.accent },
  stepLabel: { fontFamily: fonts.bodySemi, fontSize: 13.5, color: colors.textFaint },
  stepLabelOn: { color: colors.ink, fontFamily: fonts.bodyBold },
  advanceBtn: {
    marginTop: 12,
    height: 48,
    borderRadius: radius.md,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  advanceBtnText: { fontFamily: fonts.displaySemi, fontSize: 14, color: "#fff" },
  moreRow: { flexDirection: "row", gap: 18, justifyContent: "center", marginTop: 12 },
  moreLink: { fontFamily: fonts.bodySemi, fontSize: 12.5, color: colors.textFaint, textDecorationLine: "underline" },

  sectionCard: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius["2xl"],
    padding: 16,
    ...shadow.card,
  },
  sectionTitle: { fontFamily: fonts.display, fontSize: 16, color: colors.ink },
  sectionSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textFaint, marginTop: 3, lineHeight: 18 },

  linkBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 44,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginTop: 12,
  },
  linkBtnText: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.accent },
  referenceInput: {
    marginTop: 10,
    height: 46,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderField,
    paddingHorizontal: 13,
    fontFamily: fonts.bodyRegular,
    fontSize: 13.5,
    color: colors.ink,
    backgroundColor: colors.surface,
  },

  checkRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    paddingVertical: 11,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderSoft,
  },
  checkDot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: "#E8DCCB",
    alignItems: "center",
    justifyContent: "center",
  },
  checkDotOn: { backgroundColor: colors.success, borderColor: colors.success },
  checkLabel: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.ink },
  optional: { fontFamily: fonts.bodyRegular, fontSize: 11, color: colors.textFaintest },
  checkNotes: { fontFamily: fonts.bodyRegular, fontSize: 11.5, color: colors.textFaint, marginTop: 1 },
  viewLink: { fontFamily: fonts.bodyBold, fontSize: 12.5, color: colors.accent, marginRight: 4 },
  uploadBtn: {
    width: 36,
    height: 36,
    borderRadius: 11,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },

  tipsBox: {
    backgroundColor: "#FDF8F0",
    borderWidth: 1,
    borderColor: "#F0E4D0",
    borderRadius: radius.lg,
    padding: 12,
    marginTop: 10,
    gap: 5,
  },
  tip: { fontFamily: fonts.bodyRegular, fontSize: 12, color: "#7A6A55", lineHeight: 17 },
  sopInput: {
    marginTop: 12,
    minHeight: 180,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderField,
    padding: 13,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    lineHeight: 21,
    color: colors.ink,
    backgroundColor: colors.surface,
  },
  sopFooter: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 10 },
  wordCount: { fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: 0.6, color: colors.textFaintest },
  sopSaveBtn: {
    height: 40,
    paddingHorizontal: 18,
    borderRadius: radius.md,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  sopSaveText: { fontFamily: fonts.displaySemi, fontSize: 13, color: "#fff" },

  actionErrorBox: {
    backgroundColor: "#FCEBE7",
    borderWidth: 1,
    borderColor: "#F3C4B8",
    borderRadius: radius.xl,
    padding: 12,
  },
  actionErrorText: { fontFamily: fonts.bodySemi, fontSize: 12.5, color: "#B3402A", textAlign: "center" },
});
