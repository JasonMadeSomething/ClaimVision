// context/AuthContext.tsx
"use client";
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { signOut as amplifySignOut, fetchAuthSession } from '@aws-amplify/auth';
import { usePathname, useRouter } from 'next/navigation';

// Define the AuthTokens type to include refreshToken
interface AuthTokens {
  accessToken: {
    toString(): string;
  };
  idToken?: {
    toString(): string;
  };
  refreshToken?: {
    toString(): string;
  };
}

// Define types for our auth context
type UserData = {
  user_id?: string;
  household_id?: string;
  access_token: string;
  id_token: string;
  refresh_token: string;
};

type AuthContextType = {
  user: UserData | null;
  setUser: (userData: UserData | null) => void;
  signOut: () => Promise<void>;
  isLoading: boolean;
  refreshSession: () => Promise<void>;
};

// Create context with proper typing
const AuthContext = createContext<AuthContextType | null>(null);

// Helper to store user data in localStorage
const storeUserData = (userData: UserData) => {
  if (typeof window === 'undefined') return;
  
  localStorage.setItem('claimvision_user', JSON.stringify(userData));
  console.warn("AuthContext: Stored user data in localStorage");
};

// Helper to retrieve user data from localStorage
const retrieveUserData = (): UserData | null => {
  if (typeof window === 'undefined') return null;
  
  const storedUser = localStorage.getItem('claimvision_user');
  if (!storedUser) return null;
  
  try {
    return JSON.parse(storedUser) as UserData;
  } catch (e) {
    console.error("AuthContext: Failed to parse stored user data:", e);
    return null;
  }
};

// Helper to store current path
const storeCurrentPath = (path: string) => {
  if (typeof window === 'undefined' || !path || path === '/') return;
  localStorage.setItem('claimvision_last_path', path);
  console.warn("AuthContext: Stored current path:", path);
};

