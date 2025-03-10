"use client";

import { SearchMode } from "@/types/workbench";
import { MagnifyingGlassIcon, FunnelIcon, EyeIcon } from "@heroicons/react/24/outline";

interface SearchBarProps {
  searchQuery: string;
  searchMode: SearchMode;
  onSearchChange: (query: string) => void;
  onModeChange: (mode: SearchMode) => void;
}

export default function SearchBar({
  searchQuery,
  searchMode,
  onSearchChange,
  onModeChange,
}: SearchBarProps) {
  return (
    <div className="mb-6">
      <h2 className="text-sm font-semibold text-gray-700 mb-2">Search & Filter</h2>
      
      <div className="relative mb-2">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by AI labels..."
          className="w-full pl-10 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      
      <div className="flex space-x-2">
        <button
          onClick={() => onModeChange("find")}
          className={`flex items-center px-3 py-1.5 rounded-md text-xs ${
            searchMode === "find"
              ? "bg-blue-100 text-blue-800"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          } transition-colors`}
        >
          <FunnelIcon className="h-3 w-3 mr-1" />
          Find Mode
        </button>
        <button
          onClick={() => onModeChange("highlight")}
          className={`flex items-center px-3 py-1.5 rounded-md text-xs ${
            searchMode === "highlight"
              ? "bg-blue-100 text-blue-800"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          } transition-colors`}
        >
          <EyeIcon className="h-3 w-3 mr-1" />
          Highlight Mode
        </button>
      </div>
      
      <div className="mt-2 text-xs text-gray-500">
        {searchMode === "find" 
          ? "Find mode: Only matching photos are shown" 
          : "Highlight mode: All photos visible, matches highlighted"}
      </div>
    </div>
  );
}
