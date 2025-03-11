import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import Card from '../Card';
import { Photo, Item } from '@/types/workbench';
import { mockPhotos, mockItems } from '../mocks/mockData';

// Create a wrapper component for DnD testing
const DndWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <DndProvider backend={HTML5Backend}>
    {children}
  </DndProvider>
);

describe('Card Component', () => {
  // Mock functions
  const mockOnDragStart = jest.fn();
  const mockOnDragEnd = jest.fn();
  const mockOnCreateItem = jest.fn();
  const mockOnRearrange = jest.fn();
  const mockOnAddPhotoToItem = jest.fn();
  const mockOnSelectItem = jest.fn();
  const mockOnSelect = jest.fn();

  // Reset mocks before each test
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders a photo card correctly', () => {
    const photo: Photo = mockPhotos[0];
    
    render(
      <DndWrapper>
        <Card
          type="photo"
          data={photo}
          index={0}
          onDragStart={mockOnDragStart}
          onDragEnd={mockOnDragEnd}
          onCreateItem={mockOnCreateItem}
          onRearrange={mockOnRearrange}
          onSelect={mockOnSelect}
        />
      </DndWrapper>
    );

    // Check if the photo card is rendered correctly
    expect(screen.getByText(photo.labels[0])).toBeInTheDocument();
    
    // Check if the image is rendered
    const image = screen.getByRole('img');
    expect(image).toHaveAttribute('src', photo.url);
  });

  it('renders an item card correctly', () => {
    const item: Item = mockItems[0];
    
    render(
      <DndWrapper>
        <Card
          type="item"
          data={item}
          index={0}
          onDragStart={mockOnDragStart}
          onDragEnd={mockOnDragEnd}
          onRearrange={mockOnRearrange}
          onSelectItem={mockOnSelectItem}
        />
      </DndWrapper>
    );

    // Check if the item card is rendered correctly
    expect(screen.getByText(item.name)).toBeInTheDocument();
    expect(screen.getByText(item.description)).toBeInTheDocument();
  });

  it('calls onSelectItem when an item card is clicked', () => {
    const item: Item = mockItems[0];
    
    render(
      <DndWrapper>
        <Card
          type="item"
          data={item}
          index={0}
          onDragStart={mockOnDragStart}
          onDragEnd={mockOnDragEnd}
          onRearrange={mockOnRearrange}
          onSelectItem={mockOnSelectItem}
        />
      </DndWrapper>
    );

    // Click on the card
    fireEvent.click(screen.getByText(item.name));
    
    // Check if onSelectItem was called with the correct item
    expect(mockOnSelectItem).toHaveBeenCalledWith(item);
  });

  it('calls onSelect when a photo card is clicked', () => {
    const photo: Photo = mockPhotos[0];
    
    render(
      <DndWrapper>
        <Card
          type="photo"
          data={photo}
          index={0}
          onDragStart={mockOnDragStart}
          onDragEnd={mockOnDragEnd}
          onCreateItem={mockOnCreateItem}
          onRearrange={mockOnRearrange}
          onSelect={mockOnSelect}
        />
      </DndWrapper>
    );

    // Click on the card
    fireEvent.click(screen.getByText(photo.labels[0]));
    
    // Check if onSelect was called with the correct photo
    expect(mockOnSelect).toHaveBeenCalledWith(photo);
  });

  it('shows "Create Item from Photo" in the menu for unassigned photos', () => {
    const unassignedPhoto: Photo = {...mockPhotos[0], itemId: null};
    
    render(
      <DndWrapper>
        <Card
          type="photo"
          data={unassignedPhoto}
          index={0}
          onDragStart={mockOnDragStart}
          onDragEnd={mockOnDragEnd}
          onCreateItem={mockOnCreateItem}
          onRearrange={mockOnRearrange}
          onSelect={mockOnSelect}
        />
      </DndWrapper>
    );

    // Open the menu
    fireEvent.click(screen.getByRole('button'));
    
    // Check if "Create Item from Photo" is in the menu
    expect(screen.getByText('Create Item from Photo')).toBeInTheDocument();
  });

  it('shows "Edit Item Details" in the menu for item cards', () => {
    const item: Item = mockItems[0];
    
    render(
      <DndWrapper>
        <Card
          type="item"
          data={item}
          index={0}
          onDragStart={mockOnDragStart}
          onDragEnd={mockOnDragEnd}
          onRearrange={mockOnRearrange}
          onSelectItem={mockOnSelectItem}
        />
      </DndWrapper>
    );

    // Open the menu
    fireEvent.click(screen.getByRole('button'));
    
    // Check if "Edit Item Details" is in the menu
    expect(screen.getByText('Edit Item Details')).toBeInTheDocument();
  });
});
