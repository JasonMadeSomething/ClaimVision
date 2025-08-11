"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

interface DateOfLossModalProps {
  onClose: () => void;
}

export default function DateOfLossModal({ onClose }: DateOfLossModalProps) {
  const [dateOfLoss, setDateOfLoss] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const { user } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!user?.id_token) {
      setError("You must be logged in to create a claim");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Ensure the date is interpreted correctly by creating a date with the time set to noon
      // This prevents timezone issues from shifting the date
      const dateParts = dateOfLoss.split('-');
      const year = parseInt(dateParts[0], 10);
      const month = parseInt(dateParts[1], 10) - 1; // JavaScript months are 0-indexed
      const day = parseInt(dateParts[2], 10);
      
      // Create date object with time set to noon to avoid timezone issues
      const lossDate = new Date(year, month, day, 12, 0, 0);
      
      // Format the date for display in the claim title
      const formattedDate = lossDate.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      
      // Create a default title using the date of loss
      const title = `${formattedDate} Claim`;
      
      // Create the claim with minimal required information
      const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const payload = {
        title,
        date_of_loss: dateOfLoss, // Send the original date string in YYYY-MM-DD format
        description: "Claim details to be added"
      };
      
      
      const response = await fetch(`${apiUrl}/claims`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.id_token}`
        },
        body: JSON.stringify(payload)
      });

      
      if (!response.ok) {
        const errorText = await response.text();
        // eslint-disable-next-line no-console
        console.error(`Error response: ${errorText}`);
        throw new Error(errorText || "Failed to create claim");
      }

      const data = await response.json();
      
      // Close the modal before redirecting
      onClose();
      
      // Store the claim ID in localStorage (same as when selecting existing claims)
      localStorage.setItem('current_claim_id', data.id);
      
      // Redirect to the workbench without query params
      router.push('/workbench');
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Error creating claim:", err);
      const message = err instanceof Error ? err.message : 'Failed to create claim';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h2 className="text-xl font-bold mb-4">Create New Claim</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="dateOfLoss" className="block text-sm font-medium text-gray-700">
              Date of Loss
            </label>
            <input
              id="dateOfLoss"
              type="date"
              value={dateOfLoss}
              onChange={(e) => setDateOfLoss(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-sm text-gray-500">
              Please select the date when the loss occurred.
            </p>
          </div>
          
          {error && (
            <div className="text-red-600 text-sm">
              {error}
            </div>
          )}
          
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create Claim"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
