"use client";

import { Room } from "@/types/workbench";
import { ArrowLeftIcon, DocumentTextIcon } from "@heroicons/react/24/outline";

interface WorkbenchHeaderProps {
  selectedRoom: Room | null;
  onBackToWorkbench: () => void;
  onRequestReport?: () => void;
}

export default function WorkbenchHeader({ 
  selectedRoom, 
  onBackToWorkbench,
  onRequestReport,
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
          {onRequestReport && (
            <button
              onClick={onRequestReport}
              className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <DocumentTextIcon className="h-5 w-5 mr-2" />
              Generate Report
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
