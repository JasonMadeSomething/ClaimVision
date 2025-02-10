"use client";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] bg-gray-50">
      <div className="text-center max-w-2xl mx-auto px-4">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Welcome to ClaimVision
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          A seamless way to manage insurance claims with AI-powered automation.
        </p>
        <div className="space-y-4">
          <p className="text-gray-700">
            Get started by signing in or creating a new account.
          </p>
        </div>
      </div>
    </div>
  );
}
