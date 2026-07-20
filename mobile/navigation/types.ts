import type { CompositeScreenProps, NavigatorScreenParams } from "@react-navigation/native";
import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import type { Match, OnboardingForm } from "../lib/api";

/** The five persistent tabs of the signed-in app. */
export type TabParamList = {
  Home: undefined;
  Explore: undefined;
  Apps: undefined;
  Chat: undefined;
  Profile: undefined;
};

/** Route params for the root native stack. */
export type RootStackParamList = {
  // Signed-out stack
  Welcome: undefined;
  GetStarted: undefined;
  Login: undefined;
  // "signup" carries the profile to store once the email code verifies;
  // "login" is the passwordless returning-user path.
  VerifyOtp: { email: string; mode: "signup" | "login"; onboarding?: OnboardingForm };
  // Signed-in stack: the tab dock, plus detail screens pushed over it.
  MainTabs: NavigatorScreenParams<TabParamList> | undefined;
  // The match card carries everything above the fold; the curated university
  // profile (overview, all programmes) loads in behind it.
  MatchDetail: { match: Match };
  ApplicationDetail: { id: number };
  Notifications: undefined;
  // One profile category (personal / academic / test / plan) — pushed from
  // the Profile tab's rows, native settings style.
  ProfileSection: { section: ProfileSectionKey };
};

export type ProfileSectionKey = "personal" | "academic" | "test" | "plan";

/** Props for a screen living inside the tab dock (can also reach stack routes). */
export type TabScreenProps<T extends keyof TabParamList> = CompositeScreenProps<
  BottomTabScreenProps<TabParamList, T>,
  NativeStackScreenProps<RootStackParamList>
>;
