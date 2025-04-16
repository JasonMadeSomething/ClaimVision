"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { Photo, Item, SearchMode, DragItem } from "@/types/workbench";
import { DndProvider, useDrag, useDrop, DropTargetMonitor } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Menu } from '@headlessui/react';
import { EllipsisVerticalIcon } from '@heroicons/react/24/outline';
import Card from './Card';
import DropZone from './DropZone';
import { ChevronDownIcon, ChevronUpIcon, ViewColumnsIcon } from '@heroicons/react/24/outline';

// Define the props for the PhotoGrid component
interface PhotoGridProps {
  photos: Photo[];
  items: Item[];
  searchQuery: string;
  searchMode: SearchMode;
  onCreateItem: (photoId?: string) => void;
  onRearrangePhotos: (targetIndex: number, draggedId: string) => void;
  onRearrangeItems?: (targetIndex: number, draggedId: string) => void;
  onAddPhotoToItem?: (itemId: string, photoId: string) => void;
  onSelectItem?: (item: Item) => void;
  onLabelClick?: (label: string) => void;
  activeFilterLabel?: string;
  onDeleteItem?: (itemId: string) => void;
  onDeletePhoto?: (photoId: string) => void;
}

// Define grid column options
type GridColumns = 1 | 2 | 3 | 4 | 5 | 6;

// Define content type for co-mingling
type ContentItem = { type: 'photo'; data: Photo } | { type: 'item'; data: Item };

