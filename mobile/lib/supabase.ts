/**
 * Supabase client — the app's identity layer.
 *
 * Auth (signup, password login, email OTP, session refresh) goes straight to
 * Supabase; the Django API only ever receives the resulting access token.
 * Sessions persist in AsyncStorage on native and localStorage on web, and
 * supabase-js refreshes them in the background.
 *
 * URL + anon key come from app.config.js `extra` (set SUPABASE_URL /
 * SUPABASE_ANON_KEY in the environment). Until they're set, `isSupabaseConfigured`
 * is false and auth calls fail loudly rather than the app crashing on import.
 */
import "react-native-url-polyfill/auto";
import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";
import { createClient } from "@supabase/supabase-js";

const extra = (Constants.expoConfig?.extra ?? {}) as {
  supabaseUrl?: string;
  supabaseAnonKey?: string;
};

export const SUPABASE_URL = extra.supabaseUrl ?? "";
export const SUPABASE_ANON_KEY = extra.supabaseAnonKey ?? "";
export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

// On web, supabase-js already uses localStorage; provide a thin adapter so the
// same code path works, and use AsyncStorage on native.
const webStorage = {
  getItem: (key: string) => Promise.resolve(globalThis.localStorage?.getItem(key) ?? null),
  setItem: (key: string, value: string) => {
    globalThis.localStorage?.setItem(key, value);
    return Promise.resolve();
  },
  removeItem: (key: string) => {
    globalThis.localStorage?.removeItem(key);
    return Promise.resolve();
  },
};

export const supabase = createClient(
  // Placeholders keep createClient's URL validation happy before real keys are
  // set; any auth call still fails until they are (guarded by isSupabaseConfigured).
  SUPABASE_URL || "https://placeholder.supabase.co",
  SUPABASE_ANON_KEY || "placeholder-anon-key",
  {
    auth: {
      storage: Platform.OS === "web" ? webStorage : AsyncStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  },
);
