import type { Match, OnboardingForm } from "../lib/api";

/** Route params for the root native stack. */
export type RootStackParamList = {
  // Signed-out stack
  Welcome: undefined;
  GetStarted: undefined;
  Login: undefined;
  // "signup" carries the profile to store once the email code verifies;
  // "login" is the passwordless returning-user path.
  VerifyOtp: { email: string; mode: "signup" | "login"; onboarding?: OnboardingForm };
  // Signed-in stack
  Home: undefined;
  // The match card carries everything above the fold; the curated university
  // profile (overview, all programmes) loads in behind it.
  MatchDetail: { match: Match };
  // Home already holds the full ranked list — hand it over for instant render.
  Matches: { matches: Match[] };
  Profile: undefined;
  Notifications: undefined;
  Applications: undefined;
  ApplicationDetail: { id: number };
};
