"use client";

import { PlusIcon } from "@heroicons/react/24/outline";
import { Room } from "@/types/workbench";
import { useState, useRef, useEffect } from "react";
import { useDrop } from "react-dnd";

interface RoomSelectorProps {
  rooms: Room[];
  selectedRoom: Room | null;
  onSelectRoom: (room: Room | null) => void;
  onMovePhotoToRoom?: (photoId: string, roomId: string | null) => void;
  onMoveItemToRoom?: (itemId: string, roomId: string | null) => void;
}

// Room button with drop target
const RoomButton = ({ 
  room, 
  isSelected, 
  onClick, 
  onPhotoDrop,
  onItemDrop
}: { 
  room: Room; 
  isSelected: boolean; 
  onClick: () => void; 
  onPhotoDrop: (photoId: string) => void;
  onItemDrop: (itemId: string) => void;
}) => {
  const roomRef = useRef<HTMLButtonElement>(null);
  const [{ isOver }, drop] = useDrop({
    accept: ['PHOTO', 'ITEM'],
    drop: (item: { id: string, type: string }) => {
      console.log(`${item.type} dropped on room ${room.id}:`, item.id);
      if (item.type === 'PHOTO') {
        onPhotoDrop(item.id);
      } else if (item.type === 'ITEM') {
        onItemDrop(item.id);
      }
      return { dropped: true };
    },
    collect: (monitor) => ({
      isOver: !!monitor.isOver(),
    }),
  });

  // Connect the room drop ref
  useEffect(() => {
    drop(roomRef.current);
  }, [drop]);

  return (
    <button
      ref={roomRef}
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-md text-sm ${
        isSelected
          ? "bg-blue-100 text-blue-800"
          : "text-gray-700 hover:bg-gray-100"
      } ${isOver ? "bg-gray-200" : ""} transition-colors`}
    >
      {room.name}
      <span className="ml-2 text-xs text-gray-500">
        ({room.itemIds.length})
      </span>
    </button>
  );
};

// Main workbench button with drop target
const MainWorkbenchButton = ({ 
  isSelected, 
  onClick, 
  onPhotoDrop,
  onItemDrop
}: { 
  isSelected: boolean; 
  onClick: () => void; 
  onPhotoDrop: (photoId: string) => void;
  onItemDrop: (itemId: string) => void;
}) => {
  const mainWorkbenchRef = useRef<HTMLButtonElement>(null);
  const [{ isOver }, drop] = useDrop({
    accept: ['PHOTO', 'ITEM'],
    drop: (item: { id: string, type: string }) => {
      console.log(`${item.type} dropped on main workbench:`, item.id);
      if (item.type === 'PHOTO') {
        onPhotoDrop(item.id);
      } else if (item.type === 'ITEM') {
        onItemDrop(item.id);
      }
      return { dropped: true };
    },
    collect: (monitor) => ({
      isOver: !!monitor.isOver(),
    }),
  });

  // Connect the main workbench drop ref
  useEffect(() => {
    drop(mainWorkbenchRef.current);
  }, [drop]);

  return (
    <button
      ref={mainWorkbenchRef}
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-md text-sm ${
        isSelected
          ? "bg-blue-100 text-blue-800"
          : "text-gray-700 hover:bg-gray-100"
      } ${isOver ? "bg-gray-200" : ""} transition-colors`}
    >
      Main Workbench
    </button>
  );
};

export default function RoomSelector({ rooms, selectedRoom, onSelectRoom, onMovePhotoToRoom, onMoveItemToRoom }: RoomSelectorProps) {
  const [isAddingRoom, setIsAddingRoom] = useState(false);
  const [newRoomName, setNewRoomName] = useState("");

  const handleAddRoom = () => {
    // This would call an API to create a room in a real implementation
    alert(`Would create a new room: ${newRoomName}`);
    setNewRoomName("");
    setIsAddingRoom(false);
  };

  const handleDropOnMainWorkbench = (photoId: string) => {
    if (onMovePhotoToRoom) {
      onMovePhotoToRoom(photoId, null);
    }
  };

  const handleDropOnRoom = (roomId: string, photoId: string) => {
    if (onMovePhotoToRoom) {
      onMovePhotoToRoom(photoId, roomId);
    }
  };

  const handleDropItemOnMainWorkbench = (itemId: string) => {
    if (onMoveItemToRoom) {
      onMoveItemToRoom(itemId, null);
    }
  };

  const handleDropItemOnRoom = (roomId: string, itemId: string) => {
    if (onMoveItemToRoom) {
      onMoveItemToRoom(itemId, roomId);
    }
  };

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-gray-700">Rooms</h2>
        <button
          onClick={() => setIsAddingRoom(true)}
          className="p-1 rounded-full hover:bg-gray-100 transition-colors"
          aria-label="Add room"
        >
          <PlusIcon className="h-4 w-4 text-gray-500" />
        </button>
      </div>

      {isAddingRoom ? (
        <div className="mb-3">
          <input
            type="text"
            value={newRoomName}
            onChange={(e) => setNewRoomName(e.target.value)}
            placeholder="Room name"
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          <div className="flex space-x-2 mt-2">
            <button
              onClick={handleAddRoom}
              disabled={!newRoomName.trim()}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-blue-300"
            >
              Add
            </button>
            <button
              onClick={() => {
                setNewRoomName("");
                setIsAddingRoom(false);
              }}
              className="px-3 py-1 text-xs border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      <div className="space-y-1">
        <MainWorkbenchButton
          isSelected={selectedRoom === null}
          onClick={() => onSelectRoom(null)}
          onPhotoDrop={handleDropOnMainWorkbench}
          onItemDrop={handleDropItemOnMainWorkbench}
        />
        
        {rooms.map((room) => (
          <RoomButton
            key={room.id}
            room={room}
            isSelected={selectedRoom?.id === room.id}
            onClick={() => onSelectRoom(room)}
            onPhotoDrop={(photoId) => handleDropOnRoom(room.id, photoId)}
            onItemDrop={(itemId) => handleDropItemOnRoom(room.id, itemId)}
          />
        ))}
      </div>
    </div>
  );
}
