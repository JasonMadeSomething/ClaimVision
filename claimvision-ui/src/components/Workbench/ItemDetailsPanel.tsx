import { useState, useRef, useEffect } from "react";
import { XMarkIcon, ArrowPathIcon, HomeIcon, ArrowsRightLeftIcon } from "@heroicons/react/24/outline";
import { Item, Photo, Room } from "@/types/workbench";

interface ItemDetailsPanelProps {
  item: Item;
  photos: Photo[];
  rooms: Room[];
  onClose: () => void;
  onUpdate: (item: Item) => void;
  onRemovePhoto: (photoId: string) => void;
  onChangeThumbnail: () => void;
  onMoveToRoom: (roomId: string | null) => void;
}

interface EditableFieldProps {
  value: string;
  onSave: (value: string) => void;
  placeholder?: string;
  multiline?: boolean;
}

const EditableField = ({ value, onSave, placeholder, multiline }: EditableFieldProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleSave = () => {
    if (editValue !== value) {
      onSave(editValue);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    }
    if (e.key === 'Escape') {
      setEditValue(value);
      setIsEditing(false);
    }
  };

  if (isEditing) {
    if (multiline) {
      return (
        <textarea
          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          className="w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={3}
          placeholder={placeholder}
        />
      );
    }
    return (
      <input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        type="text"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className="w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        placeholder={placeholder}
      />
    );
  }

  return (
    <div
      onClick={() => setIsEditing(true)}
      className="cursor-pointer p-2 rounded-md hover:bg-gray-100"
    >
      {value || <span className="text-gray-400">{placeholder}</span>}
    </div>
  );
};

export default function ItemDetailsPanel({
  item,
  photos,
  rooms,
  onClose,
  onUpdate,
  onRemovePhoto,
  onChangeThumbnail,
  onMoveToRoom
}: ItemDetailsPanelProps) {
  const handleUpdateField = (field: keyof Item, value: any) => {
    onUpdate({
      ...item,
      [field]: value,
    });
  };

  const thumbnailPhoto = photos.find(p => p.id === item.thumbnailPhotoId);

  return (
    <div className="w-96 border-l border-gray-200 bg-white overflow-y-auto h-full shadow-lg">
      <div className="sticky top-0 bg-white z-10 border-b border-gray-200">
        <div className="flex justify-between items-center p-4">
          <h2 className="text-lg font-semibold text-gray-800">Item Details</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-gray-100 transition-colors"
            aria-label="Close panel"
          >
            <XMarkIcon className="h-5 w-5 text-gray-500" />
          </button>
        </div>
      </div>

      <div className="p-4">
        {/* Thumbnail section */}
        <div className="mb-6 relative">
          {thumbnailPhoto ? (
            <div className="relative rounded-lg overflow-hidden h-48">
              <img
                src={thumbnailPhoto.url}
                alt={item.name}
                className="w-full h-full object-cover"
              />
              <button
                onClick={onChangeThumbnail}
                className="absolute bottom-2 right-2 p-2 bg-white rounded-full shadow-md hover:bg-gray-100 transition-colors"
                aria-label="Change thumbnail"
              >
                <ArrowPathIcon className="h-5 w-5 text-gray-700" />
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 bg-gray-100 rounded-lg">
              <p className="text-gray-500">No thumbnail available</p>
            </div>
          )}
        </div>

        {/* Item details form */}
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <EditableField
              value={item.name}
              onSave={(value) => handleUpdateField('name', value)}
              placeholder="Enter a name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <EditableField
              value={item.description}
              onSave={(value) => handleUpdateField('description', value)}
              placeholder="Enter a description"
              multiline
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Replacement Value ($)
            </label>
            <EditableField
              value={item.replacementValue.toString()}
              onSave={(value) => handleUpdateField('replacementValue', parseFloat(value) || 0)}
              placeholder="Enter a replacement value"
            />
          </div>
        </div>

        {/* Room assignment */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Room Assignment</h4>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => onMoveToRoom(null)}
              className={`flex items-center px-3 py-2 rounded-md text-sm ${
                item.roomId === null
                  ? "bg-blue-100 text-blue-800"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              } transition-colors`}
            >
              <HomeIcon className="h-4 w-4 mr-1" />
              Workbench
            </button>
            {rooms.map((room) => (
              <button
                key={room.id}
                onClick={() => onMoveToRoom(room.id)}
                className={`flex items-center px-3 py-2 rounded-md text-sm ${
                  item.roomId === room.id
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                } transition-colors`}
              >
                <ArrowsRightLeftIcon className="h-4 w-4 mr-1" />
                {room.name}
              </button>
            ))}
          </div>
        </div>

        {/* Photos section */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Photos ({photos.length})</h4>
          <div className="grid grid-cols-2 gap-2">
            {photos.map((photo) => (
              <div key={photo.id} className="relative group">
                <img
                  src={photo.url}
                  alt={photo.fileName}
                  className="w-full h-24 object-cover rounded-md"
                />
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200 rounded-md">
                  <button
                    onClick={() => onRemovePhoto(photo.id)}
                    className="absolute top-1 right-1 p-1 bg-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="Remove photo from item"
                  >
                    <XMarkIcon className="h-4 w-4 text-gray-700" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
