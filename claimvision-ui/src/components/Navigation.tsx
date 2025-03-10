"use client";

import { useEffect, useState, useRef } from 'react';
import { getCurrentUser, signOut } from '@aws-amplify/auth';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { UserCircleIcon } from '@heroicons/react/24/solid';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import SignInForm from './SignInForm';
import SignUpForm from './SignUpForm';

export default function Navigation() {
  // For development, set isAuthenticated to true by default
  const [isAuthenticated, setIsAuthenticated] = useState(true);
  const [showSignIn, setShowSignIn] = useState(false);
  const [showSignUp, setShowSignUp] = useState(false);
  const router = useRouter();

  // Skip authentication check for development
  useEffect(() => {
    // Development mode: Skip actual auth check
    // checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      const user = await getCurrentUser();
      setIsAuthenticated(!!user);
    } catch (error) {
      // For development, keep authenticated even if there's an error
      // setIsAuthenticated(false);
    }
  };

  const handleSignOut = async () => {
    try {
      // For development, just set state without actual signout
      // await signOut();
      setIsAuthenticated(false);
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
          {isAuthenticated ? (
            <>
              <Link href="/my-claims" className="text-white hover:text-gray-300">
                My Claims
              </Link>
              <Link href="/workbench" className="text-white hover:text-gray-300">
                Workbench
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
                onClick={() => {
                  // For development, just set authenticated to true
                  setIsAuthenticated(true);
                }}
                className="px-4 py-2 bg-blue-500 rounded hover:bg-blue-600"
              >
                Sign In (Dev Mode)
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
