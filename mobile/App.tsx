import { StatusBar } from "expo-status-bar";
import Constants from "expo-constants";
import * as Sentry from "@sentry/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { useFonts } from "expo-font";
import {
  Manrope_400Regular,
  Manrope_500Medium,
  Manrope_600SemiBold,
  Manrope_700Bold,
} from "@expo-google-fonts/manrope";
import {
  SpaceGrotesk_500Medium,
  SpaceGrotesk_600SemiBold,
  SpaceGrotesk_700Bold,
} from "@expo-google-fonts/space-grotesk";
// Dashboard greeting: Times New Roman + Zapfino are Apple/Monotype system
// fonts — real on iOS, absent on Android/web. Tinos is metrically identical
// to Times New Roman; Great Vibes is the Zapfino-style calligraphic script.
import { Tinos_400Regular } from "@expo-google-fonts/tinos";
import { GreatVibes_400Regular } from "@expo-google-fonts/great-vibes";
// Space Mono — the travel-document voice (tickets, stamps, codes, deadlines).
import { SpaceMono_400Regular, SpaceMono_700Bold } from "@expo-google-fonts/space-mono";

import "./global.css";
import { colors } from "./theme";
import type { RootStackParamList } from "./navigation/types";
import { AuthProvider, useAuth } from "./context/AuthContext";
import WelcomeScreen from "./screens/WelcomeScreen";
import GetStartedScreen from "./screens/GetStartedScreen";
import LoginScreen from "./screens/LoginScreen";
import VerifyOtpScreen from "./screens/VerifyOtpScreen";
import MainTabs from "./navigation/MainTabs";
import MatchDetailScreen from "./screens/MatchDetailScreen";
import NotificationsScreen from "./screens/NotificationsScreen";
import ApplicationDetailScreen from "./screens/ApplicationDetailScreen";

// Client crash reporting — inert until a DSN is configured (mobile/.env:
// SENTRY_DSN_MOBILE). Sibling of the backend's Sentry; see docs/PLAYBOOK.md.
const sentryDsn = (Constants.expoConfig?.extra as { sentryDsn?: string } | undefined)?.sentryDsn;
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: __DEV__ ? "development" : "production",
    // Errors only for now — tracing/replay are paid-tier noise at this stage.
    tracesSampleRate: 0,
  });
}

const Stack = createNativeStackNavigator<RootStackParamList>();

/** Auth-gated stacks: signed-out onboarding flow vs signed-in app. */
function RootNavigator() {
  const { status } = useAuth();

  // Session bootstrap in flight — stay on the (canvas-colored) splash.
  if (status === "loading") return null;

  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.canvas },
        animation: "slide_from_right",
      }}
    >
      {status === "signedIn" ? (
        <>
          {/* Persistent tab dock; detail screens slide in over it. */}
          <Stack.Screen name="MainTabs" component={MainTabs} />
          <Stack.Screen name="MatchDetail" component={MatchDetailScreen} />
          <Stack.Screen name="ApplicationDetail" component={ApplicationDetailScreen} />
          <Stack.Screen name="Notifications" component={NotificationsScreen} />
        </>
      ) : (
        <>
          {/* Landing: Welcome hero with the "Get Started" CTA → profile form.
              No register wall — the form itself signs the user up. */}
          <Stack.Screen name="Welcome" component={WelcomeScreen} />
          <Stack.Screen name="GetStarted" component={GetStartedScreen} />
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="VerifyOtp" component={VerifyOtpScreen} />
        </>
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  const [fontsLoaded] = useFonts({
    Manrope_400Regular,
    Manrope_500Medium,
    Manrope_600SemiBold,
    Manrope_700Bold,
    SpaceGrotesk_500Medium,
    SpaceGrotesk_600SemiBold,
    SpaceGrotesk_700Bold,
    Tinos_400Regular,
    GreatVibes_400Regular,
    SpaceMono_400Regular,
    SpaceMono_700Bold,
  });

  // Hold render until fonts are ready — the design leans heavily on
  // Space Grotesk / Manrope, so a flash of the system font looks broken.
  if (!fontsLoaded) return null;

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <NavigationContainer>
          <RootNavigator />
        </NavigationContainer>
        <StatusBar style="dark" />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
