"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from '@aws-amplify/auth';

export default function MyClaims() {
  const router = useRouter();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
    // TODO: Fetch claims data from API
  }, []);

  const checkAuth = async () => {
    try {
      await getCurrentUser();
    } catch (error) {
      router.push('/login');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">My Claims</h1>
      
      {loading ? (
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
        </div>
      ) : claims.length === 0 ? (
        <div className="text-center py-12">
          <h3 className="text-xl text-gray-600">No claims found</h3>
          <button 
            className="mt-4 bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
            onClick={() => router.push('/claims/new')}
          >
            Create New Claim
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Claims will be mapped here */}
        </div>
      )}
    </div>
  );
}
