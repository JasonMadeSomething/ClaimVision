"use client";

import { useState } from "react";

interface ConfirmSignUpProps {
  username: string;
  onSuccess: () => void;
  onCancel: () => void;
}

export default function ConfirmSignUp({ username, onSuccess, onCancel }: ConfirmSignUpProps) {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const response = await fetch(`${apiUrl}/auth/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          code
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error_details || "Failed to confirm account");
      }
      
      onSuccess();
    } catch (err: unknown) {
      console.error("❌ Confirmation error:", err);
      const message = err instanceof Error ? err.message : 'Failed to confirm account';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Confirm Your Account</h2>
      <p className="mb-4 text-gray-700">
        Please enter the verification code sent to your email.
      </p>
      <form onSubmit={handleConfirm} className="space-y-4">
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
        <div className="flex flex-col space-y-3">
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? "Confirming..." : "Confirm Account"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
