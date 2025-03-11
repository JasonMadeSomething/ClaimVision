import React, { useRef, useEffect } from 'react';
import { useDrop } from 'react-dnd';

interface DropZoneProps {
  index: number;
  acceptType: string;
  onDrop: (index: number, draggedId: string) => void;
  onHover?: (index: number, isOver: boolean) => void;
  isActive?: boolean;
  orientation?: 'horizontal' | 'vertical';
}

const DropZone: React.FC<DropZoneProps> = ({
  index,
  acceptType,
  onDrop,
  onHover,
  isActive = false,
  orientation = 'horizontal',
}) => {
  // Create a ref for the drop zone
  const dropRef = useRef<HTMLDivElement>(null);
  
  // Set up drop target
  const [{ isOver, canDrop }, connectDrop] = useDrop({
    accept: acceptType,
    drop: (item: { id: string }) => {
      onDrop(index, item.id);
      return undefined;
    },
    hover: () => {
      if (onHover) onHover(index, true);
    },
    collect: (monitor) => ({
      isOver: !!monitor.isOver(),
      canDrop: !!monitor.canDrop(),
    }),
  });

  // Connect the drop ref
  connectDrop(dropRef);

  // Call onHover when isOver changes
  useEffect(() => {
    if (onHover) onHover(index, isOver);
    
    // Clean up when component unmounts
    return () => {
      if (onHover) onHover(index, false);
    };
  }, [isOver, index, onHover]);

  // Determine the appropriate class based on orientation and active state
  const getDropZoneClass = () => {
    const baseClass = 'transition-all duration-300 ease-in-out ';
    const isActiveOrOver = isActive || isOver;
    
    if (orientation === 'horizontal') {
      return baseClass + (isActiveOrOver
        ? 'h-16 bg-blue-100 border-2 border-dashed border-blue-400 rounded-md my-4 flex items-center justify-center'
        : canDrop ? 'h-8 border border-dashed border-blue-200 rounded-md my-2' : 'h-2 my-1');
    } else {
      return baseClass + (isActiveOrOver
        ? 'w-8 bg-blue-100 border-2 border-dashed border-blue-400 rounded-md absolute top-0 bottom-0 right-0 translate-x-1/2 z-10 flex items-center justify-center'
        : canDrop ? 'w-4 border border-dashed border-blue-200 rounded-md absolute top-0 bottom-0 right-0 translate-x-1/2 z-10' : 'w-1 absolute top-0 bottom-0 right-0 translate-x-1/2');
    }
  };

  return (
    <div
      ref={dropRef}
      data-testid="drop-zone"
      className={getDropZoneClass()}
      style={orientation === 'vertical' ? { height: '100%' } : {}}
    >
      {(isActive || isOver) && (
        <div className={orientation === 'horizontal' 
          ? 'h-1 w-1/2 bg-blue-400 rounded-full' 
          : 'w-1 h-1/2 bg-blue-400 rounded-full'
        } />
      )}
    </div>
  );
};

export default DropZone;
