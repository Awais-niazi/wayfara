/**
 * Persistent JWT storage. Native uses the OS keychain via expo-secure-store;
 * web (dev preview) falls back to localStorage, which SecureStore does not
 * support.
 */
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

import type { Tokens } from "./api";

const KEY = "wayfara.tokens";

export async function loadTokens(): Promise<Tokens | null> {
  try {
    const raw =
      Platform.OS === "web"
        ? globalThis.localStorage?.getItem(KEY) ?? null
        : await SecureStore.getItemAsync(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Tokens;
    return parsed.access && parsed.refresh ? parsed : null;
  } catch {
    return null;
  }
}

export async function saveTokens(tokens: Tokens): Promise<void> {
  const raw = JSON.stringify(tokens);
  if (Platform.OS === "web") {
    globalThis.localStorage?.setItem(KEY, raw);
  } else {
    await SecureStore.setItemAsync(KEY, raw);
  }
}

export async function clearTokens(): Promise<void> {
  if (Platform.OS === "web") {
    globalThis.localStorage?.removeItem(KEY);
  } else {
    await SecureStore.deleteItemAsync(KEY);
  }
}
