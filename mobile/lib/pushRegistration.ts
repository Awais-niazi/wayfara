/**
 * Expo push registration — the mobile half of the notification platform.
 *
 * Called once per signed-in session (AuthContext). Everything is best-effort
 * and silent: web has no Expo push, simulators have no tokens, users may
 * decline permission — none of that should ever surface as an error. The
 * in-app inbox (NotificationsScreen) is the durable channel; push is the
 * mirror.
 *
 * Note: since SDK 53, remote push on Android requires a dev build (Expo Go
 * no longer supports it) — this module simply no-ops until then.
 */
import { Platform } from "react-native";
import Constants from "expo-constants";

import { registerDevice } from "./api";

// Remembered so signOut can tell the backend which device token to prune.
let currentToken: string | null = null;

export function getRegisteredPushToken(): string | null {
  return currentToken;
}

export async function registerForPushNotifications(): Promise<void> {
  if (Platform.OS === "web") return; // Expo push doesn't exist on web

  try {
    // Imported lazily so the web bundle never pulls native-only modules.
    const Device = await import("expo-device");
    if (!Device.isDevice) return; // simulators/emulators have no push tokens

    const Notifications = await import("expo-notifications");

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "Wayfara",
        importance: Notifications.AndroidImportance.HIGH,
        sound: "default",
      });
    }

    const existing = await Notifications.getPermissionsAsync();
    let status = existing.status;
    if (status !== "granted") {
      status = (await Notifications.requestPermissionsAsync()).status;
    }
    if (status !== "granted") return; // declined — inbox still works

    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
    const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;

    await registerDevice(token, Platform.OS === "ios" ? "ios" : "android");
    currentToken = token;
  } catch {
    // Missing project id / no network / Expo Go limitation — push simply
    // stays off for this session; never break sign-in over it.
  }
}
