export interface Photo {
  id: string;
  url: string;
  fileName: string;
  labels: string[];
  itemId: string | null;
  roomId: string | null;
  isMainPhoto?: boolean;
  position: {
    x: number;
    y: number;
  };
  uploadedAt: string;
}

export interface Item {
  id: string;
  name: string;
  description: string;
  thumbnailPhotoId: string | null;
  photoIds: string[];
  roomId: string | null;
  replacementValue: number;
  unit_cost?: number;
}

export interface Room {
  id: string;
  name: string;
  itemIds: string[];
  fileIds?: string[];
}

export interface DragItem {
  type: 'photo' | 'item';
  id: string;
}

export enum SearchMode {
  Find = 'find',
  Highlight = 'highlight',
  Filter = 'filter',
  All = 'all'
}

// Predefined room types available for selection
export const PREDEFINED_ROOM_TYPES = [
  { id: 'attic', name: 'Attic', icon: '📦' },
  { id: 'auto', name: 'Auto', icon: '🚗' },
  { id: 'basement', name: 'Basement', icon: '🧱' },
  { id: 'bathroom', name: 'Bathroom', icon: '🚿' },
  { id: 'bedroom', name: 'Bedroom', icon: '🛏️' },
  { id: 'closet', name: 'Closet', icon: '👕' },
  { id: 'dining-room', name: 'Dining Room', icon: '🍽️' },
  { id: 'entry', name: 'Entry', icon: '🚪' },
  { id: 'exterior', name: 'Exterior', icon: '🏡' },
  { id: 'family-room', name: 'Family Room', icon: '🛋️' },
  { id: 'foyer', name: 'Foyer', icon: '🚪' },
  { id: 'game-room', name: 'Game Room', icon: '🎮' },
  { id: 'garage', name: 'Garage', icon: '🚗' },
  { id: 'hall', name: 'Hall', icon: '🚶' },
  { id: 'kitchen', name: 'Kitchen', icon: '🍳' },
  { id: 'laundry-room', name: 'Laundry Room', icon: '🧺' },
  { id: 'living-room', name: 'Living Room', icon: '🛋️' },
  { id: 'primary-bathroom', name: 'Primary Bathroom', icon: '🛁' },
  { id: 'primary-bedroom', name: 'Primary Bedroom', icon: '🛌' },
  { id: 'mud-room', name: 'Mud Room', icon: '👢' },
  { id: 'nursery', name: 'Nursery', icon: '🧸' },
  { id: 'office', name: 'Office', icon: '💻' },
  { id: 'pantry', name: 'Pantry', icon: '🥫' },
  { id: 'patio', name: 'Patio', icon: '⛱️' },
  { id: 'play-room', name: 'Play Room', icon: '🧩' },
  { id: 'pool', name: 'Pool', icon: '🏊' },
  { id: 'porch', name: 'Porch', icon: '🪑' },
  { id: 'shop', name: 'Shop', icon: '🛒' },
  { id: 'storage', name: 'Storage', icon: '📦' },
  { id: 'theater', name: 'Theater', icon: '🎬' },
  { id: 'utility-room', name: 'Utility Room', icon: '🔧' },
  { id: 'workout-room', name: 'Workout Room', icon: '💪' },
  { id: 'other', name: 'Other', icon: '📋' }
];

// Export a type for the predefined room
export type PredefinedRoomType = {
  id: string;
  name: string;
  icon: string;
};
