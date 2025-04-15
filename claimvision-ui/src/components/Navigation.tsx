"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { UserCircleIcon } from '@heroicons/react/24/solid';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import SignInForm from './SignInForm';
import SignUpForm from './SignUpForm';
import { useAuth } from '@/context/AuthContext';

export default function Navigation() {
  const [showSignIn, setShowSignIn] = useState(false);
  const [showSignUp, setShowSignUp] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const { user, signOut, isLoading, refreshSession } = useAuth();
  
  // Debug log to see what's in the user object
  useEffect(() => {
    console.log('Navigation - Auth state:', { user, isLoading, pathname });
  }, [user, isLoading, pathname]);

  // Only refresh session once on initial load, not on every route change
  useEffect(() => {
    console.log('Navigation - Initial load, refreshing session');
    refreshSession();
    // Empty dependency array means this only runs once on mount
  }, []);

  const handleSignOut = async () => {
    try {
      await signOut();
      router.push('/');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <nav className="bg-gray-800 text-white py-4 px-6">
      <div className="container mx-auto flex justify-between items-center relative">
        <Link href="/" className="text-2xl font-bold">
          ClaimVision
        </Link>
        
        <div className="flex items-center space-x-4">
          {isLoading ? (
            <div className="text-white">Loading...</div>
          ) : user ? (
            <>
              <Link href="/my-claims" className="text-white hover:text-gray-300">
                My Claims
              </Link>
              <Menu as="div" className="relative">
                <Menu.Button className="text-white hover:text-gray-300">
                  <UserCircleIcon className="h-8 w-8" />
                </Menu.Button>
                <Transition
                  as={Fragment}
                  enter="transition ease-out duration-100"
                  enterFrom="transform opacity-0 scale-95"
                  enterTo="transform opacity-100 scale-100"
                  leave="transition ease-in duration-75"
                  leaveFrom="transform opacity-100 scale-100"
                  leaveTo="transform opacity-0 scale-95"
                >
                  <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                    <Menu.Item>
                      {({ active }) => (
                        <Link
                          href="/profile"
                          className={`${
                            active ? 'bg-gray-100' : ''
                          } block px-4 py-2 text-sm text-gray-700`}
                        >
                          Profile
                        </Link>
                      )}
                    </Menu.Item>
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          onClick={handleSignOut}
                          className={`${
                            active ? 'bg-gray-100' : ''
                          } block w-full text-left px-4 py-2 text-sm text-gray-700`}
                        >
                          Sign Out
                        </button>
                      )}
                    </Menu.Item>
                  </Menu.Items>
                </Transition>
              </Menu>
            </>
          ) : (
            <div className="space-x-4">
              <button
                id="signInButton"
                onClick={() => setShowSignIn(true)}
                className="px-4 py-2 bg-blue-500 rounded hover:bg-blue-600"
              >
                Sign In
              </button>
              <button
                onClick={() => setShowSignUp(true)}
                className="px-4 py-2 border border-white rounded hover:bg-gray-700"
              >
                Sign Up
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Sign In Modal */}
      {showSignIn && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h2 className="text-2xl font-bold mb-4">Sign In</h2>
            <SignInForm 
              onClose={() => setShowSignIn(false)}
            />
          </div>
        </div>
      )}
      
      {/* Sign Up Modal */}
      {showSignUp && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h2 className="text-2xl font-bold mb-4">Sign Up</h2>
            <SignUpForm 
              onClose={() => setShowSignUp(false)}
            />
          </div>
        </div>
      )}
    </nav>
  );
}
