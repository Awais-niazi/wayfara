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

import "./global.css";
import { colors } from "./theme";
import type { RootStackParamList } from "./navigation/types";
import { AuthProvider, useAuth } from "./context/AuthContext";
import WelcomeScreen from "./screens/WelcomeScreen";
import GetStartedScreen from "./screens/GetStartedScreen";
import LoginScreen from "./screens/LoginScreen";
import VerifyOtpScreen from "./screens/VerifyOtpScreen";
import CreatePasswordScreen from "./screens/CreatePasswordScreen";
import HomeScreen from "./screens/HomeScreen";
import MatchDetailScreen from "./screens/MatchDetailScreen";
import MatchesScreen from "./screens/MatchesScreen";
import ProfileScreen from "./screens/ProfileScreen";

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
        </>
      ) : status === "needsPassword" ? (
        // Onboarding step 3: email verified, password pending. Its own stack
        // so neither the form nor the dashboard is reachable around it.
        <Stack.Screen name="CreatePassword" component={CreatePasswordScreen} />
      ) : (
        <>
          {/* Landing: Welcome hero with the "Get Started" CTA → profile form.
              No register wall — the form itself creates the account. */}
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
