"use client";

import { PlusIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { Room, PREDEFINED_ROOM_TYPES, PredefinedRoomType } from "@/types/workbench";
import { useState, useRef, useEffect } from "react";
import { useDrop } from "react-dnd";

interface RoomSelectorProps {
  rooms: Room[];
  selectedRoom: Room | null;
  onSelectRoom: (room: Room | null) => void;
  onMovePhotoToRoom?: (photoId: string, roomId: string | null) => void;
  onMoveItemToRoom?: (itemId: string, roomId: string | null) => void;
  onCreateRoom?: (roomName: string, roomType: string) => Promise<void>;
  onDeleteRoom?: (roomId: string) => Promise<void>;
  claimId?: string | undefined;
}

// Room button with drop target
const RoomButton = ({ 
  room, 
  isSelected, 
  onClick, 
  onPhotoDrop,
  onItemDrop,
  onDelete,
  isEmpty
}: { 
  room: Room; 
  isSelected: boolean; 
  onClick: () => void; 
  onPhotoDrop: (photoId: string) => void;
  onItemDrop: (itemId: string) => void;
  onDelete?: () => void;
  isEmpty: boolean;
}) => {
  const roomRef = useRef<HTMLButtonElement>(null);
  const [{ isOver }, drop] = useDrop({
    accept: ['PHOTO', 'ITEM'],
    drop: (item: any) => {
      console.log("Item dropped on room:", item);
      console.log(`Item type: ${item.type}, Item ID: ${item.id}, Room ID: ${room.id}`);
      
      // Check if the item has a type property
      if (!item.type) {
        console.error("Dropped item has no type property:", item);
        return { dropped: true };
      }
      
      if (item.type === 'PHOTO') {
        onPhotoDrop(item.id);
      } else if (item.type === 'ITEM') {
        onItemDrop(item.id);
      } else {
        console.warn(`Unknown item type: ${item.type}`);
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

  // Find matching predefined room type for icon
  const roomType = PREDEFINED_ROOM_TYPES.find(
    type => {
      const roomNameLower = room.name.toLowerCase();
      const typeNameLower = type.name.toLowerCase();
      const typeIdLower = type.id.toLowerCase();
      
      // Try to match by exact name first
      if (roomNameLower === typeNameLower) {
        return true;
      }
      
      // Then try partial matches
      if (roomNameLower.includes(typeIdLower) || 
          typeIdLower.includes(roomNameLower) ||
          roomNameLower.includes(typeNameLower) ||
          typeNameLower.includes(roomNameLower)) {
        return true;
      }
      
      return false;
    }
  ) || PREDEFINED_ROOM_TYPES[PREDEFINED_ROOM_TYPES.length - 1]; // Default to "Other"

  return (
    <div className="relative group">
      <button
        ref={roomRef}
        onClick={onClick}
        className={`w-full text-left px-3 py-2 rounded-md text-sm ${
          isSelected
            ? "bg-blue-100 text-blue-800"
            : "text-gray-700 hover:bg-gray-100"
        } ${isOver ? "bg-gray-200" : ""} transition-colors flex items-center`}
      >
        <span className="mr-2">{roomType.icon}</span>
        <span className="flex-grow">{room.name}</span>
        <span className="ml-2 text-xs text-gray-500">
          {room.itemIds?.length > 0 && (
            <span>
              {room.itemIds.length} items
            </span>
          )}
          {room.fileIds && room.fileIds.length > 0 && (
            <span>
              {room.fileIds.length} files
            </span>
          )}
          {(!room.itemIds || room.itemIds.length === 0) && 
           (!room.fileIds || room.fileIds.length === 0) && (
            <span>Empty</span>
          )}
        </span>
      </button>
      
      {isEmpty && onDelete && (
        <button 
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-full hover:bg-red-100 text-red-500"
          title="Delete room"
        >
          <XMarkIcon className="h-4 w-4" />
        </button>
      )}
    </div>
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
      } ${isOver ? "bg-gray-200" : ""} transition-colors flex items-center`}
    >
      <span className="mr-2">🏠</span>
      <span>Main Workbench</span>
    </button>
  );
};

export default function RoomSelector({ 
  rooms, 
  selectedRoom, 
  onSelectRoom, 
  onMovePhotoToRoom, 
  onMoveItemToRoom,
  onCreateRoom,
  onDeleteRoom,
  claimId
}: RoomSelectorProps) {
  const [isAddingRoom, setIsAddingRoom] = useState(false);
  const [selectedRoomType, setSelectedRoomType] = useState<PredefinedRoomType | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get list of room types that haven't been added yet
  const availableRoomTypes = PREDEFINED_ROOM_TYPES.filter(roomType => {
    return !rooms.some(room => {
      const roomNameLower = room.name.toLowerCase();
      const typeNameLower = roomType.name.toLowerCase();
      const typeIdLower = roomType.id.toLowerCase();
      
      // Check for exact name match
      if (roomNameLower === typeNameLower) {
        return true;
      }
      
      // Check for partial matches
      if (roomNameLower.includes(typeIdLower) || 
          typeIdLower.includes(roomNameLower) ||
          roomNameLower.includes(typeNameLower) ||
          typeNameLower.includes(roomNameLower)) {
        return true;
      }
      
      return false;
    });
  });

  const handleAddRoom = async () => {
    if (!selectedRoomType || !onCreateRoom) {
      setError("Unable to create room. Missing room type or creation function.");
      return;
    }

    if (!claimId) {
      setError("Unable to create room. Missing claim ID.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await onCreateRoom(selectedRoomType.name, selectedRoomType.id);
      setSelectedRoomType(null);
      setIsAddingRoom(false);
    } catch (err) {
      setError("Failed to create room. Please try again.");
      console.error("Error creating room:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteRoom = async (roomId: string) => {
    if (!onDeleteRoom) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      await onDeleteRoom(roomId);
      // If the deleted room was selected, go back to main workbench
      if (selectedRoom?.id === roomId) {
        onSelectRoom(null);
      }
    } catch (err) {
      setError("Failed to delete room. Please try again.");
      console.error("Error deleting room:", err);
    } finally {
      setIsLoading(false);
    }
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
          disabled={availableRoomTypes.length === 0 || isLoading}
        >
          <PlusIcon className="h-4 w-4 text-gray-500" />
        </button>
      </div>

      {error && (
        <div className="mb-3 text-xs text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      {isAddingRoom ? (
        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Select Room Type
          </label>
          <select
            value={selectedRoomType?.id || ""}
            onChange={(e) => {
              const selected = PREDEFINED_ROOM_TYPES.find(room => room.id === e.target.value);
              setSelectedRoomType(selected || null);
            }}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          >
            <option value="">Select a room type</option>
            {availableRoomTypes.map(roomType => (
              <option key={roomType.id} value={roomType.id}>
                {roomType.icon} {roomType.name}
              </option>
            ))}
          </select>
          
          <div className="flex space-x-2 mt-2">
            <button
              onClick={handleAddRoom}
              disabled={!selectedRoomType || isLoading}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
            >
              {isLoading ? "Adding..." : "Add Room"}
            </button>
            <button
              onClick={() => {
                setSelectedRoomType(null);
                setIsAddingRoom(false);
                setError(null);
              }}
              className="px-3 py-1 text-xs border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
              disabled={isLoading}
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
        
        {rooms.map((room) => {
          // Check if room is empty (no items or files)
          const isEmpty = !room.itemIds || room.itemIds.length === 0;
          
          return (
            <RoomButton
              key={room.id}
              room={room}
              isSelected={selectedRoom?.id === room.id}
              onClick={() => onSelectRoom(room)}
              onPhotoDrop={(photoId) => handleDropOnRoom(room.id, photoId)}
              onItemDrop={(itemId) => handleDropItemOnRoom(room.id, itemId)}
              onDelete={isEmpty ? () => handleDeleteRoom(room.id) : undefined}
              isEmpty={isEmpty}
            />
          );
        })}
      </div>
    </div>
  );
}
