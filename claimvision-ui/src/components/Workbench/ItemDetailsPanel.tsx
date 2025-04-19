import { useState, useRef, useEffect } from "react";
import { XMarkIcon, ArrowPathIcon, HomeIcon, ArrowsRightLeftIcon, TagIcon, TrashIcon } from "@heroicons/react/24/outline";
import { Item, Photo, Room } from "@/types/workbench";

interface ItemDetailsPanelProps {
  item: Item;
  photos: Photo[];
  rooms: Room[];
  onClose: () => void;
  onUpdate: (item: Item) => void;
  onRemovePhoto: (photoId: string) => void;
  onChangeThumbnail: () => void;
  onMoveToRoom: (roomId: string | null) => void;
  onAddPhoto: (itemId: string, photoId: string) => void;
  onDeleteItem?: () => void;
  onDeletePhoto?: (photoId: string) => void;
}

interface EditableFieldProps {
  value: string;
  onSave: (value: string) => void | Promise<void>;
  placeholder?: string;
  multiline?: boolean;
  validate?: (value: string) => string | null;
  'data-testid'?: string;
}

const EditableField = ({ value, onSave, placeholder, multiline, validate, 'data-testid': dataTestId }: EditableFieldProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  // Update editValue when value prop changes
  useEffect(() => {
    setEditValue(value);
  }, [value]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleSave = async () => {
    if (editValue !== value) {
      const validationError = validate?.(editValue);
      if (validationError) {
        setError(validationError);
        return;
      }
      setError(null);
      try {
        await onSave(editValue);
        setIsEditing(false);
      } catch (err) {
        // Keep the edited value but show error in parent
        return;
      }
    } else {
      setIsEditing(false);
    }
  };

  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      await handleSave();
    }
    if (e.key === 'Escape') {
      setEditValue(value);
      setError(null);
      setIsEditing(false);
    }
  };

  const commonProps = {
    value: editValue,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setEditValue(e.target.value);
      setError(null);
    },
    onBlur: handleSave,
    onKeyDown: handleKeyDown,
    className: `w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${error ? 'border-red-500' : ''}`,
    placeholder,
    'data-testid': `${dataTestId}-input`,
  };

  if (isEditing) {
    return (
      <div>
        {multiline ? (
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            rows={3}
            {...commonProps}
          />
        ) : (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="text"
            {...commonProps}
          />
        )}
        {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
      </div>
    );
  }

  return (
    <div
      onClick={() => setIsEditing(true)}
      className="cursor-pointer p-2 rounded-md hover:bg-gray-100"
      data-testid={dataTestId}
    >
      {editValue || <span className="text-gray-400">{placeholder}</span>}
    </div>
  );
};

const validateName = (value: string) => {
  if (!value.trim()) {
    return 'Name is required';
  }
  return null;
};

const validateValue = (value: string) => {
  const numValue = Number(value);
  if (isNaN(numValue)) {
    return 'Value must be a number';
  }
  if (numValue < 0) {
    return 'Value must be positive';
  }
  return null;
};

