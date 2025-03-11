import { Item, Photo, Room } from "@/types/workbench";
import { mockItems, mockPhotos, mockRooms } from "./mockData";

// Mock API class that simulates API calls to the Python backend
class WorkbenchApi {
  // Initialize with the mock data from mockData.ts
  private items: Item[] = [...mockItems];
  private photos: Photo[] = [...mockPhotos];
  private rooms: Room[] = [...mockRooms];

  // Reset mock data to initial state (useful for tests)
  resetMockData(): void {
    this.items = [...mockItems];
    this.photos = [...mockPhotos];
    this.rooms = [...mockRooms];
  }

  // Simulate API delay
  private delay(ms: number = 100): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Simulate AWS Lambda response format
  private formatResponse<T>(data: T): { statusCode: number; body: string; headers: Record<string, string> } {
    return {
      statusCode: 200,
      body: JSON.stringify(data),
      headers: {
        "Content-Type": "application/json"
      }
    };
  }

  // Parse AWS Lambda response format
  private parseResponse<T>(response: { statusCode: number; body: string; headers: Record<string, string> }): T {
    if (response.statusCode !== 200) {
      throw new Error(`API error: ${response.statusCode}`);
    }
    return JSON.parse(response.body) as T;
  }

  // API Methods that simulate the Python backend

  // Items API
  async getItems(): Promise<Item[]> {
    await this.delay();
    const response = this.formatResponse({ items: this.items });
    return this.parseResponse<{ items: Item[] }>(response).items;
  }

  async getItem(id: string): Promise<Item | null> {
    await this.delay();
    const item = this.items.find(item => item.id === id);
    if (!item) {
      return null;
    }
    const response = this.formatResponse({ item });
    return this.parseResponse<{ item: Item }>(response).item;
  }

  async createItem(item: Omit<Item, 'id'>): Promise<Item> {
    await this.delay();
    const newItem: Item = {
      ...item,
      id: `item-${Date.now()}`,
    };
    this.items.push(newItem);
    
    // Update room if roomId is provided
    if (newItem.roomId) {
      const room = this.rooms.find(r => r.id === newItem.roomId);
      if (room) {
        room.itemIds.push(newItem.id);
      }
    }
    
    const response = this.formatResponse({ item: newItem });
    return this.parseResponse<{ item: Item }>(response).item;
  }

  async updateItem(item: Item): Promise<Item> {
    await this.delay();
    const index = this.items.findIndex(i => i.id === item.id);
    if (index === -1) {
      throw new Error(`Item with ID ${item.id} not found`);
    }
    
    // Handle room changes
    const oldRoomId = this.items[index].roomId;
    const newRoomId = item.roomId;
    
    if (oldRoomId !== newRoomId) {
      // Remove from old room
      if (oldRoomId) {
        const oldRoom = this.rooms.find(r => r.id === oldRoomId);
        if (oldRoom) {
          oldRoom.itemIds = oldRoom.itemIds.filter(id => id !== item.id);
        }
      }
      
      // Add to new room
      if (newRoomId) {
        const newRoom = this.rooms.find(r => r.id === newRoomId);
        if (newRoom && !newRoom.itemIds.includes(item.id)) {
          newRoom.itemIds.push(item.id);
        }
      }
    }
    
    this.items[index] = { ...item };
    const response = this.formatResponse({ item: this.items[index] });
    return this.parseResponse<{ item: Item }>(response).item;
  }

  async deleteItem(id: string): Promise<void> {
    await this.delay();
    const index = this.items.findIndex(i => i.id === id);
    if (index === -1) {
      throw new Error(`Item with ID ${id} not found`);
    }
    
    // Remove from room
    const roomId = this.items[index].roomId;
    if (roomId) {
      const room = this.rooms.find(r => r.id === roomId);
      if (room) {
        room.itemIds = room.itemIds.filter(itemId => itemId !== id);
      }
    }
    
    // Update photos
    this.photos.forEach(photo => {
      if (photo.itemId === id) {
        photo.itemId = null;
      }
    });
    
    this.items.splice(index, 1);
    const response = this.formatResponse({ success: true });
    this.parseResponse(response);
  }

  // Photos API
  async getPhotos(): Promise<Photo[]> {
    await this.delay();
    const response = this.formatResponse({ photos: this.photos });
    return this.parseResponse<{ photos: Photo[] }>(response).photos;
  }

  async getPhoto(id: string): Promise<Photo | null> {
    await this.delay();
    const photo = this.photos.find(photo => photo.id === id);
    if (!photo) {
      return null;
    }
    const response = this.formatResponse({ photo });
    return this.parseResponse<{ photo: Photo }>(response).photo;
  }

