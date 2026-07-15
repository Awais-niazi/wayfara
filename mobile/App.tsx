import { StatusBar } from "expo-status-bar";
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

import "./global.css";
import { colors } from "./theme";
import type { RootStackParamList } from "./navigation/types";
import { AuthProvider, useAuth } from "./context/AuthContext";
import WelcomeScreen from "./screens/WelcomeScreen";
import GetStartedScreen from "./screens/GetStartedScreen";
import LoginScreen from "./screens/LoginScreen";
import VerifyOtpScreen from "./screens/VerifyOtpScreen";
import HomeScreen from "./screens/HomeScreen";
import MatchDetailScreen from "./screens/MatchDetailScreen";
import MatchesScreen from "./screens/MatchesScreen";
import ProfileScreen from "./screens/ProfileScreen";
import NotificationsScreen from "./screens/NotificationsScreen";
import ApplicationsScreen from "./screens/ApplicationsScreen";
import ApplicationDetailScreen from "./screens/ApplicationDetailScreen";

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
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen name="MatchDetail" component={MatchDetailScreen} />
          <Stack.Screen name="Matches" component={MatchesScreen} />
          <Stack.Screen name="Profile" component={ProfileScreen} />
          <Stack.Screen name="Notifications" component={NotificationsScreen} />
          <Stack.Screen name="Applications" component={ApplicationsScreen} />
          <Stack.Screen name="ApplicationDetail" component={ApplicationDetailScreen} />
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