export default function ItemDetailsPanel({
  item,
  photos,
  rooms,
  onClose,
  onUpdate,
  onRemovePhoto,
  onChangeThumbnail,
  onMoveToRoom,
  onAddPhoto,
  onDeleteItem,
  onDeletePhoto
}: ItemDetailsPanelProps) {
  const [error, setError] = useState<string | null>(null);
  const [selectedLabels, setSelectedLabels] = useState<string[]>([]);
  const thumbnailPhoto = photos.find(p => p.id === item.thumbnailPhotoId);

  // Collect all unique labels from photos
  const allLabels = Array.from(
    new Set(
      photos.flatMap(photo => photo.labels || [])
    )
  ).sort();

  // Filter photos based on selected labels
  const filteredPhotos = selectedLabels.length > 0
    ? photos.filter(photo => 
        selectedLabels.some(label => photo.labels && photo.labels.includes(label))
      )
    : photos;

  const handleUpdateField = async (field: keyof Item, value: any) => {
    try {
      await onUpdate({
        ...item,
        [field]: value,
      });
      setError(null);
    } catch (err) {
      setError('Failed to update item');
      throw err; // Re-throw to let EditableField know the save failed
    }
  };

  const toggleLabel = (label: string) => {
    setSelectedLabels(prev => 
      prev.includes(label)
        ? prev.filter(l => l !== label)
        : [...prev, label]
    );
  };

  return (
    <div className="w-96 border-l border-gray-200 bg-white overflow-y-auto h-full shadow-lg">
      <div className="sticky top-0 bg-white z-10 border-b border-gray-200">
        <div className="flex justify-between items-center mb-4 border-b pb-2">
          <h2 className="text-xl font-semibold">Item Details</h2>
          <div className="flex space-x-2">
            {onDeleteItem && (
              <button 
                onClick={() => {
                  if (window.confirm('Are you sure you want to delete this item?')) {
                    onDeleteItem();
                    onClose();
                  }
                }}
                className="p-1.5 rounded-full text-red-600 hover:bg-red-50"
                title="Delete Item"
              >
                <TrashIcon className="h-5 w-5" />
              </button>
            )}
            <button 
              onClick={onClose} 
              className="p-1.5 rounded-full text-gray-500 hover:bg-gray-100"
              title="Close Panel"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      <div className="p-4">
        {error && (
          <div className="mb-4 p-2 bg-red-100 text-red-700 rounded-md">
            {error}
          </div>
        )}

        {/* Thumbnail section */}
        <div className="mb-6 relative">
          {thumbnailPhoto ? (
            <div className="relative rounded-lg overflow-hidden h-48">
              <img
                src={thumbnailPhoto.url}
                alt={item.name}
                className="w-full h-full object-cover"
              />
              <button
                onClick={onChangeThumbnail}
                className="absolute bottom-2 right-2 p-2 bg-white rounded-full shadow-md hover:bg-gray-100 transition-colors"
                aria-label="Change thumbnail"
                data-testid="change-thumbnail-button"
              >
                <ArrowPathIcon className="h-5 w-5 text-gray-700" />
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 bg-gray-100 rounded-lg">
              <p className="text-gray-500">No thumbnail available</p>
            </div>
          )}
        </div>

        {/* Item details form */}
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <EditableField
              value={item.name}
              onSave={(value) => handleUpdateField('name', value)}
              placeholder="Enter item name"
              validate={validateName}
              data-testid="name-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <EditableField
              value={item.description || ''}
              onSave={(value) => handleUpdateField('description', value)}
              placeholder="Enter description"
              multiline
              data-testid="description-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Unit Cost ($)
            </label>
            <EditableField
              value={item.unit_cost?.toString() || ''}
              onSave={(value) => handleUpdateField('unit_cost', Number(value))}
              placeholder="Enter unit cost"
              validate={validateValue}
              data-testid="unit-cost-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Quantity
            </label>
            <EditableField
              value={item.quantity?.toString() || '1'}
              onSave={(value) => handleUpdateField('quantity', Number(value))}
              placeholder="Enter quantity"
              validate={validateValue}
              data-testid="quantity-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Brand/Manufacturer
            </label>
            <EditableField
              value={item.brand_manufacturer || ''}
              onSave={(value) => handleUpdateField('brand_manufacturer', value)}
              placeholder="Enter brand or manufacturer"
              data-testid="brand-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Model Number
            </label>
            <EditableField
              value={item.model_number || ''}
              onSave={(value) => handleUpdateField('model_number', value)}
              placeholder="Enter model number"
              data-testid="model-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Original Vendor
            </label>
            <EditableField
              value={item.original_vendor || ''}
              onSave={(value) => handleUpdateField('original_vendor', value)}
              placeholder="Enter original vendor"
              data-testid="vendor-field"
            />
          </div>

          <div className="flex space-x-4">
            <div className="w-1/2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Age (Years)
              </label>
              <EditableField
                value={item.age_years?.toString() || ''}
                onSave={(value) => handleUpdateField('age_years', Number(value))}
                placeholder="Years"
                validate={validateValue}
                data-testid="age-years-field"
              />
            </div>
            <div className="w-1/2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Age (Months)
              </label>
              <EditableField
                value={item.age_months?.toString() || ''}
                onSave={(value) => handleUpdateField('age_months', Number(value))}
                placeholder="Months"
                validate={validateValue}
                data-testid="age-months-field"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Condition
            </label>
            <select
              value={item.condition || ''}
              onChange={(e) => handleUpdateField('condition', e.target.value)}
              className="w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              data-testid="condition-select"
            >
              <option value="">Select condition</option>
              <option value="New">New</option>
              <option value="Good">Good</option>
              <option value="Average">Average</option>
              <option value="Bad">Bad</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Room
            </label>
            <select
              value={item.roomId || ''}
              onChange={(e) => onMoveToRoom(e.target.value || null)}
              className="w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              data-testid="room-select"
            >
              <option value="">No Room</option>
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Labels section */}
        {allLabels.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center mb-2">
              <TagIcon className="h-4 w-4 text-gray-700 mr-1" />
              <h3 className="text-sm font-medium text-gray-700">Labels</h3>
            </div>
            <div className="flex flex-wrap gap-2" data-testid="labels-container">
              {allLabels.map(label => (
                <button
                  key={label}
                  onClick={() => toggleLabel(label)}
                  className={`
                    text-xs px-2 py-1 rounded-full
                    ${selectedLabels.includes(label)
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
                    transition-colors
                  `}
                  data-testid="label-button"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Photos section */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            Photos {selectedLabels.length > 0 && `(Filtered: ${selectedLabels.join(', ')})`}
          </h3>
          {selectedLabels.length > 0 && (
            <button
              onClick={() => setSelectedLabels([])}
              className="text-xs text-blue-500 mb-2 hover:underline"
              data-testid="clear-filters-button"
            >
              Clear filters
            </button>
          )}
          <div className="grid grid-cols-2 gap-2">
            {filteredPhotos.map((photo) => (
              <div 
                key={photo.id} 
                className="relative rounded-lg overflow-hidden"
                data-testid="photo-item"
              >
                <img
                  src={photo.url}
                  alt={photo.fileName}
                  className="w-full h-24 object-cover"
                />
                {photo.labels && photo.labels.length > 0 && (
                  <div className="absolute bottom-0 left-0 right-0 bg-black/50 p-1">
                    <div className="flex flex-wrap gap-1">
                      {photo.labels.map((label, index) => (
                        <span 
                          key={index} 
                          className={`
                            text-xs px-1 py-0.5 rounded
                            ${selectedLabels.includes(label) 
                              ? 'bg-blue-500 text-white' 
                              : 'bg-gray-500 text-white'}
                          `}
                          data-testid="photo-label"
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <div className="flex space-x-1">
                    <button 
                      onClick={() => onRemovePhoto(photo.id)}
                      className="p-1 bg-white rounded-full shadow-md hover:bg-gray-100"
                      title="Remove from Item"
                    >
                      <XMarkIcon className="h-4 w-4 text-gray-700" />
                    </button>
                    <button 
                      onClick={() => {
                        onUpdate({
                          ...item,
                          thumbnailPhotoId: photo.id
                        });
                      }}
                      className="p-1 bg-white rounded-full shadow-md hover:bg-gray-100"
                      title="Set as Thumbnail"
                    >
                      <ArrowPathIcon className="h-4 w-4 text-gray-700" />
                    </button>
                    {onDeletePhoto && (
                      <button 
                        onClick={() => {
                          if (window.confirm('Are you sure you want to delete this photo?')) {
                            onDeletePhoto(photo.id);
                          }
                        }}
                        className="p-1 bg-white rounded-full shadow-md hover:bg-red-100"
                        title="Delete Photo"
                      >
                        <TrashIcon className="h-4 w-4 text-red-600" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
