import type { Match } from "../lib/api";

/** Route params for the root native stack. */
export type RootStackParamList = {
  // Signed-out stack
  Welcome: undefined;
  GetStarted: undefined;
  Login: undefined;
  VerifyOtp: { email: string };
  // Own stack while me.has_password is false (onboarding step 3)
  CreatePassword: undefined;
  // Signed-in stack
  Home: undefined;
  // The match card carries everything above the fold; the curated university
  // profile (overview, all programmes) loads in behind it.
  MatchDetail: { match: Match };
  // Home already holds the full ranked list — hand it over for instant render.
  Matches: { matches: Match[] };
  Profile: undefined;
};
