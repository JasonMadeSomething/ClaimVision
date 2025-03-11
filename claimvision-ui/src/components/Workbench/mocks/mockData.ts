import { Item, Photo, Room, SearchMode } from "@/types/workbench";

// Mock photos data
export const mockPhotos: Photo[] = Array.from({ length: 20 }, (_, i) => ({
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
export const mockItems: Item[] = Array.from({ length: 5 }, (_, i) => ({
  id: `item-${i}`,
  name: `Item ${i + 1}`,
  description: `Description for item ${i + 1}`,
  thumbnailPhotoId: `photo-${i * 2}`,
  photoIds: [`photo-${i * 2}`, `photo-${i * 2 + 1}`],
  roomId: i < 2 ? "room-1" : (i < 4 ? "room-2" : null),
  replacementValue: Math.floor(Math.random() * 1000) + 100,
}));

// Mock rooms data
export const mockRooms: Room[] = [
  { id: "room-1", name: "Living Room", itemIds: ["item-0", "item-1"] },
  { id: "room-2", name: "Kitchen", itemIds: ["item-2", "item-3"] },
];

// Default props for PhotoGrid component
export const defaultPhotoGridProps = {
  photos: [],
  items: [],
  searchQuery: '',
  searchMode: 'all' as SearchMode,
  selectedItem: null,
  onSelectItem: jest.fn(),
  onCreateItem: jest.fn(),
  onAddPhotoToItem: jest.fn(),
  detailsPanelOpen: false,
};

// Default props for ItemDetailsPanel component
export const defaultItemDetailsPanelProps = {
  item: {
    id: 'item-0',
    name: 'Item 1',
    description: 'Description for item 1',
    thumbnailPhotoId: 'photo-0',
    photoIds: ['photo-0', 'photo-1'],
    roomId: 'room-1',
    replacementValue: 500,
  },
  photos: mockPhotos.filter(p => p.itemId === 'item-0'),
  rooms: mockRooms,
  onUpdate: jest.fn(),
  onRemovePhoto: jest.fn(),
  onChangeThumbnail: jest.fn(),
  onClose: jest.fn(),
  onMoveToRoom: jest.fn(),
  onAddPhoto: jest.fn(),
};

// Mock API handlers
export const mockApiHandlers = {
  onSelectItem: jest.fn(),
  onCreateItem: jest.fn(),
  onAddPhotoToItem: jest.fn(),
  onUpdateItem: jest.fn(),
  onRemovePhoto: jest.fn(),
  onChangeThumbnail: jest.fn(),
  onMoveToRoom: jest.fn(),
};
