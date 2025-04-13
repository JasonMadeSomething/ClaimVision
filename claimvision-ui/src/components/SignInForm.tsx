"use client";

import { useState, useEffect } from "react";
import { useRouter } from 'next/navigation';
import { useAuth } from "@/context/AuthContext";
import { fetchAuthSession } from "@aws-amplify/auth";

export default function SignInForm({ onClose }: { onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const { user, setUser, signOut, isLoading } = useAuth();

  // Check if user is already signed in - only once on mount
  useEffect(() => {
    // Only set error if we're not in the loading state and user exists
    if (!isLoading && user) {
      setError("You are already signed in. Please sign out first if you want to sign in with a different account.");
    }
  }, [isLoading, user]);

  const handleSignOut = async () => {
    try {
      await signOut();
      setError("");
    } catch (err: any) {
      console.error("Sign-out error:", err.message);
      setError(`Failed to sign out: ${err.message}`);
    }
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // If already signed in, don't try to sign in again
    if (user) {
      return;
    }
    
    setLoading(true);
    setError("");

    try {
      console.log("SignInForm: Attempting to sign in with email:", email);
      
      // Call the login API directly
      const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const response = await fetch(`${apiUrl}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: email,
          password
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error_details || 'Failed to sign in');
      }

      const loginData = await response.json();
      console.log("SignInForm: Sign-in successful, result:", loginData);
      
      if (!loginData.data || !loginData.data.id_token) {
        throw new Error('Invalid response from server - missing authentication tokens');
      }
      
      // Update the auth context with the user
      // We need to refresh the session to get the updated tokens
      await setUser(loginData.data);
      
      // Close the modal
      onClose();
      
      // Redirect to my claims page
      router.push('/my-claims');
    } catch (err: any) {
      console.error("Sign-in error:", err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-4">
        <h2 className="text-xl font-bold mb-4">Sign In</h2>
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-2">Checking authentication status...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Sign In</h2>
      
      {user && (
        <div className="mb-4">
          <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
            You are already signed in. Please sign out first if you want to sign in with a different account.
          </div>
          <button
            onClick={handleSignOut}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            Sign Out
          </button>
        </div>
      )}
      
      <form onSubmit={handleSignIn} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            required
            disabled={!!user}
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            required
            disabled={!!user}
          />
        </div>
        {error && !user && (
          <div className="text-red-600 text-sm">
            {error}
          </div>
        )}
        <div className="flex flex-col space-y-3">
          <button
            type="submit"
            disabled={loading || !!user}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Close
          </button>
        </div>
      </form>
    </div>
  );
}
