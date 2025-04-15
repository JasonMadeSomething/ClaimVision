import React, { useRef, useState } from 'react';
import { Photo, Item, SearchMode } from '@/types/workbench';
import { useDrag, useDrop } from 'react-dnd';
import { Menu } from '@headlessui/react';
import { EllipsisVerticalIcon } from '@heroicons/react/24/outline';

// Type guards for Photo and Item
const isPhoto = (data: Photo | Item): data is Photo => {
  return 'url' in data;
};

const isItem = (data: Photo | Item): data is Item => {
  return 'name' in data;
};

interface CardProps {
  type: 'photo' | 'item';
  data: Photo | Item;
  index: number;
  onSelect?: (data: Photo | Item) => void;
  onSelectItem?: (item: Item) => void;
  onDragStart?: (id: string) => void;
  onDragEnd?: () => void;
  onCreateItem?: (photoId: string) => void;
  onRearrange?: (targetIndex: number, draggedId: string) => void;
  onAddPhotoToItem?: (itemId: string, photoId: string) => void;
  isDraggingAny?: boolean;
  isBeingDragged?: boolean;
  searchQuery?: string;
  isHighlighted?: boolean;
  className?: string;
  onLabelClick?: (label: string) => void;
}

const Card: React.FC<CardProps> = ({
  type,
  data,
  index,
  onSelect,
  onSelectItem,
  onDragStart,
  onDragEnd,
  onCreateItem,
  onRearrange,
  onAddPhotoToItem,
  isDraggingAny = false,
  isBeingDragged = false,
  searchQuery = '',
  isHighlighted = false,
  className = '',
  onLabelClick,
}) => {
  // Create refs
  const ref = useRef<HTMLDivElement>(null);
  
  // Define the drag functionality
  const [{ isDragging }, drag] = useDrag({
    type: type.toUpperCase(),
    item: () => {
      if (onDragStart) onDragStart(data.id);
      const dragItem = { 
        id: data.id, 
        index, 
        type: type.toUpperCase() 
      };
      console.log("Dragging item with type:", dragItem.type);
      return dragItem;
    },
    end: () => {
      if (onDragEnd) onDragEnd();
    },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  // Define the drop functionality for rearranging
  const [{ isOver }, drop] = useDrop({
    accept: type.toUpperCase(),
    hover: (item: { id: string; index: number }, monitor) => {
      if (item.id === data.id) return;
      if (onRearrange) {
        onRearrange(index, item.id);
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  });

  // Define the drop functionality for item cards
  const [{ isOver: isPhotoOver }, dropPhoto] = useDrop({
    accept: "PHOTO",
    drop: (item: { id: string; index: number }) => {
      if (isItem(data) && onAddPhotoToItem) {
        onAddPhotoToItem(data.id, item.id);
      }
      return undefined;
    },
    canDrop: () => {
      // Only allow dropping photos onto item cards
      return isItem(data);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  });

  // Apply the drag and drop refs
  const mergedRef = (node: HTMLDivElement | null) => {
    ref.current = node;
    drag(node);
    drop(node);
    if (isItem(data)) {
      dropPhoto(node);
    }
  };

  // Get the image URL
  const imageUrl = isPhoto(data) 
    ? data.url 
    : isItem(data) && data.thumbnailPhotoId 
      ? `/api/photos/${data.thumbnailPhotoId}` 
      : '/placeholder-image.jpg';

  // Get the title
  const title = isPhoto(data) ? data.fileName : isItem(data) ? data.name : '';

  // Get the labels
  const labels = isPhoto(data) ? data.labels : [];
  
  // State for tooltip visibility
  const [showTooltip, setShowTooltip] = useState(false);

  // Get the description (items only)
  const description = isItem(data) ? data.description : '';

  // Get the replacement value (items only)
  const replacementValue = isItem(data) ? data.replacementValue : null;

  return (
    <div
      ref={mergedRef}
      className={`
        relative bg-white rounded-lg shadow-md overflow-hidden transition-all duration-300 ease-in-out
        ${isDragging ? 'opacity-30 scale-95 shadow-none' : 'opacity-100'}
        ${isOver ? 'ring-2 ring-blue-400 transform translate-y-1' : ''}
        ${isPhotoOver ? 'ring-2 ring-green-500 transform scale-105' : ''}
        ${isHighlighted ? 'ring-2 ring-blue-500' : ''}
        ${isBeingDragged ? 'scale-105 z-20 shadow-xl rotate-1' : ''}
        ${isDraggingAny && !isBeingDragged ? 'scale-95 transition-transform duration-200' : ''}
        hover:shadow-lg
        ${className}
      `}
      style={{ 
        touchAction: 'none',
        transform: isBeingDragged ? 'rotate(2deg)' : undefined
      }}
      onClick={() => {
        if (onSelect) onSelect(data);
        if (onSelectItem && isItem(data)) onSelectItem(data);
      }}
    >
      {/* Image */}
      <div className="aspect-square overflow-hidden">
        <img
          src={imageUrl}
          alt={title}
          className="w-full h-full object-cover"
        />
      </div>

      {/* Content */}
      <div className="p-3">
        {/* Title */}
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-medium text-gray-900 truncate">{title}</h3>
        </div>

        {/* Labels */}
        {Array.isArray(labels) && labels.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {labels.slice(0, 3).map((label, idx) => (
            <span
              key={idx}
              className={`
                inline-block px-2 py-1 text-xs rounded-full cursor-pointer
                ${isHighlighted && label.toLowerCase().includes((searchQuery || '').toLowerCase())
                  ? 'bg-blue-100 text-blue-800' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
              `}
              onClick={(e) => {
                e.stopPropagation(); // Prevent card selection
                if (onLabelClick) onLabelClick(label);
              }}
            >
              {label}
            </span>
          ))}
          {labels.length > 3 && (
            <div className="relative">
              <span 
                className="inline-block px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200 cursor-pointer"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                onClick={(e) => {
                  e.stopPropagation(); // Prevent card selection
                  // We don't do anything on click for the +n label itself
                }}
              >
                +{labels.length - 3}
              </span>
              
              {/* Tooltip for remaining labels */}
              {showTooltip && (
                <div className="absolute z-50 bottom-full left-0 mb-2 p-2 bg-white rounded-md shadow-lg border border-gray-200 min-w-48 max-w-xs">
                  <div className="flex flex-wrap gap-1">
                    {labels.slice(3).map((label, idx) => (
                      <span
                        key={idx}
                        className="inline-block px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200 cursor-pointer"
                        onClick={(e) => {
                          e.stopPropagation(); // Prevent card selection
                          if (onLabelClick) onLabelClick(label);
                          setShowTooltip(false);
                        }}
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                  <div className="absolute bottom-0 left-4 transform translate-y-1/2 rotate-45 w-2 h-2 bg-white border-r border-b border-gray-200"></div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
        
        {/* Item-specific details */}
        {type === 'item' && isItem(data) && (
          <>
            {description && (
              <p className="text-sm text-gray-600 mb-2 line-clamp-2">{description}</p>
            )}
            {replacementValue !== null && (
              <p className="text-sm font-medium text-gray-900">
                Value: ${replacementValue.toFixed(2)}
              </p>
            )}
          </>
        )}
      </div>

      <div className="absolute top-1 right-1" onClick={(e) => e.stopPropagation()}>
        <Menu as="div" className="relative inline-block text-left">
          <Menu.Button className="p-1 rounded-full bg-white/80 hover:bg-white text-gray-500 hover:text-gray-700">
            <EllipsisVerticalIcon className="h-4 w-4" />
          </Menu.Button>
          <Menu.Items className="absolute right-0 mt-1 w-40 bg-white rounded-md shadow-lg z-20">
            <div className="p-1">
              {isPhoto(data) && (
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => onSelect && onSelect(data)}
                      className={`${
                        active ? 'bg-gray-100' : ''
                      } w-full text-left px-2 py-1 text-sm rounded-md`}
                    >
                      View Photo Details
                    </button>
                  )}
                </Menu.Item>
              )}
              {isPhoto(data) && !data.itemId && (
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => onCreateItem && onCreateItem(data.id)}
                      className={`${
                        active ? 'bg-gray-100' : ''
                      } w-full text-left px-2 py-1 text-sm rounded-md`}
                    >
                      Create Item from Photo
                    </button>
                  )}
                </Menu.Item>
              )}
              {isItem(data) && (
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => onSelectItem && onSelectItem(data)}
                      className={`${
                        active ? 'bg-gray-100' : ''
                      } w-full text-left px-2 py-1 text-sm rounded-md`}
                    >
                      Edit Item Details
                    </button>
                  )}
                </Menu.Item>
              )}
            </div>
          </Menu.Items>
        </Menu>
      </div>
    </div>
  );
};

export default Card;
