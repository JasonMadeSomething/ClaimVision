"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function NewClaim() {
  const router = useRouter();
  
  useEffect(() => {
    // Redirect to the my-claims page with a parameter to open the modal
    router.replace('/my-claims?createNew=true');
  }, [router]);

  // Show a loading state while redirecting
  return (
    <div className="container mx-auto px-4 py-8 flex justify-center items-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      <span className="ml-3">Redirecting to simplified claim creation...</span>
    </div>
  );
}
