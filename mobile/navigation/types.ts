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
};
