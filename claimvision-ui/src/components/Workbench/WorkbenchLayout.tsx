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
import ReportRequestModal from './ReportRequestModal';

export default function WorkbenchLayout() {
  const router = useRouter();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [internalSearchTerm, setInternalSearchTerm] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>(SearchMode.Highlight);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [claimId, setClaimId] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showReportRequestModal, setShowReportRequestModal] = useState(false);
  // Track pending file associations for temporary items
  const [pendingFileAssociations, setPendingFileAssociations] = useState<{[tempItemId: string]: string[]}>({});
  const { user } = useAuth();

  const { autoOpenDetailPanel } = useSettingsStore();

  // Get claim_id from localStorage or URL if present
  useEffect(() => {
    // First try to get claim_id from localStorage
    const storedClaimId = typeof window !== 'undefined' ? localStorage.getItem('current_claim_id') : null;
    
    if (storedClaimId) {
      setClaimId(storedClaimId);
      // Clear from localStorage after retrieving to avoid stale data on future visits
      localStorage.removeItem('current_claim_id');
      return;
    }
    
    // Fallback to URL query param for backward compatibility
    const urlParams = new URLSearchParams(window.location.search);
    const claimIdParam = urlParams.get('claim_id');
    if (claimIdParam) {
      setClaimId(claimIdParam);
      
      // Clean up the URL to remove the query parameter
      if (typeof window !== 'undefined' && window.history && window.history.replaceState) {
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
      }
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
          // Process items and associate them with their photos
          const safeItems = Array.isArray(itemsJson?.data?.items)
            ? itemsJson.data.items
            : [];
          if (!Array.isArray(itemsJson?.data?.items)) {
            console.warn("Malformed items response:", itemsJson);
          }
          
          // Set photos safely
          const safePhotos = Array.isArray(photosJson?.data?.files)
            ? photosJson.data.files
            : Array.isArray(photosJson)
            ? photosJson
            : [];
          if (!Array.isArray(photosJson?.data?.files) && !Array.isArray(photosJson)) {
            console.warn("Malformed photos response:", photosJson);
          }
          
          // Process items and associate them with their photos
          const processedItems = safeItems.map((item: any) => {
            // Ensure photoIds is always an array
            if (!Array.isArray(item.file_ids)) {
              console.warn(`Item ${item.id} has no file_ids array, initializing empty array`);
              item.file_ids = [];
            }
            
            // Map file_ids to photoIds for backward compatibility
            item.photoIds = item.file_ids || [];
            
            // Set thumbnailPhotoId to the first photo if not set
            if (!item.thumbnailPhotoId && item.photoIds.length > 0) {
              item.thumbnailPhotoId = item.photoIds[0];
            }
            
            // Map unit_cost from the API response
            if (item.unit_cost !== undefined) {
              item.unit_cost = parseFloat(item.unit_cost);
            } else {
              item.unit_cost = item.replacementValue || 0;
            }
            
            // Ensure roomId is properly set from the API response
            // The backend stores room_id, but frontend uses roomId
            item.roomId = item.room_id || null;
            
            return item;
          });
          
          // Process photos and associate them with their items
          const processedPhotos = safePhotos.map((photo: any) => {
            // Find if this photo is associated with any item
            const associatedItem = processedItems.find((item: any) => 
              item.photoIds && item.photoIds.includes(photo.id)
            );
            
            // If associated, set the itemId
            if (associatedItem) {
              photo.itemId = associatedItem.id;
            } else {
              photo.itemId = null;
            }
            
            // Ensure roomId is properly set from the API response
            // The backend stores room_id, but frontend uses roomId
            photo.roomId = photo.room_id || null;
            
            return photo;
          });
          
          // Process rooms to populate itemIds arrays based on item room assignments
          const processedRooms = safeRooms.map((room: any) => {
            // Make sure itemIds is initialized as an array
            if (!Array.isArray(room.itemIds)) {
              room.itemIds = [];
            }
            
            // Find all items assigned to this room
            const roomItems = processedItems.filter((item: any) => 
              item.room_id === room.id || item.roomId === room.id
            );
            
            // Add item IDs to the room's itemIds array if not already present
            roomItems.forEach((item: any) => {
              if (!room.itemIds.includes(item.id)) {
                room.itemIds.push(item.id);
              }
            });
            
            // Find all files assigned to this room
            const roomFiles = processedPhotos.filter((photo: any) => 
              photo.room_id === room.id || photo.roomId === room.id
            );
            
            // Make sure fileIds is initialized as an array
            if (!Array.isArray(room.fileIds)) {
              room.fileIds = [];
            }
            
            // Add file IDs to the room's fileIds array if not already present
            roomFiles.forEach((photo: any) => {
              if (!room.fileIds.includes(photo.id)) {
                room.fileIds.push(photo.id);
              }
            });
            
            return room;
          });
          
          setItems(processedItems);
          setPhotos(processedPhotos);
          setRooms(processedRooms);
          console.log("Photos set:", processedPhotos);
          console.log("Items set:", processedItems);
          console.log("Rooms set:", processedRooms);
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
    if (!internalSearchTerm) return true;
    
    const matchesSearch = photo.labels.some(label => 
      label.toLowerCase().includes(internalSearchTerm.toLowerCase())
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
      return !photo.roomId;
    }
  });

  // Get items for current view (workbench or specific room)
  const visibleItems = Array.isArray(items)
  ? items.filter(item => {
      if (selectedRoom) {
        return item.roomId === selectedRoom.id;
      } else {
        // On main workbench, show items not assigned to any room
        return !item.roomId;
      }
    })
  : [];

  // Create a new item with optional initial photo
  const handleCreateItem = async (photoId?: string) => {
    if (!claimId || !user?.id_token) {
      console.error("Cannot create item: missing claim ID or auth token");
      return;
    }

    // Create a temporary ID for optimistic UI updates
    const tempId = `item-${Date.now()}`;
    
    const newItem: Item = {
      id: tempId,
      name: photoId ? 'New Item' : '',
      description: '',
      thumbnailPhotoId: photoId || null,
      photoIds: photoId ? [photoId] : [],
      roomId: selectedRoom?.id || null,
      unit_cost: 0,
      quantity: 1
    };
    
    // Optimistically update the UI
    setItems([...items, newItem]);
    
    // Only set selected item if autoOpenDetailPanel is true
    if (autoOpenDetailPanel) {
      setSelectedItem(newItem);
    }
    
    // Update the photo's itemId if a photoId was provided
    if (photoId) {
      setPhotos(photos.map(photo => 
        photo.id === photoId ? { ...photo, itemId: tempId } : photo
      ));
    }

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      
      // Prepare the request body to match what the backend expects
      const requestBody: any = {
        name: photoId ? 'New Item' : '',
        description: '',
        unit_cost: 0, // Use unit_cost instead of replacement_value
        room_id: selectedRoom?.id || null
      };
      
      // Add file_id if a photoId is provided (instead of using photo_ids or thumbnail_photo_id)
      if (photoId) {
        requestBody.file_id = photoId;
      }
      
      console.log(`Creating item for claim ${claimId} with data:`, requestBody);
      
      const response = await fetch(`${baseUrl}/claims/${claimId}/items`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.id_token}`
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Error creating item (${response.status}):`, errorText);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch (e) {
          errorData = { error_details: errorText || 'Failed to create item' };
        }
        throw new Error(errorData.error_details || 'Failed to create item');
      }

      const result = await response.json();
      console.log("Item created successfully:", result);
      
      if (result.data && result.data.id) {
        // Replace the temporary item with the server-returned item
        const serverItem: Item = {
          id: result.data.id,
          name: result.data.name,
          description: result.data.description || '',
          thumbnailPhotoId: photoId || null, // Use the photoId we already have
          photoIds: photoId ? [photoId] : [],
          roomId: result.data.room_id,
          unit_cost: result.data.unit_cost || 0, // Map unit_cost to replacementValue
          quantity: 1
        };
        
        setItems(prevItems => prevItems.map(item => 
          item.id === tempId ? serverItem : item
        ));
        
        // Update the photo's itemId with the server-assigned ID
        if (photoId) {
          setPhotos(prevPhotos => prevPhotos.map(photo => 
            photo.id === photoId ? { ...photo, itemId: serverItem.id } : photo
          ));
          
          // Update the photo's item association on the server
          try {
            await fetch(`${baseUrl}/files/${photoId}`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${user.id_token}`
              },
              body: JSON.stringify({
                item_id: serverItem.id
              })
            });
            console.log(`Photo ${photoId} associated with item ${serverItem.id}`);
          } catch (error) {
            console.error("Error associating photo with item:", error);
          }
        }
        
        // Update selected item if needed
        if (selectedItem?.id === tempId) {
          setSelectedItem(serverItem);
        }
        
        // Process any pending file associations
        if (pendingFileAssociations[tempId] && pendingFileAssociations[tempId].length > 0) {
          const fileIds = [...pendingFileAssociations[tempId]];
          
          // Update the pending associations state properly
          setPendingFileAssociations(prevAssociations => {
            const newAssociations = { ...prevAssociations };
            delete newAssociations[tempId];
            return newAssociations;
          });
          
          // Associate each file with the newly created item
          for (const fileId of fileIds) {
            try {
              // Log the URL we're calling to help with debugging
              const url = `${baseUrl}/items/${serverItem.id}/files`;
              const requestBody = {
                file_id: fileId,
                seed_labels: true // Optionally seed labels from the file to the item
              };
              
              // Log detailed request information for debugging
              console.log('File association request details (from pending associations):');
              console.log('URL:', url);
              console.log('Method:', 'POST');
              console.log('Headers:', { 'Content-Type': 'application/json', 'Authorization': 'Bearer [token redacted]' });
              console.log('Body:', JSON.stringify(requestBody, null, 2));
              
              const response = await fetch(url, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${user.id_token}`
                },
                body: JSON.stringify(requestBody)
              });

              if (!response.ok) {
                const errorText = await response.text();
                console.error(`Error associating file with item (${response.status}):`, errorText);
                throw new Error('Failed to associate file with item');
              }

              console.log(`File ${fileId} associated with item ${serverItem.id}`);
            } catch (error) {
              console.error(`Error associating file ${fileId} with item ${serverItem.id}:`, error);
            }
          }
        }
      }
    } catch (error) {
      console.error("Error creating item:", error);
      
      // Revert optimistic updates on error
      setItems(prevItems => prevItems.filter(item => item.id !== tempId));
      
      if (photoId) {
        setPhotos(prevPhotos => prevPhotos.map(photo => 
          photo.id === photoId ? { ...photo, itemId: null } : photo
        ));
      }
      
      if (selectedItem?.id === tempId) {
        setSelectedItem(null);
      }
    }
  };

  // Handle updating item details
  const handleUpdateItem = async (updatedItem: Item) => {
    if (!claimId || !user?.id_token) {
      console.error("Cannot update item: missing claim ID or auth token");
      // Still update the UI even if we can't save to the server
      const updatedItems = items.map(item => 
        item.id === updatedItem.id ? updatedItem : item
      );
      setItems(updatedItems);
      setSelectedItem(updatedItem);
      return;
    }
    
    // Skip API calls for temporary items (they haven't been created on the server yet)
    if (updatedItem.id.startsWith('item-')) {
      console.log("Skipping API update for temporary item:", updatedItem.id);
      const updatedItems = items.map(item => 
        item.id === updatedItem.id ? updatedItem : item
      );
      setItems(updatedItems);
      setSelectedItem(updatedItem);
      return;
    }
    
    // Store the original item for rollback if needed
    const originalItem = items.find(item => item.id === updatedItem.id);
    if (!originalItem) return;
    
    // Optimistically update the UI
    const updatedItems = items.map(item => 
      item.id === updatedItem.id ? updatedItem : item
    );
    setItems(updatedItems);
    setSelectedItem(updatedItem);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      
      // Prepare the request body to match what the backend expects
      const requestBody = {
        name: updatedItem.name,
        description: updatedItem.description,
        unit_cost: updatedItem.unit_cost,
        room_id: updatedItem.roomId,
        brand_manufacturer: updatedItem.brand_manufacturer,
        model_number: updatedItem.model_number,
        original_vendor: updatedItem.original_vendor,
        quantity: updatedItem.quantity,
        age_years: updatedItem.age_years,
        age_months: updatedItem.age_months,
        condition: updatedItem.condition
      };
      
      console.log(`Updating item ${updatedItem.id} with data:`, requestBody);
      
      const response = await fetch(`${baseUrl}/items/${updatedItem.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.id_token}`
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Error updating item (${response.status}):`, errorText);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch (e) {
          errorData = { error_details: errorText || 'Failed to update item' };
        }
        throw new Error(errorData.error_details || 'Failed to update item');
      }

      console.log("Item updated successfully");
    } catch (error) {
      console.error("Error updating item:", error);
      
      // Revert optimistic updates on error
      if (originalItem) {
        const revertedItems = items.map(item => 
          item.id === updatedItem.id ? originalItem : item
        );
        setItems(revertedItems);
        setSelectedItem(originalItem);
      }
    }
  };

  // Handle creating a new room
  const handleCreateRoom = async (roomName: string, roomType: string) => {
    if (!claimId || !user?.id_token) {
      console.error("Cannot create room: missing claim ID or auth token");
      return;
    }

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const response = await fetch(`${baseUrl}/claims/${claimId}/rooms`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.id_token}`
        },
        body: JSON.stringify({
          name: roomName,
          description: `${roomType} room` // API expects name and description, not type
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error_details || 'Failed to create room');
      }

      const roomData = await response.json();
      console.log("Room created successfully:", roomData);
      
      // Add the new room to the rooms list
      if (roomData.data) {
        const newRoom = {
          id: roomData.data.id,
          name: roomData.data.name,
          itemIds: roomData.data.item_ids || [],
          fileIds: roomData.data.file_ids || []
        };
        setRooms([...rooms, newRoom]);
      }
    } catch (error) {
      console.error("Error creating room:", error);
      throw error;
    }
  };

  // Handle deleting a room
  const handleDeleteRoom = async (roomId: string) => {
    if (!claimId || !user?.id_token) {
      console.error("Cannot delete room: missing claim ID or auth token");
      return;
    }

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const response = await fetch(`${baseUrl}/claims/${claimId}/rooms/${roomId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${user.id_token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error_details || 'Failed to delete room');
      }

      console.log("Room deleted successfully");
      
      // Remove the room from the rooms list
      setRooms(rooms.filter(room => room.id !== roomId));
      
      // If the deleted room was selected, go back to main workbench
      if (selectedRoom?.id === roomId) {
        setSelectedRoom(null);
      }
    } catch (error) {
      console.error("Error deleting room:", error);
      throw error;
    }
  };

  // Handle creating an empty item
  const handleCreateEmptyItem = () => {
    handleCreateItem();
  };

  // Handle adding a photo to an item
  const handleAddPhotoToItem = async (itemId: string, photoId: string) => {
    // Find the item
    const item = items.find(i => i.id === itemId);
    if (!item) return;

    // Add the photo to the item
    const updatedItem = {
      ...item,
      photoIds: Array.isArray(item.photoIds) ? [...item.photoIds, photoId] : [photoId],
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
    
    // Make API call to associate the file with the item
    if (claimId && user?.id_token && !itemId.startsWith('item-')) {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
        
        // Use the correct endpoint and HTTP method
        const url = `${baseUrl}/items/${itemId}/files`;
        const requestBody = {
          file_id: photoId,
          seed_labels: true // Optionally seed labels from the file to the item
        };
        
        // Log detailed request information for debugging
        console.log('File association request details:');
        console.log('URL:', url);
        console.log('Method:', 'POST');
        console.log('Headers:', { 'Content-Type': 'application/json', 'Authorization': 'Bearer [token redacted]' });
        console.log('Body:', JSON.stringify(requestBody, null, 2));
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.id_token}`
          },
          body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error(`Error associating file with item (${response.status}):`, errorText);
          throw new Error('Failed to associate file with item');
        }

        console.log(`Successfully associated file ${photoId} with item ${itemId}`);
      } catch (error) {
        console.error("Error associating file with item:", error);
        // Continue with local state updates even if the API call fails
      }
    } else if (itemId.startsWith('item-')) {
      console.log("Skipping API call for temporary item:", itemId);
      // Store the association for later processing
      setPendingFileAssociations(prevAssociations => ({
        ...prevAssociations,
        [itemId]: [...(prevAssociations[itemId] || []), photoId]
      }));
    }
    
    // We don't need to call handleUpdateItem since the association is handled by the API
    // and we've already updated the local state
  };

  // Handle removing a photo from an item
  const handleRemovePhotoFromItem = async (photoId: string) => {
    if (!selectedItem) return;

    // Update the photo to no longer be part of the item
    const updatedPhotos = photos.map(photo => 
      photo.id === photoId ? { ...photo, itemId: null } : photo
    );

    // Update the item's photoIds
    const updatedPhotoIds = selectedItem.photoIds.filter(id => id !== photoId);
    
    if (updatedPhotoIds.length === 0) {
      // If no photos left, delete the item
      const updatedItems = Array.isArray(items)
        ? items.filter(item => item.id !== selectedItem?.id)
        : [];
      setItems(updatedItems);
      setSelectedItem(null);
      
      // Delete the item from the server
      if (claimId && user?.id_token && selectedItem.id.startsWith('item-') === false) {
        try {
          const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
          const response = await fetch(`${baseUrl}/items/${selectedItem.id}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${user.id_token}`
            }
          });
          
          if (!response.ok) {
            console.error(`Error deleting item: ${response.status}`);
            // Revert the local deletion to prevent duplication
            setItems(prevItems => {
              // Only add the item back if it's not already in the array
              if (!prevItems.some(item => item.id === selectedItem.id)) {
                return [...prevItems, selectedItem];
              }
              return prevItems;
            });
            return; // Exit early to prevent further processing
          }
          
          console.log("Item deleted successfully");
        } catch (error) {
          console.error("Error deleting item:", error);
          // Revert the local deletion to prevent duplication
          setItems(prevItems => {
            // Only add the item back if it's not already in the array
            if (!prevItems.some(item => item.id === selectedItem.id)) {
              return [...prevItems, selectedItem];
            }
            return prevItems;
          });
        }
      }
    } else {
      // Update the item with remaining photos
      let updatedItem = {
        ...selectedItem,
        photoIds: updatedPhotoIds,
      };
      
      // If the thumbnail was removed, set a new one
      if (selectedItem.thumbnailPhotoId === photoId) {
        updatedItem = {
          ...updatedItem,
          thumbnailPhotoId: updatedPhotoIds[0] || null
        };
      }
      
      // Update state
      setItems(items.map(item => 
        item.id === selectedItem.id ? updatedItem : item
      ));
      setSelectedItem(updatedItem);
      
      // Persist the change
      await handleUpdateItem(updatedItem);
    }
    
    // Update photos state
    setPhotos(updatedPhotos);
    
    // Update the photo's association on the server
    if (claimId && user?.id_token) {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
        await fetch(`${baseUrl}/files/${photoId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.id_token}`
          },
          body: JSON.stringify({
            item_id: null
          })
        });
        console.log("Photo item association updated successfully");
      } catch (error) {
        console.error("Error updating photo item association:", error);
      }
    }
  };

  // Move an item to a room
  const handleMoveItemToRoom = async (itemId: string, roomId: string | null) => {
    try {
      if (!claimId || !user?.id_token) {
        console.error("Cannot move item: missing claim ID or auth token");
        return;
      }

      // Optimistically update the UI
      const updatedItems = items.map(item => 
        item.id === itemId ? { ...item, roomId } : item
      );
      setItems(updatedItems);

      // Update the selected item if it's the one being moved
      if (selectedItem && selectedItem.id === itemId) {
        setSelectedItem({ ...selectedItem, roomId });
      }

      // Update on the server
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const response = await fetch(`${baseUrl}/items/${itemId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.id_token}`
        },
        body: JSON.stringify({
          room_id: roomId
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update item room');
      }

      console.log(`Item ${itemId} moved to room ${roomId || 'main workbench'}`);
      
      // Also update the room's itemIds array for proper tracking
      if (roomId) {
        // Add to new room
        setRooms(prevRooms => prevRooms.map(room => 
          room.id === roomId 
            ? { ...room, itemIds: [...(room.itemIds || []), itemId] } 
            : room
        ));
      }
      
      // Remove from previous room if it was in one
      const previousRoom = rooms.find(room => 
        room.itemIds && room.itemIds.includes(itemId)
      );
      
      if (previousRoom && previousRoom.id !== roomId) {
        setRooms(prevRooms => prevRooms.map(room => 
          room.id === previousRoom.id 
            ? { ...room, itemIds: room.itemIds.filter(id => id !== itemId) } 
            : room
        ));
      }
    } catch (error) {
      console.error('Error moving item to room:', error);
      // Revert optimistic update on error
      // This would require keeping track of the previous state
    }
  };

  // Handle moving an item to a specific room from the details panel
  const handleMoveItemToRoomFromPanel = (roomId: string | null) => {
    if (!selectedItem) return;
    handleMoveItemToRoom(selectedItem.id, roomId);
  };

  // Handle changing the thumbnail photo for an item
  const handleChangeThumbnail = async (itemId: string) => {
    const item = items.find(item => item.id === itemId);
    if (!item || item.photoIds.length <= 1) return;

    // Find the current thumbnail index
    const currentIndex = item.photoIds.findIndex(id => id === item.thumbnailPhotoId);
    // Get the next photo in the array (or circle back to the first)
    const nextIndex = (currentIndex + 1) % item.photoIds.length;
    const newThumbnailId = item.photoIds[nextIndex];

    // Update the item
    const updatedItem = { ...item, thumbnailPhotoId: newThumbnailId };
    
    // Optimistically update the UI
    const updatedItems = items.map(item => 
      item.id === itemId ? updatedItem : item
    );
    
    setItems(updatedItems);
    if (selectedItem?.id === itemId) {
      setSelectedItem(updatedItem);
    }
    
    // Persist the change
    await handleUpdateItem(updatedItem);
  };

  // Handle moving a photo to a room
  const handleMovePhotoToRoom = async (photoId: string, roomId: string | null) => {
    // Find the photo
    const photo = photos.find(p => p.id === photoId);
    if (!photo) return;
    
    // Get the previous room ID
    const prevRoomId = photo.roomId;
    
    // Update locally first for immediate feedback
    const updatedPhoto = { ...photo, roomId };
    setPhotos(photos.map(p => p.id === photoId ? updatedPhoto : p));
    
    // Update the rooms' fileIds arrays
    const updatedRooms = rooms.map(room => {
      // Remove the file from its previous room
      if (prevRoomId === room.id) {
        return {
          ...room,
          fileIds: room.fileIds ? room.fileIds.filter((id: string) => id !== photoId) : []
        };
      }
      
      // Add the file to its new room
      if (roomId === room.id) {
        return {
          ...room,
          fileIds: room.fileIds ? [...room.fileIds, photoId] : [photoId]
        };
      }
      
      // Return unchanged room
      return room;
    });
    
    setRooms(updatedRooms);
    
    // Log the action
    console.log(`Photo ${photoId} moved to room ${roomId || 'Main Workbench'}`);
    
    // Update on the server
    if (!claimId || !user?.id_token) {
      console.error("Cannot update room assignment: missing claim ID or auth token");
      return;
    }
    
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      
      // For files, we use the files metadata endpoint
      const response = await fetch(`${baseUrl}/files/${photoId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.id_token}`
        },
        body: JSON.stringify({
          room_id: roomId // null will remove room association
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error("Error updating file room assignment:", errorData);
        
        // Revert the local change if the server update failed
        setPhotos(photos.map(p => p.id === photoId ? photo : p));
        
        throw new Error(errorData.error_details || 'Failed to update room assignment');
      }
      
      console.log("File room assignment updated successfully on server");
    } catch (error) {
      console.error("Error updating file room assignment:", error);
    }
  };

  // Handle rearranging photos
  const handleRearrangePhotos = (targetIndex: number, draggedId: string) => {
    // Find the photo at the dragged index
    const draggedIndex = photos.findIndex(photo => photo.id === draggedId);
    if (draggedIndex === -1) return;
    
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
  const handleRearrangeItems = (targetIndex: number, draggedId: string) => {
    // Find the item at the dragged index
    const draggedIndex = items.findIndex(item => item.id === draggedId);
    if (draggedIndex === -1) return;
    
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
    setInternalSearchTerm(searchQuery);
  };

  // Handle label click to search in find mode
  const handleLabelClick = (label: string) => {
    // If the label is already being used as a filter, clear it
    if (internalSearchTerm === label) {
      setSearchMode(SearchMode.Highlight);
      setInternalSearchTerm('');
    } else {
      // Set search mode to Find
      setSearchMode(SearchMode.Find);
      
      // Set internal search term without updating the input field
      setInternalSearchTerm(label);
    }
    
    // Don't update the visible search query in the input field
    // This way the search works but doesn't populate the search box
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

  // Handle deleting an item
  const handleDeleteItem = async (itemId: string) => {
    if (!claimId || !user?.id_token) {
      console.error("Cannot delete item: missing claim ID or auth token");
      return;
    }

    // Find the item to delete for potential rollback
    const itemToDelete = items.find(item => item.id === itemId);
    if (!itemToDelete) {
      console.error("Item not found:", itemId);
      return;
    }

    // If the selected item is being deleted, clear the selection
    if (selectedItem?.id === itemId) {
      setSelectedItem(null);
    }

    // Optimistically update the UI
    setItems(items.filter(item => item.id !== itemId));

    // If the item has photos, update their itemId to null
    const updatedPhotos = photos.map(photo => 
      photo.itemId === itemId ? { ...photo, itemId: null } : photo
    );
    setPhotos(updatedPhotos);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      
      console.log(`Deleting item ${itemId}`);
      
      const response = await fetch(`${baseUrl}/items/${itemId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${user.id_token}`
        }
      });
      
      if (!response.ok) {
        console.error(`Error deleting item: ${response.status}`);
        // Revert the local deletion to prevent duplication
        setItems(prevItems => {
          // Only add the item back if it's not already in the array
          if (!prevItems.some(item => item.id === itemId)) {
            return [...prevItems, itemToDelete];
          }
          return prevItems;
        });
        return; // Exit early to prevent further processing
      }
      
      console.log("Item deleted successfully");
    } catch (error) {
      console.error("Error deleting item:", error);
      // Revert the local deletion to prevent duplication
      setItems(prevItems => {
        // Only add the item back if it's not already in the array
        if (!prevItems.some(item => item.id === itemId)) {
          return [...prevItems, itemToDelete];
        }
        return prevItems;
      });
    }
  };

  // Handle deleting a photo
  const handleDeletePhoto = async (photoId: string) => {
    if (!claimId || !user?.id_token) {
      console.error("Cannot delete photo: missing claim ID or auth token");
      return;
    }

    // Find the photo to delete for potential rollback
    const photoToDelete = photos.find(photo => photo.id === photoId);
    if (!photoToDelete) {
      console.error("Photo not found:", photoId);
      return;
    }

    // Optimistically update the UI
    setPhotos(photos.filter(photo => photo.id !== photoId));

    // If the photo is associated with an item, update the item's photoIds
    if (photoToDelete.itemId) {
      const updatedItems = items.map(item => {
        if (item.id === photoToDelete.itemId) {
          return {
            ...item,
            photoIds: item.photoIds.filter(id => id !== photoId),
            thumbnailPhotoId: item.thumbnailPhotoId === photoId ? null : item.thumbnailPhotoId
          };
        }
        return item;
      });
      setItems(updatedItems);
    }

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      
      console.log(`Deleting photo ${photoId}`);
      
      const response = await fetch(`${baseUrl}/files/${photoId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${user.id_token}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Error deleting photo (${response.status}):`, errorText);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch (e) {
          errorData = { error_details: errorText || 'Failed to delete photo' };
        }
        throw new Error(errorData.error_details || 'Failed to delete photo');
      }

      console.log("Photo deleted successfully");
    } catch (error) {
      console.error("Error deleting photo:", error);
      
      // Revert optimistic updates on error
      if (photoToDelete) {
        setPhotos([...photos, photoToDelete]);
        
        // Restore item associations
        if (photoToDelete.itemId) {
          const updatedItems = items.map(item => {
            if (item.id === photoToDelete.itemId) {
              return {
                ...item,
                photoIds: [...item.photoIds, photoId],
                thumbnailPhotoId: item.thumbnailPhotoId === null && photoToDelete.isMainPhoto 
                  ? photoId 
                  : item.thumbnailPhotoId
              };
            }
            return item;
          });
          setItems(updatedItems);
        }
      }
    }
  };

  // Handle opening the report request modal
  const handleOpenReportRequestModal = () => {
    setShowReportRequestModal(true);
  };

  // Handle closing the report request modal
  const handleCloseReportRequestModal = () => {
    setShowReportRequestModal(false);
  };

  // Handle back to workbench
  const handleBackToWorkbench = () => {
    setSelectedRoom(null);
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex flex-col h-screen">
        <WorkbenchHeader 
          selectedRoom={selectedRoom} 
          onBackToWorkbench={handleBackToWorkbench}
          onRequestReport={handleOpenReportRequestModal}
        />
        
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-64 min-w-64 flex-shrink-0 bg-white border-r border-gray-200 p-4 overflow-y-auto">
            <RoomSelector 
              rooms={rooms}
              selectedRoom={selectedRoom}
              onSelectRoom={setSelectedRoom}
              onMovePhotoToRoom={handleMovePhotoToRoom}
              onMoveItemToRoom={handleMoveItemToRoom}
              onCreateRoom={handleCreateRoom}
              onDeleteRoom={handleDeleteRoom}
              claimId={claimId || undefined}
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

            {/* Upload Button */}
            <div className="flex justify-end space-x-4 mb-4">
              <button
                onClick={handleCreateEmptyItem}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Item
              </button>
              <button
                onClick={toggleUploadModal}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload Files
              </button>
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
                      : searchMode === SearchMode.Find && internalSearchTerm
                        ? photos.filter(photo => 
                            photo.labels.some(label => 
                              label.toLowerCase().includes(internalSearchTerm.toLowerCase())
                            )
                          )
                        : photos
                    : []
                }
                items={
                  Array.isArray(items)
                    ? selectedRoom 
                      ? items.filter(item => item.roomId === selectedRoom.id)
                      : searchMode === SearchMode.Find && internalSearchTerm
                        ? items.filter(item => !item.roomId)
                        : items.filter(item => !item.roomId)
                    : []
                }
                searchQuery={internalSearchTerm}
                searchMode={searchMode}
                onCreateItem={handleCreateItem}
                onRearrangePhotos={handleRearrangePhotos}
                onRearrangeItems={handleRearrangeItems}
                onAddPhotoToItem={handleAddPhotoToItem}
                onSelectItem={handleSelectItem}
                onLabelClick={handleLabelClick}
                activeFilterLabel={searchMode === SearchMode.Find ? internalSearchTerm : ''}
                onDeleteItem={handleDeleteItem}
                onDeletePhoto={handleDeletePhoto}
              />
            )}
          </div>
        </div>
        
        {/* Item details panel */}
        {selectedItem && (
          <div className="fixed top-16 right-0 h-[calc(100vh-4rem)] z-10 max-w-sm">
            <ItemDetailsPanel 
              item={selectedItem}
              photos={photos.filter(photo => selectedItem.photoIds?.includes(photo.id) || false)}
              onClose={() => setSelectedItem(null)}
              onUpdate={handleUpdateItem}
              onRemovePhoto={handleRemovePhotoFromItem}
              onChangeThumbnail={() => handleChangeThumbnail(selectedItem.id)}
              onMoveToRoom={handleMoveItemToRoomFromPanel}
              onAddPhoto={handleAddPhotoToItem}
              onDeleteItem={() => handleDeleteItem(selectedItem.id)}
              onDeletePhoto={handleDeletePhoto}
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
        
        {/* Report Request Modal */}
        {claimId && showReportRequestModal && (
          <ReportRequestModal
            isOpen={showReportRequestModal}
            onClose={handleCloseReportRequestModal}
            claimId={claimId}
          />
        )}
      </div>
    </DndProvider>
  );
}