// PhotoGrid component - displays photos and items in a configurable grid
export default function PhotoGrid({
  photos,
  items,
  searchQuery,
  searchMode,
  onCreateItem,
  onRearrangePhotos,
  onRearrangeItems,
  onAddPhotoToItem,
  onSelectItem,
  onLabelClick,
  activeFilterLabel = '',
  onDeleteItem,
  onDeletePhoto,
}: PhotoGridProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  
  // UI state
  const [showItems, setShowItems] = useState(true);
  const [showPhotos, setShowPhotos] = useState(true);
  const [itemsExpanded, setItemsExpanded] = useState(true);
  const [photosExpanded, setPhotosExpanded] = useState(true);
  const [comingleContent, setComingleContent] = useState(false);
  const [gridColumns, setGridColumns] = useState<GridColumns>(4);
  const [showAllPhotos, setShowAllPhotos] = useState(true);
  
  // Group photos by their associated item
  const photosByItem = new Map<string | null, Photo[]>();
  
  // Initialize with null (unassigned photos)
  photosByItem.set(null, []);
  
  // Group photos by item
  photos.forEach(photo => {
    const itemId = photo.itemId;
    if (!photosByItem.has(itemId)) {
      photosByItem.set(itemId, []);
    }
    photosByItem.get(itemId)?.push(photo);
  });

  // Check if a photo should be highlighted based on search query
  const isPhotoHighlighted = (photo: Photo) => {
    if (!searchQuery) return false;
    
    return photo.labels.some(label => 
      label.toLowerCase().includes(searchQuery.toLowerCase())
    );
  };

  // Check if an item should be highlighted based on search query
  const isItemHighlighted = (item: Item) => {
    if (!searchQuery) return false;
    
    // Check if any of the item's photos have matching labels
    const itemPhotos = photos.filter(p => p.itemId === item.id);
    return itemPhotos.some(photo => isPhotoHighlighted(photo));
  };

  // Filter photos based on search mode and query
  const getFilteredPhotos = () => {
    if (!searchQuery) {
      return showAllPhotos ? photos : photosByItem.get(null) || [];
    }
    
    const photosToFilter = showAllPhotos ? photos : photosByItem.get(null) || [];
    
    if (searchMode === SearchMode.Find) {
      // In Find mode, only show photos that match the search query
      return photosToFilter.filter(photo => isPhotoHighlighted(photo));
    } else {
      // In Highlight mode, show all photos but they will be styled differently in the UI
      return photosToFilter;
    }
  };

  // Filter items based on search mode and query
  const getFilteredItems = () => {
    if (!searchQuery) {
      return items;
    }
    
    if (searchMode === SearchMode.Find) {
      // In Find mode, only show items that match the search query
      return items.filter(item => isItemHighlighted(item));
    } else if (searchMode === SearchMode.Filter) {
      // Filter mode is handled separately
      return searchMode === SearchMode.Filter ? items.filter(item => isItemHighlighted(item)) : items;
    } else {
      // In Highlight mode, show all items but they will be styled differently in the UI
      return items;
    }
  };

  // Handle photo drop between photos
  const handlePhotoBetweenDrop = (targetIndex: number, draggedId: string) => {
    if (!onRearrangePhotos) return;
    
    // Find the dragged photo's index in the original array
    const draggedIndex = photos.findIndex(p => p.id === draggedId);
    if (draggedIndex === -1) return;
    
    // Convert the target index to the actual index in the photos array
    // This is needed because we're only showing unassigned photos in this section
    const unassignedPhotos = photos.filter(p => p.itemId === null);
    const effectiveTargetIndex = targetIndex;
    
    let actualTargetIndex = 0;
    let unassignedCount = 0;
    
    for (let i = 0; i < photos.length; i++) {
      if (photos[i].itemId === null) {
        if (unassignedCount === effectiveTargetIndex) {
          actualTargetIndex = i;
          break;
        }
        unassignedCount++;
      }
    }
    
    // If we're dropping at the end, find the position after the last unassigned photo
    if (effectiveTargetIndex === unassignedPhotos.length) {
      for (let i = photos.length - 1; i >= 0; i--) {
        if (photos[i].itemId === null) {
          actualTargetIndex = i + 1;
          break;
        }
      }
    }
    
    // Call the parent component's rearrange function with the correct indices
    onRearrangePhotos(actualTargetIndex, draggedId);
    setHoverIndex(null);
  };

  // Handle item drop between items
  const handleItemBetweenDrop = (targetIndex: number, draggedItemId: string) => {
    if (!onRearrangeItems) return;
    
    const draggedIndex = items.findIndex(i => i.id === draggedItemId);
    if (draggedIndex === -1) return;
    
    onRearrangeItems(targetIndex, draggedItemId);
    setHoverIndex(null);
  };

  // Handle drag start
  const handleDragStart = (id: string) => {
    setIsDragging(true);
    setActiveDragId(id);
  };

  // Handle drag end
  const handleDragEnd = () => {
    setIsDragging(false);
    setActiveDragId(null);
    setHoverIndex(null);
  };

  // Handle hover over a drop zone
  const handleDropZoneHover = (index: number | null, isOver: boolean) => {
    if (isOver) {
      setHoverIndex(index);
    } else if (hoverIndex === index) {
      setHoverIndex(null);
    }
  };

  // Create a new item from a photo
  const handleCreateItemFromPhoto = (photoId: string) => {
    onCreateItem(photoId);
  };

  // Get unassigned photos
  const unassignedPhotos = photosByItem.get(null) || [];

  // Get the card class based on highlight status
  const getCardClass = (isHighlighted: boolean) => {
    if (!searchQuery) return '';
    
    if (searchMode === SearchMode.Highlight) {
      return isHighlighted 
        ? 'ring-2 ring-blue-500 z-10 scale-105 shadow-lg' 
        : 'opacity-60 grayscale-[30%] scale-95';
    }
    
    return isHighlighted ? 'ring-2 ring-blue-500' : '';
  };

  // Get grid column class based on current setting
  const getGridColumnClass = () => {
    const baseClass = "grid gap-6 ";
    switch (gridColumns) {
      case 1: return baseClass + "grid-cols-1";
      case 2: return baseClass + "grid-cols-1 sm:grid-cols-2";
      case 3: return baseClass + "grid-cols-1 sm:grid-cols-2 md:grid-cols-3";
      case 4: return baseClass + "grid-cols-2 sm:grid-cols-3 md:grid-cols-4";
      case 5: return baseClass + "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5";
      case 6: return baseClass + "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6";
      default: return baseClass + "grid-cols-2 sm:grid-cols-3 md:grid-cols-4";
    }
  };

  // Combined content for co-mingled display
  const combinedContent: ContentItem[] = [...getFilteredItems().map(item => ({ type: 'item' as const, data: item }))];
  
  if (comingleContent) {
    getFilteredPhotos().forEach(photo => {
      combinedContent.push({ type: 'photo' as const, data: photo });
    });
  }

  return (
    <div className="p-4">
      {/* Grid controls */}
      <div className="mb-6 flex flex-wrap gap-4 items-center justify-between">
        <div className="flex gap-2">
          <button 
            onClick={() => setShowItems(!showItems)}
            className={`px-3 py-1 text-sm rounded-md ${showItems ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'}`}
          >
            {showItems ? 'Hide Items' : 'Show Items'}
          </button>
          <button 
            onClick={() => setShowPhotos(!showPhotos)}
            className={`px-3 py-1 text-sm rounded-md ${showPhotos ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'}`}
          >
            {showPhotos ? 'Hide Photos' : 'Show Photos'}
          </button>
          <button 
            onClick={() => setComingleContent(!comingleContent)}
            className={`px-3 py-1 text-sm rounded-md ${comingleContent ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'}`}
          >
            {comingleContent ? 'Separate Sections' : 'Co-mingle Content'}
          </button>
          <button 
            onClick={() => setShowAllPhotos(!showAllPhotos)}
            className={`px-3 py-1 text-sm rounded-md ${showAllPhotos ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'}`}
          >
            {showAllPhotos ? 'Show Unassigned Photos Only' : 'Show All Photos'}
          </button>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Columns:</span>
          <div className="flex">
            {[1, 2, 3, 4, 5, 6].map((cols) => (
              <button
                key={cols}
                onClick={() => setGridColumns(cols as GridColumns)}
                className={`w-8 h-8 flex items-center justify-center rounded-md ${
                  gridColumns === cols ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'
                }`}
              >
                {cols}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Co-mingled content */}
      {comingleContent && (
        <div className="mb-8">
          <div className={`grid gap-6 ${getGridColumnClass()}`}>
            {combinedContent.map((content, index) => {
              const isBeforeActive = hoverIndex === index;
              const isAfterActive = hoverIndex === index + 1;
              const isHighlighted = content.type === 'photo' 
                ? isPhotoHighlighted(content.data as Photo)
                : isItemHighlighted(content.data as Item);
              
              return (
                <div key={content.data.id} className="relative">
                  {/* Drop zone before card */}
                  <DropZone 
                    index={index} 
                    acceptType={content.type === 'photo' ? 'PHOTO' : 'ITEM'}
                    onDrop={content.type === 'photo' ? handlePhotoBetweenDrop : handleItemBetweenDrop}
                    onHover={handleDropZoneHover}
                    isActive={isBeforeActive}
                    orientation="horizontal"
                  />
                  
                  {/* Card component */}
                  <Card
                    key={content.data.id}
                    type={content.type}
                    data={content.data}
                    index={index}
                    isHighlighted={isHighlighted}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                    onCreateItem={handleCreateItemFromPhoto}
                    onRearrange={content.type === 'photo' ? handlePhotoBetweenDrop : handleItemBetweenDrop}
                    isDraggingAny={isDragging}
                    isBeingDragged={activeDragId === content.data.id}
                    searchQuery={searchQuery}
                    onAddPhotoToItem={onAddPhotoToItem}
                    onSelectItem={onSelectItem}
                    onLabelClick={onLabelClick}
                    activeFilterLabel={activeFilterLabel}
                    allPhotos={photos}
                    onDeleteItem={onDeleteItem}
                    onDeletePhoto={onDeletePhoto}
                    className={getCardClass(isHighlighted)}
                  />
                  
                  {/* Drop zone after card (only for the last card in each row) */}
                  {(index + 1) % gridColumns === 0 && (
                    <DropZone 
                      index={index + 1} 
                      acceptType={content.type === 'photo' ? 'PHOTO' : 'ITEM'}
                      onDrop={content.type === 'photo' ? handlePhotoBetweenDrop : handleItemBetweenDrop}
                      onHover={handleDropZoneHover}
                      isActive={isAfterActive}
                      orientation="horizontal"
                    />
                  )}
                  
                  {/* Vertical drop zones between cards */}
                  {index < combinedContent.length - 1 && (index + 1) % gridColumns !== 0 && (
                    <DropZone 
                      index={index + 0.5} 
                      acceptType={content.type === 'photo' ? 'PHOTO' : 'ITEM'}
                      onDrop={content.type === 'photo' ? handlePhotoBetweenDrop : handleItemBetweenDrop}
                      onHover={handleDropZoneHover}
                      isActive={hoverIndex === index + 0.5}
                      orientation="vertical"
                    />
                  )}
                </div>
              );
            })}
            
            {/* Final drop zone at the end */}
            {combinedContent.length > 0 && (
              <DropZone 
                index={combinedContent.length} 
                acceptType="PHOTO"
                onDrop={handlePhotoBetweenDrop}
                onHover={handleDropZoneHover}
                isActive={hoverIndex === combinedContent.length}
                orientation="horizontal"
              />
            )}
            
            {combinedContent.length === 0 && (
              <div className="col-span-full text-gray-500 text-center py-8">
                No content to display
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Separate sections */}
      {!comingleContent && (
        <>
          {/* Items section */}
          {showItems && getFilteredItems().length > 0 && (
            <div className="mb-8">
              <div 
                className="flex items-center justify-between mb-4 cursor-pointer"
                onClick={() => setItemsExpanded(!itemsExpanded)}
              >
                <h2 className="text-lg font-semibold text-gray-900">Items</h2>
                <button className="p-1 rounded-full hover:bg-gray-100">
                  {itemsExpanded ? (
                    <ChevronUpIcon className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                  )}
                </button>
              </div>
              
              {itemsExpanded && (
                <div className={getGridColumnClass()}>
                  {getFilteredItems().map((item, index) => {
                    const isBeforeActive = hoverIndex === index;
                    const isAfterActive = hoverIndex === index + 1;
                    
                    return (
                      <div key={item.id} className="relative">
                        {/* Drop zone before item */}
                        <DropZone 
                          index={index} 
                          acceptType="ITEM"
                          onDrop={handleItemBetweenDrop}
                          onHover={handleDropZoneHover}
                          isActive={isBeforeActive}
                          orientation="horizontal"
                        />
                        
                        {/* Item card */}
                        <Card
                          key={`item-${item.id}`}
                          type="item"
                          data={item}
                          index={index}
                          onSelectItem={onSelectItem}
                          onDragStart={(id) => handleDragStart(id)}
                          onDragEnd={handleDragEnd}
                          onRearrange={onRearrangeItems ? (targetIndex, draggedId) => onRearrangeItems(targetIndex, draggedId) : undefined}
                          onAddPhotoToItem={onAddPhotoToItem}
                          isDraggingAny={isDragging}
                          isBeingDragged={activeDragId === item.id}
                          searchQuery={searchQuery}
                          isHighlighted={isItemHighlighted(item)}
                          onDeleteItem={onDeleteItem}
                          allPhotos={photos}
                          className={getCardClass(isItemHighlighted(item))}
                        />
                        
                        {/* Drop zone after item (only for the last item in each row) */}
                        {(index + 1) % gridColumns === 0 && (
                          <DropZone 
                            index={index + 1} 
                            acceptType="ITEM"
                            onDrop={handleItemBetweenDrop}
                            onHover={handleDropZoneHover}
                            isActive={isAfterActive}
                            orientation="horizontal"
                          />
                        )}
                        
                        {/* Vertical drop zones between items */}
                        {index < getFilteredItems().length - 1 && (index + 1) % gridColumns !== 0 && (
                          <DropZone 
                            index={index + 0.5} 
                            acceptType="ITEM"
                            onDrop={handleItemBetweenDrop}
                            onHover={handleDropZoneHover}
                            isActive={hoverIndex === index + 0.5}
                            orientation="vertical"
                          />
                        )}
                      </div>
                    );
                  })}
                  
                  {/* Final drop zone at the end */}
                  {getFilteredItems().length > 0 && (
                    <DropZone 
                      index={getFilteredItems().length} 
                      acceptType="ITEM"
                      onDrop={handleItemBetweenDrop}
                      onHover={handleDropZoneHover}
                      isActive={hoverIndex === getFilteredItems().length}
                      orientation="horizontal"
                    />
                  )}
                </div>
              )}
            </div>
          )}
          
          {/* Photos section */}
          {showPhotos && (
            <div>
              <div 
                className="flex items-center justify-between mb-4 cursor-pointer"
                onClick={() => setPhotosExpanded(!photosExpanded)}
              >
                <h2 className="text-lg font-semibold text-gray-900">{showAllPhotos ? 'All Photos' : 'Unassigned Photos'}</h2>
                <button className="p-1 rounded-full hover:bg-gray-100">
                  {photosExpanded ? (
                    <ChevronUpIcon className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                  )}
                </button>
              </div>
              
              {photosExpanded && (
                <div className="relative">
                  {/* Grid of photos with drop zones */}
                  <div className={getGridColumnClass()}>
                    {getFilteredPhotos().map((photo, index) => {
                      const isBeforeActive = hoverIndex === index;
                      const isAfterActive = hoverIndex === index + 1;
                      
                      return (
                        <div key={photo.id} className="relative">
                          {/* Drop zone before photo */}
                          <DropZone 
                            index={index} 
                            acceptType="PHOTO"
                            onDrop={handlePhotoBetweenDrop}
                            onHover={handleDropZoneHover}
                            isActive={isBeforeActive}
                            orientation="horizontal"
                          />
                          
                          {/* Photo card */}
                          <Card
                            key={`photo-${photo.id}`}
                            type="photo"
                            data={photo}
                            index={index}
                            onSelect={() => {}}
                            onDragStart={(id) => handleDragStart(id)}
                            onDragEnd={handleDragEnd}
                            onCreateItem={(photoId) => onCreateItem(photoId)}
                            onRearrange={(targetIndex, draggedId) => onRearrangePhotos(targetIndex, draggedId)}
                            isDraggingAny={isDragging}
                            isBeingDragged={activeDragId === photo.id}
                            searchQuery={searchQuery}
                            isHighlighted={isPhotoHighlighted(photo)}
                            onLabelClick={onLabelClick}
                            activeFilterLabel={activeFilterLabel}
                            onDeletePhoto={onDeletePhoto}
                            allPhotos={photos}
                            className={getCardClass(isPhotoHighlighted(photo))}
                          />
                          
                          {/* Drop zone after photo (only for the last photo in each row) */}
                          {(index + 1) % gridColumns === 0 && (
                            <DropZone 
                              index={index + 1} 
                              acceptType="PHOTO"
                              onDrop={handlePhotoBetweenDrop}
                              onHover={handleDropZoneHover}
                              isActive={isAfterActive}
                              orientation="horizontal"
                            />
                          )}
                          
                          {/* Vertical drop zones between photos */}
                          {index < getFilteredPhotos().length - 1 && (index + 1) % gridColumns !== 0 && (
                            <DropZone 
                              index={index + 0.5} 
                              acceptType="PHOTO"
                              onDrop={handlePhotoBetweenDrop}
                              onHover={handleDropZoneHover}
                              isActive={hoverIndex === index + 0.5}
                              orientation="vertical"
                            />
                          )}
                        </div>
                      );
                    })}
                    
                    {/* Final drop zone at the end */}
                    {getFilteredPhotos().length > 0 && (
                      <DropZone 
                        index={getFilteredPhotos().length} 
                        acceptType="PHOTO"
                        onDrop={handlePhotoBetweenDrop}
                        onHover={handleDropZoneHover}
                        isActive={hoverIndex === getFilteredPhotos().length}
                        orientation="horizontal"
                      />
                    )}
                    
                    {getFilteredPhotos().length === 0 && (
                      <div className="col-span-full text-gray-500 text-center py-8">
                        No {(showAllPhotos ? 'photos' : 'unassigned photos')}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
