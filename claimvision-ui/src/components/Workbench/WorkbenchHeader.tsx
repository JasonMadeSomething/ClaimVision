"use client";

import { Room } from "@/types/workbench";
import { ArrowLeftIcon } from "@heroicons/react/24/outline";
import { PlusIcon } from "@heroicons/react/24/outline";

interface WorkbenchHeaderProps {
  selectedRoom: Room | null;
  onBackToWorkbench: () => void;
  onCreateEmptyItem: () => void;
}

export default function WorkbenchHeader({ 
  selectedRoom, 
  onBackToWorkbench,
  onCreateEmptyItem,
}: WorkbenchHeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          {selectedRoom && (
            <button
              onClick={onBackToWorkbench}
              className="mr-4 p-2 rounded-full hover:bg-gray-100"
            >
              <ArrowLeftIcon className="h-5 w-5 text-gray-500" />
            </button>
          )}
          <h1 className="text-xl font-semibold text-gray-900">
            {selectedRoom ? selectedRoom.name : "Main Workbench"}
          </h1>
        </div>
        <div className="flex items-center space-x-4">
          <button
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            onClick={() => {
              // TODO: Implement photo upload
            }}
          >
            Upload Photos
          </button>
          <button
            onClick={onCreateEmptyItem}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            New Item
          </button>
        </div>
      </div>
    </header>
  );
}
