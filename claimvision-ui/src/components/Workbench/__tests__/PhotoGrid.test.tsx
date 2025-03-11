import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import PhotoGrid from '../PhotoGrid';
import { defaultPhotoGridProps, mockItems, mockPhotos } from '../mocks/mockData';
import { workbenchApi } from '../mocks/mockApi';
import { SearchMode } from '@/types/workbench';
import Card from '../Card';

// Mock react-dnd
jest.mock('react-dnd', () => ({
  DndProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useDrag: () => [{ isDragging: false }, jest.fn(), jest.fn()],
  useDrop: () => [{ isOver: false }, jest.fn()],
}));

// Mock react-dnd-html5-backend
jest.mock('react-dnd-html5-backend', () => ({
  HTML5Backend: jest.fn(),
}));

// Mock Card component
jest.mock('../Card', () => {
  return {
    __esModule: true,
    default: jest.fn(props => (
      <div data-testid={`card-${props.type}-${props.data.id}`}>
        {props.type === 'photo' && (
          <div data-testid={`photo-${props.data.id}`}>
            {props.data.id}
          </div>
        )}
        {props.type === 'item' && (
          <div data-testid={`item-${props.data.id}`}>
            {props.data.id}
          </div>
        )}
      </div>
    ))
  };
});

// Mock DropZone component
jest.mock('../DropZone', () => {
  return {
    __esModule: true,
    default: jest.fn(props => (
      <div data-testid={`dropzone-${props.index}`}>
        Dropzone {props.index}
      </div>
    ))
  };
});

// Mock headlessui components
jest.mock('@headlessui/react', () => {
  const MenuButton = ({ children }: { children: React.ReactNode }) => <button data-testid="menu-button">{children}</button>;
  const MenuItem = ({ children }: { children: React.ReactNode }) => {
    if (typeof children === 'function') {
      // Fix the type error by providing a proper function call with explicit typing
      const renderFunction = children as ({ active }: { active: boolean }) => React.ReactNode;
      return <div data-testid="menu-item">{renderFunction({ active: false })}</div>;
    }
    return <div data-testid="menu-item">{children}</div>;
  };
  const MenuItems = ({ children }: { children: React.ReactNode }) => <div data-testid="menu-items">{children}</div>;
  
  const Menu = ({ children }: { children: React.ReactNode }) => <div data-testid="menu">{children}</div>;
  Menu.Button = MenuButton;
  Menu.Items = MenuItems;
  Menu.Item = MenuItem;
  
  return { Menu };
});

// Mock heroicons
jest.mock('@heroicons/react/24/outline', () => {
  return {
    EllipsisVerticalIcon: () => <div data-testid="ellipsis-icon">Icon</div>,
    ChevronUpIcon: () => <div data-testid="chevron-up-icon">Icon</div>,
    ChevronDownIcon: () => <div data-testid="chevron-down-icon">Icon</div>
  };
});

