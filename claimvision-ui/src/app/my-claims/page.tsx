"use client";

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import DateOfLossModal from '@/components/DateOfLossModal';

interface Claim {
  id: string;
  title: string;
  status: string;
  created_at: string;
  description?: string;
}

export default function MyClaims() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const { user } = useAuth();

  // Check if we should show the modal based on query params
  useEffect(() => {
    const createNew = searchParams.get('createNew');
    if (createNew === 'true') {
      setShowModal(true);
    }
  }, [searchParams]);

  useEffect(() => {
    const fetchClaims = async () => {
      if (!user) {
        router.push('/');
        return;
      }

      setLoading(true);
      setError(null);
      
      try {
        // Use the ID token from the auth context instead of fetchAuthSession
        if (!user.id_token) {
          throw new Error('No valid ID token found in user context');
        }
        
        const idToken = user.id_token;
        console.log("Using ID token from auth context");
        
        // Fetch claims from the API
        const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
        console.log(`Fetching claims from: ${apiUrl}/claims`);
        
        const response = await fetch(`${apiUrl}/claims`, {
          method: 'GET', // Explicitly set method to GET
          headers: {
            Authorization: `Bearer ${idToken}`,
            'Content-Type': 'application/json'
          }
        });

        console.log(`Response status: ${response.status}`);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error(`Error response: ${errorText}`);
          throw new Error(`Failed to fetch claims: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        console.log(`Raw API response:`, data);
        
        // Check if the data is wrapped in a data property (common API pattern)
        const claimsData = data.data?.results || [];
        console.log(`Processed claims data:`, claimsData);
        // Ensure we're handling an array of claims
        if (Array.isArray(claimsData)) {
          console.log(`Received ${claimsData.length} claims`);
          setClaims(claimsData);
        } else {
          console.log(`Received non-array data, setting empty claims list`);
          setClaims([]);
        }
      } catch (err: any) {
        console.error('Error fetching claims:', err);
        setError(err.message || 'Failed to load claims. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchClaims();
  }, [user, router]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(date);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">My Claims</h1>
        <button 
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          onClick={() => setShowModal(true)}
          type="button"
        >
          Create New Claim
        </button>
      </div>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : claims.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <h3 className="text-xl text-gray-600 mb-2">No claims found</h3>
          <p className="text-gray-500 mb-6">Create a new claim to get started</p>
          <button 
            className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
            onClick={() => setShowModal(true)}
            type="button"
          >
            Create New Claim
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {claims.map((claim) => (
            <div 
              key={claim.id}
              className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => {
                // Store the claim ID in localStorage
                localStorage.setItem('current_claim_id', claim.id);
                // Navigate to the workbench without query params
                router.push('/workbench');
              }}
            >
              <div className="p-4 border-b">
                <div className="flex justify-between items-start">
                  <h3 className="text-lg font-semibold truncate">{claim.title}</h3>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    claim.status === 'open' ? 'bg-green-100 text-green-800' :
                    claim.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {claim.status}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  Created: {formatDate(claim.created_at)}
                </p>
              </div>
              <div className="p-4 bg-gray-50">
                <p className="text-sm text-gray-700 line-clamp-2">
                  {claim.description || 'No description provided'}
                </p>
                <div className="mt-3 text-blue-600 text-sm font-medium">
                  View Claim →
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {showModal && <DateOfLossModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
