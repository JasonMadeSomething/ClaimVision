import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import PhotoGrid from '../PhotoGrid';
import { Photo, Item, SearchMode } from '@/types/workbench';

const renderWithDnD = (ui: React.ReactElement) => {
  return render(
    <DndProvider backend={HTML5Backend}>
      {ui}
    </DndProvider>
  );
};

describe('PhotoGrid', () => {
  const mockPhotos: Photo[] = [
    {
      id: '1',
      url: 'test1.jpg',
      fileName: 'test1.jpg',
      labels: [],
      itemId: null,
      roomId: null,
      position: { x: 0, y: 0 },
      uploadedAt: new Date().toISOString(),
    },
    {
      id: '2',
      url: 'test2.jpg',
      fileName: 'test2.jpg',
      labels: [],
      itemId: null,
      roomId: null,
      position: { x: 1, y: 0 },
      uploadedAt: new Date().toISOString(),
    },
  ];

  const mockApis = {
    onCreateItem: jest.fn(),
    onAddPhotoToItem: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Card Layout', () => {
    it('renders photos with correct card layout', () => {
      renderWithDnD(
        <PhotoGrid
          photos={mockPhotos}
          selectedItem={null}
          onCreateItem={mockApis.onCreateItem}
          onAddPhotoToItem={mockApis.onAddPhotoToItem}
          searchMode="highlight"
          searchQuery=""
        />
      );

      const photoCards = screen.getAllByTestId('photo-card');
      photoCards.forEach(card => {
        expect(card).toHaveClass('relative', 'rounded-lg', 'overflow-hidden');
        expect(card.querySelector('img')).toHaveClass('w-full', 'h-full', 'object-cover');
      });
    });

    it('renders items with correct card layout and labels', () => {
      const mockItem: Item = {
        id: 'item1',
        name: 'Test Item',
        description: 'Test description',
        photoIds: ['1', '2'],
        thumbnailPhotoId: '1',
        roomId: 'room1',
        replacementValue: 331,
      };

      renderWithDnD(
        <PhotoGrid
          photos={mockPhotos}
          selectedItem={mockItem}
          onCreateItem={mockApis.onCreateItem}
          onAddPhotoToItem={mockApis.onAddPhotoToItem}
          searchMode="highlight"
          searchQuery=""
        />
      );

      const itemCard = screen.getByTestId('item-card');
      expect(itemCard).toHaveClass('relative', 'rounded-lg', 'overflow-hidden');
      
      // Check for item name label
      expect(screen.getByText('Test Item')).toBeInTheDocument();
      
      // Check for photo count label
      expect(screen.getByText('2 photos')).toBeInTheDocument();
      
      // Check for value label
      expect(screen.getByText('$331')).toBeInTheDocument();
    });

    it('shows correct labels on photos that are part of items', () => {
      const photosWithItems = mockPhotos.map(photo => ({
        ...photo,
        itemId: 'item1'
      }));

      renderWithDnD(
        <PhotoGrid
          photos={photosWithItems}
          selectedItem={null}
          onCreateItem={mockApis.onCreateItem}
          onAddPhotoToItem={mockApis.onAddPhotoToItem}
          searchMode="highlight"
          searchQuery=""
        />
      );

      const itemLabels = screen.getAllByText('Part of Item');
      expect(itemLabels).toHaveLength(2);
      itemLabels.forEach(label => {
        expect(label).toHaveClass('absolute', 'top-2', 'left-2', 'bg-blue-500', 'text-white');
      });
    });
  });
});