  async createPhoto(photo: Omit<Photo, 'id'>): Promise<Photo> {
    await this.delay();
    const newPhoto: Photo = {
      ...photo,
      id: `photo-${Date.now()}`,
    };
    this.photos.push(newPhoto);
    
    // Update item if itemId is provided
    if (newPhoto.itemId) {
      const item = this.items.find(i => i.id === newPhoto.itemId);
      if (item) {
        item.photoIds.push(newPhoto.id);
        // If this is the first photo, make it the thumbnail
        if (!item.thumbnailPhotoId) {
          item.thumbnailPhotoId = newPhoto.id;
        }
      }
    }
    
    const response = this.formatResponse({ photo: newPhoto });
    return this.parseResponse<{ photo: Photo }>(response).photo;
  }

  async updatePhoto(photo: Photo): Promise<Photo> {
    await this.delay();
    const index = this.photos.findIndex(p => p.id === photo.id);
    if (index === -1) {
      throw new Error(`Photo with ID ${photo.id} not found`);
    }
    
    // Handle item changes
    const oldItemId = this.photos[index].itemId;
    const newItemId = photo.itemId;
    
    if (oldItemId !== newItemId) {
      // Remove from old item
      if (oldItemId) {
        const oldItem = this.items.find(i => i.id === oldItemId);
        if (oldItem) {
          oldItem.photoIds = oldItem.photoIds.filter(id => id !== photo.id);
          // If this was the thumbnail, update it
          if (oldItem.thumbnailPhotoId === photo.id) {
            oldItem.thumbnailPhotoId = oldItem.photoIds[0] || null;
          }
        }
      }
      
      // Add to new item
      if (newItemId) {
        const newItem = this.items.find(i => i.id === newItemId);
        if (newItem && !newItem.photoIds.includes(photo.id)) {
          newItem.photoIds.push(photo.id);
          // If this is the first photo, make it the thumbnail
          if (!newItem.thumbnailPhotoId) {
            newItem.thumbnailPhotoId = photo.id;
          }
        }
      }
    }
    
    this.photos[index] = { ...photo };
    const response = this.formatResponse({ photo: this.photos[index] });
    return this.parseResponse<{ photo: Photo }>(response).photo;
  }

  async deletePhoto(id: string): Promise<void> {
    await this.delay();
    const index = this.photos.findIndex(p => p.id === id);
    if (index === -1) {
      throw new Error(`Photo with ID ${id} not found`);
    }
    
    // Remove from item
    const itemId = this.photos[index].itemId;
    if (itemId) {
      const item = this.items.find(i => i.id === itemId);
      if (item) {
        item.photoIds = item.photoIds.filter(photoId => photoId !== id);
        // If this was the thumbnail, update it
        if (item.thumbnailPhotoId === id) {
          item.thumbnailPhotoId = item.photoIds[0] || null;
        }
      }
    }
    
    this.photos.splice(index, 1);
    const response = this.formatResponse({ success: true });
    this.parseResponse(response);
  }

  // Rooms API
  async getRooms(): Promise<Room[]> {
    await this.delay();
    const response = this.formatResponse({ rooms: this.rooms });
    return this.parseResponse<{ rooms: Room[] }>(response).rooms;
  }

  async getRoom(id: string): Promise<Room | null> {
    await this.delay();
    const room = this.rooms.find(room => room.id === id);
    if (!room) {
      return null;
    }
    const response = this.formatResponse({ room });
    return this.parseResponse<{ room: Room }>(response).room;
  }

  async createRoom(room: Omit<Room, 'id'>): Promise<Room> {
    await this.delay();
    const newRoom: Room = {
      ...room,
      id: `room-${Date.now()}`,
    };
    this.rooms.push(newRoom);
    const response = this.formatResponse({ room: newRoom });
    return this.parseResponse<{ room: Room }>(response).room;
  }

  async updateRoom(room: Room): Promise<Room> {
    await this.delay();
    const index = this.rooms.findIndex(r => r.id === room.id);
    if (index === -1) {
      throw new Error(`Room with ID ${room.id} not found`);
    }
    this.rooms[index] = { ...room };
    const response = this.formatResponse({ room: this.rooms[index] });
    return this.parseResponse<{ room: Room }>(response).room;
  }

