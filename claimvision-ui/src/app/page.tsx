"use client";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] bg-gray-50 px-4">
      <div className="text-center max-w-2xl mx-auto">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">
          ClaimVision
        </h1>

        <p className="text-lg text-gray-700 mb-4">
          Practical tools for organizing property damage claims.
        </p>

        <p className="text-base text-gray-600 mb-6">
          ClaimVision helps streamline documentation after a loss—upload photos, organize by room, tag items, and generate structured reports.
        </p>

        <p className="text-base text-gray-600 mb-6">
          Export reporting is in progress—early users can help shape how it works.
        </p>

        <p className="text-base text-gray-600 mb-6">
          Built from real-world experience to reduce friction, not add it.
        </p>

        <div className="mt-10 text-sm text-gray-400">
          Private by default. No noise. No nonsense.
        </div>
      </div>
    </div>
  );
}