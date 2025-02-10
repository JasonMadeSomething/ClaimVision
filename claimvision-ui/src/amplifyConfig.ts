import { Amplify } from 'aws-amplify';
import { cognitoUserPoolsTokenProvider } from '@aws-amplify/auth/cognito';

// Track configuration state
const isConfigured = { configured: false };

export function initializeAmplify() {
  if (isConfigured.configured) return;

  try {
    console.warn('[Amplify] 🚀 Initializing Amplify...');

    const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID;
    const userPoolClientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
    const region = process.env.NEXT_PUBLIC_AWS_REGION;
    const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY;

    if (!userPoolId || !userPoolClientId || !region || !apiUrl) {
      console.error('[Amplify] ❌ Missing Environment Variables:', {
        userPoolId,
        userPoolClientId,
        region,
        apiUrl
      });
      throw new Error('🚨 Required environment variables are missing!');
    }

    const config = {
      Auth: {
        Cognito: {
          userPoolId,
          userPoolClientId,
          region,
          tokenIncludes: ['id', 'access'],
          authenticationFlowType: 'USER_PASSWORD_AUTH'
        }
      },
      API: {
        REST: {
          ClaimVisionAPI: {
            endpoint: apiUrl,
            region,
            custom_header: async () => {
              try {
                const tokens = await cognitoUserPoolsTokenProvider.getTokens();
                console.warn('[Amplify] 🔑 Retrieved Tokens:', tokens);
                return {
                  Authorization: `Bearer ${tokens?.accessToken?.toString() || ''}`,
                  'Accept': 'application/json'
                };
              } catch (error) {
                console.error('[Amplify] ❌ Failed to fetch auth token:', error);
                return {};
              }
            }
          }
        }
      }
    };

    console.warn('[Amplify] ✅ Amplify Configuration:', config);
    Amplify.configure(config);

    isConfigured.configured = true;
    console.warn('[Amplify] 🎉 Amplify configured successfully!');
  } catch (error) {
    console.error('[Amplify] ❌ Error Configuring Amplify:', error);
    throw error;
  }
}
