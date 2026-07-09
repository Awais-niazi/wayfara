// Dynamic Expo config. Everything that was static in app.json lives here so a
// single field — the backend API URL — can come from the environment.
//
//   dev:        WAYFARA_API_URL unset -> falls back to the local dev backend.
//               (Ash holds :8000 on the dev machine, so Wayfara dev runs :8010.)
//   Railway/EAS: set WAYFARA_API_URL=https://<your-app>.up.railway.app and it
//               flows into Constants.expoConfig.extra.apiUrl (read by lib/api.ts).
//
// Nothing here is Railway-specific yet — it just stops the production API URL
// from being hardcoded, ready for the eventual deploy.

const API_URL = process.env.WAYFARA_API_URL ?? "http://localhost:8010";

/** @type {import('@expo/config').ExpoConfig} */
module.exports = {
  name: "Wayfara",
  slug: "wayfara",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "light",
  ios: {
    supportsTablet: true,
  },
  android: {
    adaptiveIcon: {
      backgroundColor: "#F8593C",
      foregroundImage: "./assets/android-icon-foreground.png",
      backgroundImage: "./assets/android-icon-background.png",
      monochromeImage: "./assets/android-icon-monochrome.png",
    },
    predictiveBackGestureEnabled: false,
  },
  web: {
    favicon: "./assets/favicon.png",
  },
  plugins: ["expo-font", "expo-secure-store"],
  extra: {
    apiUrl: API_URL,
  },
};