// Helper to retrieve last path
const retrieveLastPath = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('claimvision_last_path');
};

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<UserData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionRefreshed, setSessionRefreshed] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  // Store current path whenever it changes and user is authenticated
  useEffect(() => {
    if (user && pathname && !isLoading) {
      storeCurrentPath(pathname);
    }
  }, [pathname, user, isLoading]);

  // Use useCallback to memoize the refreshSession function
  const refreshSession = useCallback(async () => {
    // Skip if we've already refreshed the session
    if (sessionRefreshed) {
      console.warn("AuthContext: Session already refreshed, skipping");
      return;
    }

    try {
      console.warn("AuthContext: Refreshing session...");
      setIsLoading(true);
      
      // First try to get user data from localStorage
      const storedUser = retrieveUserData();
      
      if (storedUser) {
        console.warn("AuthContext: Found stored user data");
        
        // Check if the token is still valid by checking expiration
        try {
          const payload = JSON.parse(atob(storedUser.id_token.split('.')[1]));
          const expTime = payload.exp * 1000; // Convert to milliseconds
          
          if (expTime > Date.now()) {
            console.warn("AuthContext: Token is still valid, expires at:", new Date(expTime).toISOString());
            setUser(storedUser);
            setSessionRefreshed(true);
            
            // After a short delay, restore the last path if we're on the home page
            if (pathname === '/') {
              setTimeout(() => {
                const lastPath = retrieveLastPath();
                if (lastPath && lastPath !== '/') {
                  console.warn("AuthContext: Restoring last path:", lastPath);
                  router.push(lastPath);
                }
              }, 100);
            }
            
            setIsLoading(false);
            return;
          } else {
            console.warn("AuthContext: Token has expired, clearing session");
            localStorage.removeItem('claimvision_user');
          }
        } catch (e) {
          console.error("AuthContext: Failed to parse token:", e);
        }
      }
      
      // If we don't have stored user data or the token is invalid, try Amplify
      try {
        // Try to fetch the auth session to check if we have valid tokens
        const session = await fetchAuthSession();
        console.warn("AuthContext: Session valid:", !!session.tokens);
        
        if (session.tokens) {
          // If we have tokens, we're authenticated
          const tokens = session.tokens as AuthTokens;
          const userData: UserData = {
            access_token: tokens.accessToken.toString(),
            id_token: tokens.idToken?.toString() || '',
            refresh_token: tokens.refreshToken?.toString() || ''
          };
          
          // Try to extract user_id and household_id from the token
          try {
            const payload = JSON.parse(atob(userData.id_token.split('.')[1]));
            userData.user_id = payload.sub;
            userData.household_id = payload.household_id;
            console.warn("AuthContext: Extracted user data from token:", { 
              user_id: userData.user_id,
              household_id: userData.household_id
            });
          } catch (e) {
            console.error("AuthContext: Failed to extract user data from token:", e);
          }
          
          setUser(userData);
          storeUserData(userData);
          setSessionRefreshed(true);
          
          // After a short delay, restore the last path if we're on the home page
          if (pathname === '/') {
            setTimeout(() => {
              const lastPath = retrieveLastPath();
              if (lastPath && lastPath !== '/') {
                console.warn("AuthContext: Restoring last path:", lastPath);
                router.push(lastPath);
              }
            }, 100);
          }
        } else {
          throw new Error("No valid tokens found");
        }
      } catch (error) {
        console.error("AuthContext: No valid session found:", error);
        setUser(null);
        
        // Clear any stale data
        if (typeof window !== 'undefined') {
          localStorage.removeItem('claimvision_user');
          localStorage.removeItem('amplify-signin-with-hostedUI');
          Object.keys(localStorage)
            .filter(key => key.startsWith('amplify') || key.startsWith('CognitoIdentityServiceProvider'))
            .forEach(key => {
              console.warn("AuthContext: Removing stale localStorage item:", key);
              localStorage.removeItem(key);
            });
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, [sessionRefreshed, pathname, router]);

  // Check for user on initial load only
  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const handleSetUser = async (userData: UserData | null) => {
    console.warn("AuthContext: Setting user:", { hasIdToken: !!userData?.id_token, hasAccessToken: !!userData?.access_token });
    
    if (userData) {
      // Store the user data in localStorage for persistence
      storeUserData(userData);
      
      // Configure Amplify with the tokens we received from the API
      if (userData.id_token && userData.access_token) {
        try {
          // Try to extract user_id and household_id from the token if not already present
          if (!userData.user_id || !userData.household_id) {
            try {
              const payload = JSON.parse(atob(userData.id_token.split('.')[1]));
              userData.user_id = userData.user_id || payload.sub;
              userData.household_id = userData.household_id || payload.household_id;
              console.warn("AuthContext: Extracted user data from token:", { 
                user_id: userData.user_id,
                household_id: userData.household_id
              });
              
              // Update the stored user data with the extracted information
              storeUserData(userData);
            } catch (e) {
              console.error("AuthContext: Failed to extract user data from token:", e);
            }
          }
          
          // Store tokens in localStorage for Amplify to find
          localStorage.setItem('amplify-authenticator-authState', 'signedIn');
          
          // Configure Amplify with the tokens
          try {
            // This is a workaround to manually set the tokens in Amplify's storage
            const cognitoKey = `CognitoIdentityServiceProvider.${process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID}.${userData.user_id || 'LastAuthUser'}`;
            localStorage.setItem(cognitoKey, userData.user_id || '');
            localStorage.setItem(`${cognitoKey}.idToken`, userData.id_token);
            localStorage.setItem(`${cognitoKey}.accessToken`, userData.access_token);
            localStorage.setItem(`${cognitoKey}.refreshToken`, userData.refresh_token);
            console.warn("AuthContext: Stored tokens in localStorage");
          } catch (e) {
            console.error("AuthContext: Failed to store tokens in localStorage:", e);
          }
          
          setUser(userData);
          setSessionRefreshed(true);
          console.warn("AuthContext: User authenticated successfully");
        } catch (error) {
          console.error("AuthContext: Error configuring Amplify with tokens:", error);
        }
      }
    } else {
      // Clear user data from localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('claimvision_user');
      }
      
      setUser(null);
      setSessionRefreshed(false);
    }
  };

  const signOut = async () => {
    console.warn("AuthContext: Signing out...");
    try {
      await amplifySignOut({ global: true });
      console.warn("AuthContext: Sign out successful");
      setUser(null);
      setSessionRefreshed(false);
      
      // Clear any persisted session data from localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('claimvision_user');
        localStorage.removeItem('claimvision_last_path');
        localStorage.removeItem('amplify-signin-with-hostedUI');
        Object.keys(localStorage)
          .filter(key => key.startsWith('amplify') || key.startsWith('CognitoIdentityServiceProvider'))
          .forEach(key => {
            console.warn("AuthContext: Removing localStorage item:", key);
            localStorage.removeItem(key);
          });
      }
    } catch (error) {
      console.error("AuthContext: Error signing out:", error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ user, setUser: handleSetUser, signOut, isLoading, refreshSession }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
