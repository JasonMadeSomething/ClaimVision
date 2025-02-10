console.log("AWS REGION:", process.env.NEXT_PUBLIC_AWS_REGION);
console.log("COGNITO USER POOL ID:", process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID);
console.log("COGNITO CLIENT ID:", process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID);
console.log("API GATEWAY:", process.env.NEXT_PUBLIC_API_GATEWAY);


const awsExports = {
  Auth: {
    region: process.env.NEXT_PUBLIC_AWS_REGION!,
    userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
    userPoolWebClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
    signUpVerificationMethod: "code",
  },
  API: {
    endpoints: [
      {
        name: "ClaimVisionAPI",
        endpoint: process.env.NEXT_PUBLIC_API_GATEWAY!,
        region: process.env.NEXT_PUBLIC_AWS_REGION!,
      },
    ],
  },
  ssr: true,
};

export default awsExports;
