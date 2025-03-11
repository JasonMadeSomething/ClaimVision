"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Photo, Item, Room, SearchMode } from "@/types/workbench";
import { useSettingsStore } from "@/stores/settingsStore";
import WorkbenchHeader from "./WorkbenchHeader";
import PhotoGrid from "./PhotoGrid";
import ItemDetailsPanel from "./ItemDetailsPanel";
import RoomSelector from "./RoomSelector";
import SearchBar from "./SearchBar";

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

  const { autoOpenDetailPanel } = useSettingsStore();

  // Fetch photos, items, and rooms on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        
        // Create a simple mock API implementation directly in the component
        // This will be replaced with actual API calls in the future
        console.log("Creating mock data...");
        
        // Mock photos data
        const mockPhotos: Photo[] = Array.from({ length: 20 }, (_, i) => ({
          id: `photo-${i}`,
          url: `https://source.unsplash.com/random/300x300?disaster&sig=${i}`,
          fileName: `photo-${i}.jpg`,
          labels: ["damage", i % 2 === 0 ? "water" : "fire", i % 3 === 0 ? "TV" : "furniture"],
          itemId: i < 10 ? `item-${Math.floor(i / 2)}` : null,
          position: { x: Math.random() * 800, y: Math.random() * 600 },
          roomId: i < 5 ? "room-1" : (i < 10 ? "room-2" : null),
          uploadedAt: new Date().toISOString(),
        }));
        
        // Mock items data
        const mockItems: Item[] = Array.from({ length: 5 }, (_, i) => ({
          id: `item-${i}`,
          name: `Item ${i + 1}`,
          description: `Description for item ${i + 1}`,
          thumbnailPhotoId: `photo-${i * 2}`,
          photoIds: [`photo-${i * 2}`, `photo-${i * 2 + 1}`],
          roomId: i < 2 ? "room-1" : (i < 4 ? "room-2" : null),
          replacementValue: Math.floor(Math.random() * 1000) + 100,
        }));
        
        // Mock rooms data
        const mockRooms: Room[] = [
          { id: "room-1", name: "Living Room", itemIds: ["item-0", "item-1"] },
          { id: "room-2", name: "Kitchen", itemIds: ["item-2", "item-3"] },
        ];
        
        console.log("Mock data created successfully");

        // Set the state with the mock data
        setPhotos(mockPhotos);
        setItems(mockItems);
        setRooms(mockRooms);
      } catch (err) {
        console.error("Error in fetchData:", err);
        if (err instanceof Error) {
          setError(`Failed to load workbench data: ${err.message}`);
        } else {
          setError("Failed to load workbench data");
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

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
  const visibleItems = items.filter(item => {
    if (selectedRoom) {
      return item.roomId === selectedRoom.id;
    } else {
      // On main workbench, show items not assigned to any room
      return item.roomId === null;
    }
  });

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
      // If no photos left, delete the item
      const updatedItems = items.filter(item => item.id !== selectedItem.id);
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
          <div className="flex-1 overflow-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              </div>
            ) : error ? (
              <div className="text-red-500 text-center p-4">{error}</div>
            ) : (
              <PhotoGrid
                photos={selectedRoom 
                  ? photos.filter(photo => photo.roomId === selectedRoom.id)
                  : photos}
                items={selectedRoom 
                  ? items.filter(item => item.roomId === selectedRoom.id)
                  : items}
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
      </div>
    </DndProvider>
  );
}
