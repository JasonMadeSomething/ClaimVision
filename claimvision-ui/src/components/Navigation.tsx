"use client";

import { useEffect, useState } from 'react';
import { getCurrentUser, signOut } from '@aws-amplify/auth';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { UserCircleIcon } from '@heroicons/react/24/solid';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import SignInForm from './SignInForm';
import SignUpForm from './SignUpForm';

export default function Navigation() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showSignIn, setShowSignIn] = useState(false);
  const [showSignUp, setShowSignUp] = useState(false);
  const router = useRouter();

  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      const user = await getCurrentUser();
      setIsAuthenticated(!!user);
    } catch (error) {
      setIsAuthenticated(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      setIsAuthenticated(false);
      router.push('/');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const handleClickOutside = (event: MouseEvent & { target: Element }): void => {
    if (!event.target.closest('.menu-items')) {
      setShowSignIn(false);
      setShowSignUp(false);
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
                  setShowSignUp(false);
                  setShowSignIn(!showSignIn);
                }}
                className="px-4 py-2 bg-blue-500 rounded hover:bg-blue-600"
              >
                Sign In
              </button>
              <button
                onClick={() => {
                  setShowSignIn(false);
                  setShowSignUp(!showSignUp);
                }}
                className="px-4 py-2 bg-green-500 rounded hover:bg-green-600"
              >
                Sign Up
              </button>

              <Menu as="div" className="relative inline-block" onClick={(event) => handleClickOutside(event)}>
                <Menu.Items
                  static
                  className={`${
                    showSignIn || showSignUp ? 'block' : 'hidden'
                  } absolute right-0 mt-2 w-80 origin-top-right bg-white rounded-md shadow-lg focus:outline-none`}
                >
                  {showSignIn && (
                    <SignInForm onClose={() => {
                      setShowSignIn(false);
                      checkAuthState();
                    }} />
                  )}
                  {showSignUp && (
                    <SignUpForm onClose={() => {
                      setShowSignUp(false);
                    }} />
                  )}
                </Menu.Items>
              </Menu>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
