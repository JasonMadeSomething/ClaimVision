"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Photo, Item, Room, SearchMode } from "@/types/workbench";
import { useSettingsStore } from "@/stores/settingsStore";
import { useAuth } from '@/context/AuthContext';
import WorkbenchHeader from "./WorkbenchHeader";
import PhotoGrid from "./PhotoGrid";
import ItemDetailsPanel from "./ItemDetailsPanel";
import RoomSelector from "./RoomSelector";
import SearchBar from "./SearchBar";
import FileUploader from './FileUploader';

export default function WorkbenchLayout() {
  const router = useRouter();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>(SearchMode.Highlight);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [claimId, setClaimId] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const { user } = useAuth();

  const { autoOpenDetailPanel } = useSettingsStore();

  // Get claim_id from URL if present
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const claimIdParam = urlParams.get('claim_id');
    if (claimIdParam) {
      setClaimId(claimIdParam);
    }
  }, []);

  // Fetch photos, items, and rooms on component mount
  useEffect(() => {
    if (!claimId || !user?.id_token) return;
    const fetchData = async (token: string) => {
      try {
        if (!user) {
          router.push('/');
          return;
        }
        
        setIsLoading(true);
    
        const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
        
        // If we have a claim_id, fetch data for that specific claim
        const roomsEndpoint = `${baseUrl}/claims/${claimId}/rooms`;
        const itemsEndpoint = `${baseUrl}/claims/${claimId}/items`;
        const filesEndpoint = `${baseUrl}/claims/${claimId}/files`;

        try {
          const [roomsRes, itemsRes, photosRes] = await Promise.all([
            fetch(roomsEndpoint, { headers: { Authorization: `Bearer ${token}` } }),
            fetch(itemsEndpoint, { headers: { Authorization: `Bearer ${token}` } }),
            fetch(filesEndpoint, { headers: { Authorization: `Bearer ${token}` } }),
          ]);

          if (!roomsRes.ok || !itemsRes.ok || !photosRes.ok) {
            throw new Error("Failed to fetch some resources");
          }

          const [roomsJson, itemsJson, photosJson] = await Promise.all([
            roomsRes.json(),
            itemsRes.json(),
            photosRes.json(),
          ]);

          // Set rooms safely
          const safeRooms = Array.isArray(roomsJson?.data?.rooms)
            ? roomsJson.data.rooms
            : [];
          if (!Array.isArray(roomsJson?.data?.rooms)) {
            console.warn("Malformed rooms response:", roomsJson);
          }
          setRooms(safeRooms);

          // Set items safely
          const safeItems = Array.isArray(itemsJson?.data?.items)
            ? itemsJson.data.items
            : [];
          if (!Array.isArray(itemsJson?.data?.items)) {
            console.warn("Malformed items response:", itemsJson);
          }
          setItems(safeItems);

          // Set photos safely
          const safePhotos = Array.isArray(photosJson?.data?.files)
            ? photosJson.data.files
            : Array.isArray(photosJson)
            ? photosJson
            : [];
          if (!Array.isArray(photosJson?.data?.files) && !Array.isArray(photosJson)) {
            console.warn("Malformed photos response:", photosJson);
          }
          setPhotos(safePhotos);
          console.log("Photos set:", safePhotos);
        } catch (err) {
          console.error("Error fetching claim data:", err);
          // Optional: Show toast or UI fallback state
          setRooms([]);
          setItems([]);
          setPhotos([]);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchData(user.id_token);
  }, [claimId, user?.id_token]);

  // Filter photos based on search query and mode
  const filteredPhotos = photos.filter(photo => {
    if (!searchQuery) return true;
    
    const matchesSearch = photo.labels.some(label => 
      label.toLowerCase().includes(searchQuery.toLowerCase())
    );
    
    if (searchMode === SearchMode.Find) {
      return matchesSearch;
    } else {
      // In highlight mode, we show all photos but will style them differently in the UI
      return true;
    }
  });

  // Get photos for current view (workbench or specific room)
  const visiblePhotos = filteredPhotos.filter(photo => {
    if (selectedRoom) {
      return photo.roomId === selectedRoom.id;
    } else {
      // On main workbench, show photos not assigned to any room
      return photo.roomId === null;
    }
  });

  // Get items for current view (workbench or specific room)
  const visibleItems = Array.isArray(items)
  ? items.filter(item => {
      if (selectedRoom) {
        return item.roomId === selectedRoom.id;
      } else {
        return item.roomId === null;
      }
    })
  : [];

  // Create a new item with optional initial photo
  const handleCreateItem = (photoId?: string) => {
    const newItem: Item = {
      id: `item-${Date.now()}`,
      name: '',
      description: '',
      thumbnailPhotoId: photoId || null,
      photoIds: photoId ? [photoId] : [],
      roomId: selectedRoom?.id || null,
      replacementValue: 0,
    };
    setItems([...items, newItem]);
    
    // Only set selected item if autoOpenDetailPanel is true
    if (autoOpenDetailPanel) {
      setSelectedItem(newItem);
    }
  };

  // Handle creating an empty item
  const handleCreateEmptyItem = () => {
    handleCreateItem();
  };

  // Handle adding a photo to an item
  const handleAddPhotoToItem = (itemId: string, photoId: string) => {
    // Find the item
    const item = items.find(i => i.id === itemId);
    if (!item) return;

    // Add the photo to the item
    const updatedItem = {
      ...item,
      photoIds: [...item.photoIds, photoId],
      // If this is the first photo, make it the thumbnail
      thumbnailPhotoId: item.thumbnailPhotoId || photoId,
    };

    // Update items state
    setItems(items.map(i => i.id === itemId ? updatedItem : i));

    // Update the photo's itemId property
    setPhotos(photos.map(photo => 
      photo.id === photoId ? { ...photo, itemId: itemId } : photo
    ));

    // If this was the selected item, update that too
    if (selectedItem?.id === itemId) {
      setSelectedItem(updatedItem);
    }
  };

  // Handle removing a photo from an item
  const handleRemovePhotoFromItem = (photoId: string) => {
    if (!selectedItem) return;

    // Update the photo to no longer be part of the item
    const updatedPhotos = photos.map(photo => 
      photo.id === photoId ? { ...photo, itemId: null } : photo
    );

    // Update the item's photoIds
    const updatedPhotoIds = selectedItem.photoIds.filter(id => id !== photoId);
    
    if (updatedPhotoIds.length === 0) {
      const updatedItems = Array.isArray(items)
        ? items.filter(item => item.id !== selectedItem?.id)
        : [];
      setItems(updatedItems);
      setSelectedItem(null);
    } else {
      // Update the item with remaining photos
      const updatedItem = {
        ...selectedItem,
        photoIds: updatedPhotoIds,
        thumbnailPhotoId: selectedItem.thumbnailPhotoId === photoId 
          ? updatedPhotoIds[0] 
          : selectedItem.thumbnailPhotoId
      };
      
      const updatedItems = items.map(item => 
        item.id === selectedItem.id ? updatedItem : item
      );
      
      setItems(updatedItems);
      setSelectedItem(updatedItem);
    }

    setPhotos(updatedPhotos);
  };

  // Handle moving an item to a room
  const handleMoveItemToRoom = (itemId: string, roomId: string | null) => {
    // Find the item
    const item = items.find(i => i.id === itemId);
    if (!item) return;
    
    // Update the item's roomId
    const updatedItem = { ...item, roomId };
    
    // Update the items state
    setItems(items.map(i => i.id === itemId ? updatedItem : i));
    
    // If this was the selected item, update that too
    if (selectedItem?.id === itemId) {
      setSelectedItem(updatedItem);
    }
  };

  // Handle moving an item to a specific room from the details panel
  const handleMoveItemToRoomFromPanel = (roomId: string | null) => {
    if (!selectedItem) return;
    handleMoveItemToRoom(selectedItem.id, roomId);
  };

  // Handle updating item details
  const handleUpdateItem = (updatedItem: Item) => {
    const updatedItems = items.map(item => 
      item.id === updatedItem.id ? updatedItem : item
    );
    setItems(updatedItems);
    setSelectedItem(updatedItem);
  };

  // Handle changing the thumbnail photo for an item
  const handleChangeThumbnail = (itemId: string) => {
    const item = items.find(item => item.id === itemId);
    if (!item || item.photoIds.length <= 1) return;

    // Find the current thumbnail index
    const currentIndex = item.photoIds.findIndex(id => id === item.thumbnailPhotoId);
    // Get the next photo in the array (or circle back to the first)
    const nextIndex = (currentIndex + 1) % item.photoIds.length;
    const newThumbnailId = item.photoIds[nextIndex];

    // Update the item
    const updatedItem = { ...item, thumbnailPhotoId: newThumbnailId };
    const updatedItems = items.map(i => i.id === itemId ? updatedItem : i);
    
    setItems(updatedItems);
    if (selectedItem?.id === itemId) {
      setSelectedItem(updatedItem);
    }
  };

  // Handle moving a photo to a room
  const handleMovePhotoToRoom = (photoId: string, roomId: string | null) => {
    // Find the photo
    const photo = photos.find(p => p.id === photoId);
    if (!photo) return;
    
    // Update the photo's roomId
    const updatedPhoto = { ...photo, roomId };
    
    // Update the photos state
    setPhotos(photos.map(p => p.id === photoId ? updatedPhoto : p));
    
    // If the photo is part of an item, we need to update that too
    if (photo.itemId) {
      const item = items.find(i => i.id === photo.itemId);
      if (item) {
        // If the item has multiple photos, just move this one
        if (item.photoIds.length > 1) {
          // Remove the photo from the item
          const updatedItem = {
            ...item,
            photoIds: item.photoIds.filter(id => id !== photoId),
            thumbnailPhotoId: item.thumbnailPhotoId === photoId 
              ? item.photoIds.find(id => id !== photoId) || null 
              : item.thumbnailPhotoId
          };
          
          // Update the items state
          setItems(items.map(i => i.id === item.id ? updatedItem : i));
          
          // Update the photo to no longer be part of the item
          setPhotos(photos.map(p => p.id === photoId ? { ...updatedPhoto, itemId: null } : p));
        } 
        // If it's the only photo, move the entire item
        else {
          const updatedItem = { ...item, roomId };
          setItems(items.map(i => i.id === item.id ? updatedItem : i));
        }
      }
    }
  };

  // Handle rearranging photos
  const handleRearrangePhotos = (targetIndex: number, draggedIndex: number) => {
    // Create a copy of the photos array
    const newPhotos = [...photos];
    // Get the photo at the dragged index
    const draggedPhoto = newPhotos[draggedIndex];
    // Remove the dragged photo from its original position
    newPhotos.splice(draggedIndex, 1);
    // Insert the dragged photo at the target position
    newPhotos.splice(targetIndex, 0, draggedPhoto);
    // Update the photos state
    setPhotos(newPhotos);
  };

  // Handle rearranging items
  const handleRearrangeItems = (targetIndex: number, draggedIndex: number) => {
    // Create a copy of the items array
    const newItems = [...items];
    // Get the item at the dragged index
    const draggedItem = newItems[draggedIndex];
    // Remove the dragged item from its original position
    newItems.splice(draggedIndex, 1);
    // Insert the dragged item at the target position
    newItems.splice(targetIndex, 0, draggedItem);
    // Update the items state
    setItems(newItems);
  };

  // Handle selecting an item
  const handleSelectItem = (item: Item) => {
    setSelectedItem(item);
  };

  // Toggle search mode between highlight and find
  const toggleSearchMode = () => {
    setSearchMode(mode => 
      mode === SearchMode.Highlight ? SearchMode.Find : SearchMode.Highlight
    );
  };

  const handleSearchChange = (searchQuery: string) => {
    setSearchQuery(searchQuery);
  };

  // Handle file upload completion
  const handleUploadComplete = (newFiles: any[]) => {
    console.log('Upload complete, new files:', newFiles);
    setShowUploadModal(false);
    
    // Add the new files to the photos state
    if (Array.isArray(newFiles) && newFiles.length > 0) {
      setPhotos(prevPhotos => {
        return Array.isArray(prevPhotos) ? [...prevPhotos, ...newFiles] : newFiles;
      });
    }
  };

  // Toggle upload modal
  const toggleUploadModal = () => {
    setShowUploadModal(!showUploadModal);
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex flex-col h-screen">
        <WorkbenchHeader 
          selectedRoom={selectedRoom}
          onBackToWorkbench={() => setSelectedRoom(null)}
          onCreateEmptyItem={handleCreateEmptyItem}
        />
        
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-64 bg-white border-r border-gray-200 p-4 overflow-y-auto">
            <RoomSelector 
              rooms={rooms}
              selectedRoom={selectedRoom}
              onSelectRoom={setSelectedRoom}
              onMovePhotoToRoom={handleMovePhotoToRoom}
              onMoveItemToRoom={handleMoveItemToRoom}
            />
            <div className="mt-6">
              <SearchBar 
                searchQuery={searchQuery}
                searchMode={searchMode}
                onSearchChange={handleSearchChange}
                onModeChange={toggleSearchMode}
              />
            </div>
          </div>
          
          {/* Main content area */}
          <div className="flex-grow overflow-auto p-4">
            {selectedRoom && (
              <div className="mb-4 flex items-center">
                <h2 className="text-xl font-semibold">{selectedRoom.name}</h2>
                <button
                  onClick={() => setSelectedRoom(null)}
                  className="ml-4 text-blue-600 hover:text-blue-800"
                >
                  Back to All
                </button>
              </div>
            )}

            {/* Upload Button and Search */}
            <div className="flex space-x-4 mb-4">
              <button
                onClick={toggleUploadModal}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload Files
              </button>
              <div className="flex-grow"></div>
              <input
                type="text"
                placeholder="Search photos..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {isLoading ? (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
              </div>
            ) : error ? (
              <div className="text-red-500 text-center p-4">{error}</div>
            ) : (
              <PhotoGrid
                photos={
                  Array.isArray(photos)
                    ? selectedRoom
                      ? photos.filter(photo => photo.roomId === selectedRoom.id)
                      : photos
                    : []
                }
                items={
                  Array.isArray(items)
                    ? selectedRoom
                      ? items.filter(item => item.roomId === selectedRoom.id)
                      : items
                    : []
                }
                searchQuery={searchQuery}
                searchMode={searchMode}
                onCreateItem={handleCreateItem}
                onRearrangePhotos={handleRearrangePhotos}
                onRearrangeItems={handleRearrangeItems}
                onAddPhotoToItem={handleAddPhotoToItem}
                onSelectItem={handleSelectItem}
              />
            )}
          </div>
        </div>
        
        {/* Item details panel */}
        {selectedItem && (
          <div className="fixed top-16 right-0 h-[calc(100vh-4rem)] z-10 max-w-sm">
            <ItemDetailsPanel 
              item={selectedItem}
              photos={photos.filter(photo => selectedItem.photoIds.includes(photo.id))}
              onClose={() => setSelectedItem(null)}
              onUpdate={handleUpdateItem}
              onRemovePhoto={handleRemovePhotoFromItem}
              onChangeThumbnail={() => handleChangeThumbnail(selectedItem.id)}
              onMoveToRoom={handleMoveItemToRoomFromPanel}
              onAddPhoto={handleAddPhotoToItem}
              rooms={rooms}
            />
          </div>
        )}
        
        {/* File Upload Modal */}
        {showUploadModal && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
              <div className="fixed inset-0 transition-opacity" aria-hidden="true">
                <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
              </div>
              <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
              <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                  <div className="sm:flex sm:items-start">
                    <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                      <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Upload Files</h3>
                      <div className="mt-2">
                        <FileUploader 
                          claimId={claimId || ''} 
                          onUploadComplete={handleUploadComplete}
                          authToken={user?.id_token || ''}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                  <button
                    type="button"
                    onClick={toggleUploadModal}
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </DndProvider>
  );
}
