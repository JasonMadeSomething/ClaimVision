import React, { useRef, useState, useEffect } from 'react';
import { Photo, Item } from '@/types/workbench';
import { useDrag, useDrop } from 'react-dnd';
import { Menu } from '@headlessui/react';
import { EllipsisVerticalIcon, CubeIcon, TrashIcon } from '@heroicons/react/24/outline';
import { useAuth } from '@/context/AuthContext';

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
  onDeleteItem?: (itemId: string) => void;
  onDeletePhoto?: (photoId: string) => void;
  isDraggingAny?: boolean;
  isBeingDragged?: boolean;
  searchQuery?: string;
  isHighlighted?: boolean;
  className?: string;
  onLabelClick?: (label: string) => void;
  activeFilterLabel?: string;
  allPhotos?: Photo[];
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
  onDeleteItem,
  onDeletePhoto,
  isDraggingAny = false,
  isBeingDragged = false,
  searchQuery = '',
  isHighlighted = false,
  className = '',
  onLabelClick,
  activeFilterLabel = '',
  allPhotos = [],
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
    hover: (item: { id: string; index: number }, _) => {
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
  const [imageUrl, setImageUrl] = useState(isPhoto(data) ? data.url : isItem(data) && data.thumbnailPhotoId ? (() => {
    // Find the thumbnail photo in the allPhotos array
    const thumbnailPhoto = allPhotos.find(p => p.id === data.thumbnailPhotoId);
    return thumbnailPhoto?.url || '/placeholder-image.jpg';
  })() : '/placeholder-image.jpg');

  useEffect(() => {
    // Function to fetch file URL if needed
    const fetchFileUrl = async () => {
      // Case 1: If this is a photo without a URL, fetch it
      if (isPhoto(data) && !data.url) {
        await fetchPhotoUrl(data.id);
      }
      // Case 2: If this is an item with a thumbnail but no URL in the corresponding photo
      else if (isItem(data) && data.thumbnailPhotoId) {
        const thumbnailPhoto = allPhotos.find(p => p.id === data.thumbnailPhotoId);
        if (!thumbnailPhoto?.url) {
          await fetchPhotoUrl(data.thumbnailPhotoId);
        }
      }
    };

    fetchFileUrl();
  }, [data, allPhotos]);

  // Function to fetch a photo URL from the API
  const { user } = useAuth();
  const fetchPhotoUrl = async (photoId: string) => {
    if (!user?.id_token) {
      console.error("Cannot fetch photo URL: User not authenticated");
      return;
    }

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY;
      const response = await fetch(`${baseUrl}/files?ids=${photoId}`, {
        headers: {
          'Authorization': `Bearer ${user.id_token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch photo URL: ${response.status}`);
      }

      const data = await response.json();

      if (data?.data?.files && data.data.files.length > 0) {
        const fileData = data.data.files[0];
        if (fileData.url) {
          setImageUrl(fileData.url);
          console.log(`Successfully fetched URL for photo ${photoId}`);
        } else {
          console.warn(`No URL available for photo ${photoId}`);
          setImageUrl('/placeholder-image.jpg');
        }
      } else {
        console.warn(`Photo ${photoId} not found in response`);
        setImageUrl('/placeholder-image.jpg');
      }
    } catch (error) {
      console.error("Error fetching photo URL:", error);
      setImageUrl('/placeholder-image.jpg');
    }
  };

  // Get the title
  const title = isPhoto(data) ? data.fileName : isItem(data) ? data.name : '';

  // Get the labels
  const labels = isPhoto(data) ? data.labels : [];

  // State for tooltip visibility
  const [showTooltip, setShowTooltip] = useState(false);

  // Get the description (items only)
  const description = isItem(data) ? data.description : '';

  // Get the unit cost (items only)
  const unitCost = isItem(data) ? data.unit_cost : null;

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
        ${isItem(data) ? 'border-2 border-indigo-200' : ''}
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
      <div className="aspect-square overflow-hidden relative">
        <img
          src={imageUrl}
          alt={title}
          className="w-full h-full object-cover"
        />

        {/* Item indicator overlay */}
        {isItem(data) && (
          <div className="absolute top-2 right-2 bg-indigo-100 rounded-full p-1.5 shadow-md">
            <CubeIcon className="h-5 w-5 text-indigo-600" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className={`p-3 ${isItem(data) ? 'bg-indigo-50' : ''}`}>
        {/* Title with type indicator */}
        <div className="flex justify-between items-start mb-2">
          <h3 className={`font-medium truncate ${isItem(data) ? 'text-indigo-900' : 'text-gray-900'}`}>
            {isItem(data) && <span className="text-xs font-bold text-indigo-600 mr-1">ITEM</span>}
            {title}
          </h3>
        </div>

        {/* Labels */}
        {Array.isArray(labels) && labels.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {labels.slice(0, 3).map((label, idx) => (
            <span
              key={idx}
              className={`
                inline-block px-2 py-1 text-xs rounded-full cursor-pointer
                ${activeFilterLabel === label
                  ? 'bg-blue-500 text-white'
                  : isHighlighted && label.toLowerCase().includes((searchQuery || '').toLowerCase())
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
                onClick={(e) => {
                  e.stopPropagation(); // Prevent card selection
                  setShowTooltip(!showTooltip); // Toggle tooltip on click
                }}
              >
                +{labels.length - 3}
              </span>

              {/* Tooltip for remaining labels */}
              {showTooltip && (
                <div
                  className="absolute z-50 bottom-full left-0 mb-2 p-2 bg-white rounded-md shadow-lg border border-gray-200 min-w-48 max-w-xs"
                >
                  <div className="flex flex-wrap gap-1">
                    {labels.slice(3).map((label, idx) => (
                      <span
                        key={idx}
                        className={`
                          inline-block px-2 py-1 text-xs rounded-full cursor-pointer
                          ${activeFilterLabel === label
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
                        `}
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
                  <button
                    className="absolute top-1 right-1 text-gray-400 hover:text-gray-600"
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowTooltip(false);
                    }}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
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
            {unitCost !== null && unitCost !== undefined && (
              <p className="text-sm font-medium text-gray-900">
                Unit Cost: ${Number(unitCost).toFixed(2)}
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
              {isItem(data) && onDeleteItem && (
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => {
                        if (window.confirm('Are you sure you want to delete this item?')) {
                          onDeleteItem(data.id);
                        }
                      }}
                      className={`${
                        active ? 'bg-red-100' : ''
                      } w-full text-left px-2 py-1 text-sm rounded-md text-red-600 flex items-center`}
                    >
                      <TrashIcon className="h-4 w-4 mr-2" />
                      Delete Item
                    </button>
                  )}
                </Menu.Item>
              )}
              {isPhoto(data) && onDeletePhoto && (
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => {
                        if (window.confirm('Are you sure you want to delete this photo?')) {
                          onDeletePhoto(data.id);
                        }
                      }}
                      className={`${
                        active ? 'bg-red-100' : ''
                      } w-full text-left px-2 py-1 text-sm rounded-md text-red-600 flex items-center`}
                    >
                      <TrashIcon className="h-4 w-4 mr-2" />
                      Delete Photo
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
