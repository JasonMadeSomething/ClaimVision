// context/AuthContext.tsx
"use client";
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { signOut as amplifySignOut, getCurrentUser, fetchAuthSession, type AuthUser } from '@aws-amplify/auth';
import { Amplify } from 'aws-amplify';

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

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<UserData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionRefreshed, setSessionRefreshed] = useState(false);

  // Use useCallback to memoize the refreshSession function
  const refreshSession = useCallback(async () => {
    // Skip if we've already refreshed the session
    if (sessionRefreshed) {
      console.log("AuthContext: Session already refreshed, skipping");
      return;
    }

    try {
      console.log("AuthContext: Refreshing session...");
      setIsLoading(true);
      
      // Try to fetch the auth session to check if we have valid tokens
      const session = await fetchAuthSession();
      console.log("AuthContext: Session valid:", !!session.tokens);
      
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
          console.log("AuthContext: Extracted user data from token:", { 
            user_id: userData.user_id,
            household_id: userData.household_id
          });
        } catch (e) {
          console.error("AuthContext: Failed to extract user data from token:", e);
        }
        
        setUser(userData);
        setSessionRefreshed(true);
      } else {
        throw new Error("No valid tokens found");
      }
    } catch (error) {
      console.log("AuthContext: No valid session found:", error);
      setUser(null);
      
      // Clear any stale data
      if (typeof window !== 'undefined') {
        localStorage.removeItem('amplify-signin-with-hostedUI');
        Object.keys(localStorage)
          .filter(key => key.startsWith('amplify') || key.startsWith('CognitoIdentityServiceProvider'))
          .forEach(key => {
            console.log("AuthContext: Removing stale localStorage item:", key);
            localStorage.removeItem(key);
          });
      }
    } finally {
      setIsLoading(false);
    }
  }, [sessionRefreshed]);

  // Check for user on initial load only
  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const handleSetUser = async (userData: UserData | null) => {
    console.log("AuthContext: Setting user:", userData);
    
    if (userData) {
      // Configure Amplify with the tokens we received from the API
      if (userData.id_token && userData.access_token) {
        try {
          // Try to extract user_id and household_id from the token if not already present
          if (!userData.user_id || !userData.household_id) {
            try {
              const payload = JSON.parse(atob(userData.id_token.split('.')[1]));
              userData.user_id = userData.user_id || payload.sub;
              userData.household_id = userData.household_id || payload.household_id;
              console.log("AuthContext: Extracted user data from token:", { 
                user_id: userData.user_id,
                household_id: userData.household_id
              });
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
            console.log("AuthContext: Stored tokens in localStorage");
          } catch (e) {
            console.error("AuthContext: Failed to store tokens in localStorage:", e);
          }
          
          setUser(userData);
          setSessionRefreshed(true);
          console.log("AuthContext: User authenticated successfully");
        } catch (error) {
          console.error("AuthContext: Error configuring Amplify with tokens:", error);
        }
      }
    } else {
      setUser(null);
      setSessionRefreshed(false);
    }
  };

  const signOut = async () => {
    console.log("AuthContext: Signing out...");
    try {
      await amplifySignOut({ global: true });
      console.log("AuthContext: Sign out successful");
      setUser(null);
      setSessionRefreshed(false);
      
      // Clear any persisted session data from localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('amplify-signin-with-hostedUI');
        Object.keys(localStorage)
          .filter(key => key.startsWith('amplify') || key.startsWith('CognitoIdentityServiceProvider'))
          .forEach(key => {
            console.log("AuthContext: Removing localStorage item:", key);
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
