import { Amplify } from 'aws-amplify';
import { cognitoUserPoolsTokenProvider } from '@aws-amplify/auth/cognito';

// Track configuration state
const isConfigured = { configured: false };

export function initializeAmplify() {
  if (isConfigured.configured) return;

  try {
    // Initialization starting

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

    Amplify.configure(config);

    isConfigured.configured = true;
  } catch (error) {
    console.error('[Amplify] ❌ Error Configuring Amplify:', error);
    throw error;
  }
}