  async deleteRoom(id: string): Promise<void> {
    await this.delay();
    const index = this.rooms.findIndex(r => r.id === id);
    if (index === -1) {
      throw new Error(`Room with ID ${id} not found`);
    }
    
    // Update items
    this.items.forEach(item => {
      if (item.roomId === id) {
        item.roomId = null;
      }
    });
    
    // Update photos
    this.photos.forEach(photo => {
      if (photo.roomId === id) {
        photo.roomId = null;
      }
    });
    
    this.rooms.splice(index, 1);
    const response = this.formatResponse({ success: true });
    this.parseResponse(response);
  }

  // Additional helper methods
  async addPhotoToItem(itemId: string, photoId: string): Promise<void> {
    await this.delay();
    const item = this.items.find(i => i.id === itemId);
    if (!item) {
      throw new Error(`Item with ID ${itemId} not found`);
    }
    
    const photo = this.photos.find(p => p.id === photoId);
    if (!photo) {
      throw new Error(`Photo with ID ${photoId} not found`);
    }
    
    // Update the item's photoIds array
    if (!item.photoIds.includes(photoId)) {
      item.photoIds.push(photoId);
    }
    
    // If this is the first photo, make it the thumbnail
    if (!item.thumbnailPhotoId) {
      item.thumbnailPhotoId = photoId;
    }
    
    // Update the photo's itemId and roomId
    photo.itemId = itemId;
    photo.roomId = item.roomId;
    
    const response = this.formatResponse({ success: true });
    this.parseResponse(response);
  }

  async removePhotoFromItem(itemId: string, photoId: string): Promise<void> {
    await this.delay();
    const item = this.items.find(i => i.id === itemId);
    if (!item) {
      throw new Error(`Item with ID ${itemId} not found`);
    }
    
    const photo = this.photos.find(p => p.id === photoId);
    if (!photo) {
      throw new Error(`Photo with ID ${photoId} not found`);
    }
    
    // Update the item's photoIds array
    item.photoIds = item.photoIds.filter(id => id !== photoId);
    
    // If this was the thumbnail photo, update that as well
    if (item.thumbnailPhotoId === photoId) {
      item.thumbnailPhotoId = item.photoIds[0] || null;
    }
    
    // Update the photo's itemId
    photo.itemId = null;
    
    const response = this.formatResponse({ success: true });
    this.parseResponse(response);
  }

  async setItemThumbnail(itemId: string, photoId: string): Promise<void> {
    await this.delay();
    const item = this.items.find(i => i.id === itemId);
    if (!item) {
      throw new Error(`Item with ID ${itemId} not found`);
    }
    
    const photo = this.photos.find(p => p.id === photoId);
    if (!photo) {
      throw new Error(`Photo with ID ${photoId} not found`);
    }
    
    // Make sure the photo is associated with the item
    if (photo.itemId !== itemId) {
      throw new Error(`Photo with ID ${photoId} is not associated with item ${itemId}`);
    }
    
    // Update the item's thumbnailPhotoId
    item.thumbnailPhotoId = photoId;
    
    const response = this.formatResponse({ success: true });
    this.parseResponse(response);
  }

  async moveItemToRoom(itemId: string, roomId: string | null): Promise<void> {
    await this.delay();
    const item = this.items.find(i => i.id === itemId);
    if (!item) {
      throw new Error(`Item with ID ${itemId} not found`);
    }
    
    // If roomId is not null, make sure the room exists
    if (roomId !== null) {
      const room = this.rooms.find(r => r.id === roomId);
      if (!room) {
        throw new Error(`Room with ID ${roomId} not found`);
      }
    }
    
    // Remove from old room
    if (item.roomId) {
      const oldRoom = this.rooms.find(r => r.id === item.roomId);
      if (oldRoom) {
        oldRoom.itemIds = oldRoom.itemIds.filter(id => id !== itemId);
      }
    }
    
    // Add to new room
    if (roomId) {
      const newRoom = this.rooms.find(r => r.id === roomId);
      if (newRoom && !newRoom.itemIds.includes(itemId)) {
        newRoom.itemIds.push(itemId);
      }
    }
    
    // Update the item's roomId
    item.roomId = roomId;
    
    // Update all photos associated with this item
    this.photos.forEach(photo => {
      if (photo.itemId === itemId) {
        photo.roomId = roomId;
      }
    });
    
    const response = this.formatResponse({ success: true });
    this.parseResponse(response);
  }
}

// Export a singleton instance
export const workbenchApi = new WorkbenchApi();

// Export a function to create a new instance (useful for isolated tests)
export function createWorkbenchApi(): WorkbenchApi {
  return new WorkbenchApi();
}
