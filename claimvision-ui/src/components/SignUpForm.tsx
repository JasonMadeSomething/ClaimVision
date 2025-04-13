"use client";

import { useState, useEffect } from "react";
import { useRouter } from 'next/navigation';
import { useAuth } from "@/context/AuthContext";

export default function SignUpForm({ onClose }: { onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showConfirmation, setShowConfirmation] = useState(false);
  const router = useRouter();
  const { user, signOut, isLoading } = useAuth();

  // Check if user is already signed in
  useEffect(() => {
    // Only set error if we're not in the loading state and user exists
    if (!isLoading && user) {
      setError("You are already signed in. Please sign out first if you want to create a new account.");
    }
  }, [user, isLoading]);

  const handleSignOut = async () => {
    try {
      await signOut();
      setError("");
    } catch (err: any) {
      console.error("Sign-out error:", err.message);
      setError(`Failed to sign out: ${err.message}`);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // If already signed in, don't try to sign up
    if (user) {
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (!firstName || !lastName) {
      setError("First name and last name are required");
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      // Make an API call to register with all required fields
      const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const response = await fetch(`${apiUrl}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password,
          first_name: firstName,
          last_name: lastName
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error_details || 'Failed to complete registration');
      }

      const data = await response.json();
      console.log("Registration successful:", data);

      setSuccess("Account created successfully! Please check your email for a confirmation code.");
      setShowConfirmation(true);
    } catch (err: any) {
      console.error("Sign-up error:", err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // Call the confirmation API endpoint
      const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const response = await fetch(`${apiUrl}/auth/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: email,
          code
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error_details || 'Failed to confirm account');
      }
      
      setSuccess("Account confirmed successfully! You can now sign in.");
      
      // Close the modal after a short delay
      setTimeout(() => {
        onClose();
        // Open the sign-in modal
        document.getElementById('signInButton')?.click();
      }, 2000);
    } catch (err: any) {
      console.error("Confirmation error:", err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-4">
        <h2 className="text-xl font-bold mb-4">Sign Up</h2>
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
          <span className="ml-2">Checking authentication status...</span>
        </div>
      </div>
    );
  }

  if (showConfirmation) {
    return (
      <div className="p-4">
        <h2 className="text-xl font-bold mb-4">Confirm Your Account</h2>
        <p className="mb-4 text-gray-700">
          Please enter the confirmation code sent to your email.
        </p>
        <form onSubmit={handleConfirmSignUp} className="space-y-4">
          <div>
            <label htmlFor="code" className="block text-sm font-medium text-gray-700">
              Verification Code
            </label>
            <input
              id="code"
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
              required
            />
          </div>
          {error && (
            <div className="text-red-600 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="text-green-600 text-sm">
              {success}
            </div>
          )}
          <div className="flex flex-col space-y-3">
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
            >
              {loading ? "Confirming..." : "Confirm Account"}
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

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Sign Up</h2>
      
      {user && (
        <div className="mb-4">
          <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
            You are already signed in. Please sign out first if you want to create a new account.
          </div>
          <button
            onClick={handleSignOut}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            Sign Out
          </button>
        </div>
      )}
      
      <form onSubmit={handleSignUp} className="space-y-4">
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
          <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">
            First Name
          </label>
          <input
            id="firstName"
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            required
            disabled={!!user}
          />
        </div>
        <div>
          <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">
            Last Name
          </label>
          <input
            id="lastName"
            type="text"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
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
        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            required
            disabled={!!user}
          />
        </div>
        {error && (
          <div className="text-red-600 text-sm">
            {error}
          </div>
        )}
        {success && !showConfirmation && (
          <div className="text-green-600 text-sm">
            {success}
          </div>
        )}
        <div className="flex flex-col space-y-3">
          <button
            type="submit"
            disabled={loading || !!user}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
          >
            {loading ? "Signing up..." : "Sign Up"}
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
