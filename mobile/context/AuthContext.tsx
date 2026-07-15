/**
 * Auth state for the app, backed by Supabase.
 *
 * Supabase owns the session (sign-up, password login, email OTP, refresh);
 * this context derives the app's route from two facts: is there a Supabase
 * session, and has the user finished onboarding on our backend (`/me/`).
 *
 * Status drives the root navigator:
 *   "loading"   → splash (session still resolving)
 *   "signedOut" → Welcome / GetStarted / Login / VerifyOtp stack. This also
 *                 covers "has a session but hasn't onboarded yet", so the
 *                 Get Started flow can finish without the navigator yanking
 *                 the screen out from under it.
 *   "signedIn"  → Home
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { getMe, logout as apiLogout, type Me } from "../lib/api";
import {
  getRegisteredPushToken,
  registerForPushNotifications,
} from "../lib/pushRegistration";
import { supabase } from "../lib/supabase";

type AuthStatus = "loading" | "signedOut" | "signedIn";

interface AuthState {
  status: AuthStatus;
  me: Me | null;
  /** Re-read the session + `/me/` and recompute the route. Call after
   *  completing onboarding so the navigator flips to Home. */
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [me, setMe] = useState<Me | null>(null);

  // The single source of truth: a session + a completed onboarding = signed in.
  const resolve = useCallback(async () => {
    const { data } = await supabase.auth.getSession();
    if (!data.session) {
      setMe(null);
      setStatus("signedOut");
      return;
    }
    try {
      const session = await getMe();
      setMe(session);
      // A session without a finished profile stays in the signed-out stack so
      // the Get Started flow can run its final onboarding call.
      setStatus(session.onboarding_complete ? "signedIn" : "signedOut");
      if (session.onboarding_complete) {
        // Fire-and-forget: permission ask + Expo token + /devices/ register.
        registerForPushNotifications();
      }
    } catch {
      // Token rejected (e.g. Supabase not configured yet) — treat as signed out.
      setMe(null);
      setStatus("signedOut");
    }
  }, []);

  useEffect(() => {
    resolve();
    // Fires on sign-in / sign-out / token refresh; recompute the route each time.
    const { data } = supabase.auth.onAuthStateChange(() => {
      resolve();
    });
    return () => data.subscription.unsubscribe();
  }, [resolve]);

  const signOut = useCallback(async () => {
    try {
      // Prune this device's push token so a signed-out phone goes quiet.
      await apiLogout(getRegisteredPushToken() ?? undefined);
    } catch {
      // Signing out locally regardless.
    }
    await supabase.auth.signOut();
    setMe(null);
    setStatus("signedOut");
  }, []);

  return (
    <AuthContext.Provider value={{ status, me, refresh: resolve, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
