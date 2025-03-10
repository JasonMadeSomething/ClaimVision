"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Photo, Item, SearchMode } from "@/types/workbench";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Menu } from '@headlessui/react';
import { EllipsisVerticalIcon } from '@heroicons/react/24/outline';

interface PhotoGridProps {
  photos: Photo[];
  items: Item[];
  searchQuery: string;
  searchMode: SearchMode;
  selectedItem: Item | null;
  onSelectItem: (item: Item | null) => void;
  onCreateItem: (photoId: string) => void;
  onAddPhotoToItem: (itemId: string, photoId: string) => void;
  detailsPanelOpen: boolean;
}

// Individual photo component
interface PhotoComponentProps {
  photo: Photo;
  isHighlighted: boolean;
  isSelected: boolean;
  onSelect: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDrop: (draggedPhotoId: string) => void;
  onCreateItem: () => void;
  isPartOfItem?: boolean;
}

const PhotoComponent: React.FC<PhotoComponentProps> = ({
  photo,
  isHighlighted,
  isSelected,
  onSelect,
  onDragStart,
  onDragEnd,
  onDrop,
  onCreateItem,
  isPartOfItem,
}) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'PHOTO',
    item: { id: photo.id },
    collect: (monitor) => ({
      isDragging: !!monitor.isDragging(),
    }),
  }));

  const [{ isOver }, drop] = useDrop(() => ({
    accept: 'PHOTO',
    drop: (item: { id: string }) => {
      onDrop(item.id);
    },
    collect: monitor => ({
      isOver: !!monitor.isOver(),
    }),
  }));

  // Combine drag and drop refs
  const refs = (el: HTMLDivElement) => {
    drag(el);
    drop(el);
  };

  return (
    <div
      ref={refs}
      onClick={onSelect}
      data-testid="photo-card"
      className={`
        relative rounded-lg overflow-hidden cursor-pointer
        ${isSelected ? 'ring-2 ring-blue-500' : 'hover:shadow-md'}
        ${!isHighlighted ? 'opacity-40' : isDragging ? 'opacity-50' : 'opacity-100'}
        transition-all duration-200
        group
      `}
    >
      <div className="aspect-square bg-gray-100">
        <img
          src={photo.url}
          alt={photo.fileName || 'Photo'}
          className="w-full h-full object-cover"
        />
      </div>

      {/* Photo Info Overlay */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-3">
        <div className="text-white text-sm truncate">
          {photo.fileName}
        </div>
      </div>

      {/* Menu Button */}
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <Menu as="div" className="relative inline-block text-left">
          <Menu.Button className="p-1 rounded-full bg-white/90 hover:bg-white shadow-sm">
            <EllipsisVerticalIcon className="h-5 w-5 text-gray-700" />
          </Menu.Button>
          <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
            <Menu.Item>
              {({ active }) => (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCreateItem();
                  }}
                  className={`${
                    active ? 'bg-gray-100' : ''
                  } group flex w-full items-center px-4 py-2 text-sm text-gray-700`}
                >
                  Create Item from Photo
                </button>
              )}
            </Menu.Item>
          </Menu.Items>
        </Menu>
      </div>

      {/* Item Label */}
      {isPartOfItem && (
        <div className="absolute top-2 left-2 bg-blue-500 text-white px-2 py-1 rounded-md text-xs font-medium">
          Part of Item
        </div>
      )}

      {/* Drop Indicator */}
      {isOver && (
        <div className="absolute inset-0 bg-blue-500 bg-opacity-20 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-lg p-2 text-sm font-medium">
            Drop to Create Item
          </div>
        </div>
      )}
    </div>
  );
};

interface ItemComponentProps {
  item: Item;
  photos: Photo[];
  isSelected: boolean;
  onSelect: () => void;
}

