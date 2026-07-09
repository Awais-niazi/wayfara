/**
 * Auth state for the app: holds the JWT pair, bootstraps the session on
 * launch (`/api/me/`), and services the API client's refresh-on-401 hook.
 *
 * Status drives the root navigator:
 *   "loading"   → splash (fonts/session still resolving)
 *   "signedOut" → Welcome / GetStarted / Login / VerifyOtp stack
 *   "signedIn"  → Home
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  configureApi,
  getMe,
  logout as apiLogout,
  refreshTokens,
  type Me,
  type Tokens,
} from "../lib/api";
import { clearTokens, loadTokens, saveTokens } from "../lib/tokenStorage";

type AuthStatus = "loading" | "signedOut" | "needsPassword" | "signedIn";

interface AuthState {
  status: AuthStatus;
  me: Me | null;
  /** Store a fresh token pair (after OTP verify) and load the session.
   *  Routes to the create-password step if the account has none yet. */
  signIn: (tokens: Tokens) => Promise<void>;
  /** Re-check the session after the password step completes. */
  completePasswordStep: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [me, setMe] = useState<Me | null>(null);
  // Tokens live in a ref: the API client reads them synchronously per-request
  // and a re-render per refresh would buy nothing.
  const tokensRef = useRef<Tokens | null>(null);

  const setTokens = useCallback(async (tokens: Tokens | null) => {
    tokensRef.current = tokens;
    if (tokens) await saveTokens(tokens);
    else await clearTokens();
  }, []);

  const signOut = useCallback(async () => {
    const refresh = tokensRef.current?.refresh;
    if (refresh) {
      try {
        await apiLogout(refresh); // blacklist server-side; best-effort
      } catch {
        // Signed out locally regardless.
      }
    }
    await setTokens(null);
    setMe(null);
    setStatus("signedOut");
  }, [setTokens]);

  // Register the token hooks the API client calls on every request.
  useEffect(() => {
    configureApi({
      getAccessToken: () => tokensRef.current?.access ?? null,
      onUnauthorized: async () => {
        const refresh = tokensRef.current?.refresh;
        if (!refresh) return null;
        try {
          const fresh = await refreshTokens(refresh); // rotation: new pair
          await setTokens(fresh);
          return fresh.access;
        } catch {
          await setTokens(null);
          setMe(null);
          setStatus("signedOut");
          return null;
        }
      },
    });
  }, [setTokens]);

  const signIn = useCallback(
    async (tokens: Tokens) => {
      await setTokens(tokens);
      const session = await getMe();
      setMe(session);
      // Onboarding step 3: no password yet -> the navigator shows the
      // create-password screen instead of the dashboard.
      setStatus(session.has_password ? "signedIn" : "needsPassword");
    },
    [setTokens],
  );

  const completePasswordStep = useCallback(async () => {
    const session = await getMe();
    setMe(session);
    setStatus(session.has_password ? "signedIn" : "needsPassword");
  }, []);

  // Session bootstrap: stored tokens + /me/ decide the initial route.
  useEffect(() => {
    (async () => {
      const stored = await loadTokens();
      if (!stored) {
        setStatus("signedOut");
        return;
      }
      tokensRef.current = stored;
      try {
        const session = await getMe(); // 401 auto-refreshes via the hook
        setMe(session);
        // Resume mid-onboarding sessions on the password step.
        setStatus(session.has_password ? "signedIn" : "needsPassword");
      } catch {
        await setTokens(null);
        setStatus("signedOut");
      }
    })();
  }, [setTokens]);

  return (
    <AuthContext.Provider value={{ status, me, signIn, completePasswordStep, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
