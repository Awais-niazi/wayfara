import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { Text, View } from "react-native";

import "./global.css";

export default function App() {
  return (
    <SafeAreaProvider>
      <SafeAreaView className="flex-1 bg-white">
        <View className="flex-1 items-center justify-center px-8">
          <Text className="text-4xl font-bold text-primary">Wayfara</Text>
          <Text className="mt-3 text-center text-base text-gray-600">
            Your journey to studying in Finland starts here.
          </Text>
          <View className="mt-8 rounded-full bg-primary px-6 py-3">
            <Text className="font-semibold text-white">Week 1 scaffold ✓</Text>
          </View>
        </View>
        <StatusBar style="auto" />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}