const ItemComponent: React.FC<ItemComponentProps> = ({
  item,
  photos,
  isSelected,
  onSelect,
}) => {
  const thumbnailPhoto = photos.find(p => p.id === item.thumbnailPhotoId);

  return (
    <div
      onClick={onSelect}
      data-testid="item-card"
      className={`
        relative rounded-lg overflow-hidden cursor-pointer
        ${isSelected ? 'ring-2 ring-blue-500' : 'hover:shadow-md'}
        transition-all duration-200
      `}
    >
      <div className="aspect-square bg-gray-100">
        {thumbnailPhoto && (
          <img
            src={thumbnailPhoto.url}
            alt={item.name || 'Item thumbnail'}
            className="w-full h-full object-cover"
          />
        )}
      </div>

      {/* Item Info Overlay */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-3">
        <div className="text-white">
          <div className="text-lg font-medium truncate">{item.name || 'Untitled Item'}</div>
          <div className="text-sm opacity-90">
            {item.photoIds.length} {item.photoIds.length === 1 ? 'photo' : 'photos'}
          </div>
        </div>
      </div>

      {/* Value Label */}
      <div className="absolute top-2 right-2 bg-white/90 text-gray-900 px-2 py-1 rounded-md text-sm font-medium shadow-sm">
        ${item.replacementValue}
      </div>
    </div>
  );
};

export default function PhotoGrid({ 
  photos, 
  items, 
  searchQuery, 
  searchMode,
  selectedItem,
  onSelectItem,
  onCreateItem,
  onAddPhotoToItem,
  detailsPanelOpen
}: PhotoGridProps) {
  const [selectedPhotos, setSelectedPhotos] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Handle photo selection
  const handlePhotoSelect = (photo: Photo) => {
    if (photo.itemId) {
      // If photo is part of an item, select that item
      const item = items.find(i => i.id === photo.itemId);
      if (item) {
        onSelectItem(item);
      }
    } else {
      // Toggle photo selection
      setSelectedPhotos(prev => 
        prev.includes(photo.id) 
          ? prev.filter(id => id !== photo.id)
          : [...prev, photo.id]
      );
    }
  };

  // Handle creating an item from a single photo
  const handleCreateItemFromPhoto = (photoId: string) => {
    onCreateItem(photoId);
  };

  // Handle item selection
  const handleItemSelect = (item: Item) => {
    onSelectItem(selectedItem?.id === item.id ? null : item);
  };

  // Handle photo drop onto another photo
  const handlePhotoStackDrop = (targetPhotoId: string, draggedPhotoId: string) => {
    // Create an item starting with the target photo
    onCreateItem(targetPhotoId);
    
    // Once the item is created, we can add the dragged photo to it
    // This will happen in the parent component via the selectedItem
    setIsDragging(false);
  };

  // Handle photo drop onto an item
  const handlePhotoItemDrop = (itemId: string, photoId: string) => {
    onAddPhotoToItem(itemId, photoId);
    setIsDragging(false);
  };

  // Handle drag start
  const handleDragStart = (id: string) => {
    console.log('Drag started with id:', id);
    setIsDragging(true);
  };

  // Handle drag end
  const handleDragEnd = () => {
    console.log('Drag ended');
    
    // Use a short timeout to ensure this happens after any drop handlers
    setTimeout(() => {
      setIsDragging(false);
    }, 100);
  };

  // Check if a photo should be highlighted based on search
  const isPhotoHighlighted = (photo: Photo) => {
    if (!searchQuery) return true;
    return photo.labels.some(label => 
      label.toLowerCase().includes(searchQuery.toLowerCase())
    );
  };

  // Group photos by item
  const photosByItem = new Map<string | null, Photo[]>();
  photos.forEach(photo => {
    const key = photo.itemId || 'unassigned';
    if (!photosByItem.has(key)) {
      photosByItem.set(key, []);
    }
    photosByItem.get(key)!.push(photo);
  });

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex-1 overflow-y-auto p-4">
        <div className={`grid gap-4 ${
          detailsPanelOpen ? 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4' : 'grid-cols-3 md:grid-cols-4 lg:grid-cols-6'
        }`}>
          {/* Render items */}
          {items.map(item => (
            <ItemComponent
              key={item.id}
              item={item}
              photos={photos.filter(p => item.photoIds.includes(p.id))}
              isSelected={selectedItem?.id === item.id}
              onSelect={() => handleItemSelect(item)}
            />
          ))}
          
          {/* Render unassigned photos */}
          {photos
            .filter(photo => !photo.itemId)
            .map(photo => (
              <PhotoComponent
                key={photo.id}
                photo={photo}
                isHighlighted={isPhotoHighlighted(photo)}
                isSelected={selectedPhotos.includes(photo.id)}
                onSelect={() => handlePhotoSelect(photo)}
                onDragStart={() => handleDragStart(photo.id)}
                onDragEnd={handleDragEnd}
                onDrop={(draggedPhotoId) => handlePhotoStackDrop(photo.id, draggedPhotoId)}
                onCreateItem={() => handleCreateItemFromPhoto(photo.id)}
              />
            ))}
        </div>
      </div>
    </DndProvider>
  );
}
