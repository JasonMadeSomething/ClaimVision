"use client"; // ✅ Ensures this runs only on the client-side

import { useEffect } from "react";
import "./globals.css"; // Ensure global styles are loaded
import { initializeAmplify } from "@/amplifyConfig"; // ✅ Import Amplify config
import Navigation from "@/components/Navigation";
import { AuthProvider } from "@/context/AuthContext";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initializeAmplify();
  }, []);

  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <AuthProvider>
          <Navigation />
          <main className="container mx-auto px-4 py-8">
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
