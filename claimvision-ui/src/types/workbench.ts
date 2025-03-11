export interface Photo {
  id: string;
  url: string;
  fileName: string;
  labels: string[];
  itemId: string | null;
  roomId: string | null;
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
}

export interface Room {
  id: string;
  name: string;
  itemIds: string[];
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