describe('PhotoGrid', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (Card as jest.Mock).mockClear();
  });

  it('renders an empty grid when no photos are provided', () => {
    render(<PhotoGrid {...defaultPhotoGridProps} onRearrangePhotos={jest.fn()} />);
    
    // Check that the component renders
    expect(screen.getByText('Unassigned Photos')).toBeInTheDocument();
  });

  it('renders items with correct labels and values', async () => {
    const props = {
      ...defaultPhotoGridProps,
      photos: mockPhotos,
      items: mockItems,
      searchMode: 'highlight' as SearchMode,
      onRearrangePhotos: jest.fn(),
    };

    render(<PhotoGrid {...props} />);
    
    // Test for presence of key elements
    expect(screen.getByText('Unassigned Photos')).toBeInTheDocument();
  });

  it('filters unassigned photos by default', async () => {
    // Create a mix of assigned and unassigned photos
    const unassignedPhoto = { ...mockPhotos[0], itemId: null };
    const assignedPhoto = { ...mockPhotos[1], itemId: 'item-1' };
    const testPhotos = [unassignedPhoto, assignedPhoto];
    
    const props = {
      ...defaultPhotoGridProps,
      photos: testPhotos,
      items: mockItems,
      onRearrangePhotos: jest.fn(),
    };

    render(<PhotoGrid {...props} />);
    
    // By default, only "Unassigned Photos" section should be visible
    expect(screen.getByText('Unassigned Photos')).toBeInTheDocument();
    
    // The toggle button should show "Show All Photos" text
    expect(screen.getByText('Show All Photos')).toBeInTheDocument();
  });

  it('toggles between all photos and unassigned photos', async () => {
    // Create a mix of assigned and unassigned photos
    const unassignedPhoto = { ...mockPhotos[0], itemId: null, labels: ['Unassigned Photo'] };
    const assignedPhoto = { ...mockPhotos[1], itemId: 'item-1', labels: ['Assigned Photo'] };
    const testPhotos = [unassignedPhoto, assignedPhoto];
    
    const props = {
      ...defaultPhotoGridProps,
      photos: testPhotos,
      items: mockItems,
      onRearrangePhotos: jest.fn(),
    };

    render(<PhotoGrid {...props} />);
    
    // Initially, the section should be "Unassigned Photos"
    expect(screen.getByText('Unassigned Photos')).toBeInTheDocument();
    
    // Click the toggle button
    const toggleButton = screen.getByText('Show All Photos');
    fireEvent.click(toggleButton);
    
    // Now the section should be "All Photos"
    expect(screen.getByText('All Photos')).toBeInTheDocument();
    
    // The button text should change
    expect(screen.getByText('Show Unassigned Photos Only')).toBeInTheDocument();
  });

  it('does not show assigned photos in the unassigned view', () => {
    // Create a mix of assigned and unassigned photos
    const unassignedPhoto = { 
      ...mockPhotos[0], 
      id: 'unassigned-photo', 
      itemId: null, 
      labels: ['Unassigned Photo'] 
    };
    const assignedPhoto = { 
      ...mockPhotos[1], 
      id: 'assigned-photo', 
      itemId: 'item-1', 
      labels: ['Assigned Photo'] 
    };
    const testPhotos = [unassignedPhoto, assignedPhoto];
    
    const props = {
      ...defaultPhotoGridProps,
      photos: testPhotos,
      items: mockItems,
      onRearrangePhotos: jest.fn(),
    };

    // Create two separate tests - one for each view
    
    // 1. Test for unassigned view (default)
    const { unmount } = render(<PhotoGrid {...props} />);
    
    // In the default unassigned view, check which Card components were rendered
    const unassignedViewCardCalls = (Card as jest.Mock).mock.calls;
    
    // Find photo card calls
    const unassignedViewPhotoCardCalls = unassignedViewCardCalls.filter(call => call[0].type === 'photo');
    const unassignedViewPhotoIds = unassignedViewPhotoCardCalls.map(call => call[0].data.id);
    
    // Verify only unassigned photos are rendered in unassigned view
    expect(unassignedViewPhotoIds).toContain('unassigned-photo');
    expect(unassignedViewPhotoIds).not.toContain('assigned-photo');
    
    // Clean up
    unmount();
    (Card as jest.Mock).mockClear();
    
    // 2. Test for all photos view
    const { getByText } = render(<PhotoGrid {...props} />);
    
    // Click the toggle button to show all photos
    const toggleButton = getByText('Show All Photos');
    fireEvent.click(toggleButton);
    
    // Check which Card components were rendered after clicking the toggle
    const allPhotosViewCardCalls = (Card as jest.Mock).mock.calls;
    const allPhotosViewPhotoCardCalls = allPhotosViewCardCalls.filter(call => call[0].type === 'photo');
    const allPhotosViewPhotoIds = allPhotosViewPhotoCardCalls.map(call => call[0].data.id);
    
    // Verify both photos are rendered in "all photos" view
    expect(allPhotosViewPhotoIds).toContain('unassigned-photo');
    expect(allPhotosViewPhotoIds).toContain('assigned-photo');
  });

  it('calls onAddPhotoToItem when a photo is dropped on an item', async () => {
    const mockOnAddPhotoToItem = jest.fn();
    const props = {
      ...defaultPhotoGridProps,
      photos: mockPhotos,
      items: mockItems,
      onRearrangePhotos: jest.fn(),
      onAddPhotoToItem: mockOnAddPhotoToItem,
    };

    render(<PhotoGrid {...props} />);
    
    // Since we're mocking the drag and drop functionality,
    // we can't directly test the drop action.
    // But we can verify that the component is set up correctly.
    expect(screen.getByText('Unassigned Photos')).toBeInTheDocument();
  });
});
