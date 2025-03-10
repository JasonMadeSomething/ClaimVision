import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ItemDetailsPanel from '../ItemDetailsPanel';
import { Item } from '@/types/workbench';

describe('ItemDetailsPanel', () => {
  const mockItem: Item = {
    id: '1',
    name: 'Test Item',
    description: 'Test Description',
    thumbnailPhotoId: '1',
    photoIds: ['1', '2'],
    roomId: 'room1',
    replacementValue: 100,
  };

  const mockApis = {
    onUpdateItem: jest.fn(),
    onRemovePhoto: jest.fn(),
    onSetThumbnail: jest.fn(),
    onClose: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock fetch for API calls
    global.fetch = jest.fn();
  });

  describe('API Interactions', () => {
    it('calls API when updating item name', async () => {
      const user = userEvent.setup();
      render(
        <ItemDetailsPanel
          item={mockItem}
          onUpdateItem={mockApis.onUpdateItem}
          onRemovePhoto={mockApis.onRemovePhoto}
          onSetThumbnail={mockApis.onSetThumbnail}
          onClose={mockApis.onClose}
        />
      );

      // Find and edit the name field
      const nameField = screen.getByDisplayValue('Test Item');
      await user.clear(nameField);
      await user.type(nameField, 'Updated Item');
      await user.tab(); // Trigger blur event

      // Verify API call
      expect(mockApis.onUpdateItem).toHaveBeenCalledWith({
        ...mockItem,
        name: 'Updated Item',
      });

      // Verify fetch was called with correct parameters
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/items/${mockItem.id}`,
        expect.objectContaining({
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: expect.stringContaining('"name":"Updated Item"'),
        })
      );
    });

    it('calls API when updating replacement value', async () => {
      const user = userEvent.setup();
      render(
        <ItemDetailsPanel
          item={mockItem}
          onUpdateItem={mockApis.onUpdateItem}
          onRemovePhoto={mockApis.onRemovePhoto}
          onSetThumbnail={mockApis.onSetThumbnail}
          onClose={mockApis.onClose}
        />
      );

      const valueField = screen.getByDisplayValue('100');
      await user.clear(valueField);
      await user.type(valueField, '200');
      await user.tab();

      expect(mockApis.onUpdateItem).toHaveBeenCalledWith({
        ...mockItem,
        replacementValue: 200,
      });

      expect(global.fetch).toHaveBeenCalledWith(
        `/api/items/${mockItem.id}`,
        expect.objectContaining({
          method: 'PUT',
          body: expect.stringContaining('"replacementValue":200'),
        })
      );
    });

    it('calls API when removing a photo', async () => {
      const user = userEvent.setup();
      render(
        <ItemDetailsPanel
          item={mockItem}
          onUpdateItem={mockApis.onUpdateItem}
          onRemovePhoto={mockApis.onRemovePhoto}
          onSetThumbnail={mockApis.onSetThumbnail}
          onClose={mockApis.onClose}
        />
      );

      const removeButton = screen.getAllByLabelText('Remove photo')[0];
      await user.click(removeButton);

      expect(mockApis.onRemovePhoto).toHaveBeenCalledWith('1');
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/items/${mockItem.id}/photos/1`,
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('calls API when setting thumbnail photo', async () => {
      const user = userEvent.setup();
      render(
        <ItemDetailsPanel
          item={mockItem}
          onUpdateItem={mockApis.onUpdateItem}
          onRemovePhoto={mockApis.onRemovePhoto}
          onSetThumbnail={mockApis.onSetThumbnail}
          onClose={mockApis.onClose}
        />
      );

      const setThumbnailButton = screen.getAllByLabelText('Set as thumbnail')[1];
      await user.click(setThumbnailButton);

      expect(mockApis.onSetThumbnail).toHaveBeenCalledWith('2');
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/items/${mockItem.id}`,
        expect.objectContaining({
          method: 'PUT',
          body: expect.stringContaining('"thumbnailPhotoId":"2"'),
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('shows error message when API update fails', async () => {
      const user = userEvent.setup();
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

      render(
        <ItemDetailsPanel
          item={mockItem}
          onUpdateItem={mockApis.onUpdateItem}
          onRemovePhoto={mockApis.onRemovePhoto}
          onSetThumbnail={mockApis.onSetThumbnail}
          onClose={mockApis.onClose}
        />
      );

      const nameField = screen.getByDisplayValue('Test Item');
      await user.clear(nameField);
      await user.type(nameField, 'Updated Item');
      await user.tab();

      // Check for error message
      await waitFor(() => {
        expect(screen.getByText('Failed to update item')).toBeInTheDocument();
      });
    });

    it('maintains local state when API fails', async () => {
      const user = userEvent.setup();
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

      render(
        <ItemDetailsPanel
          item={mockItem}
          onUpdateItem={mockApis.onUpdateItem}
          onRemovePhoto={mockApis.onRemovePhoto}
          onSetThumbnail={mockApis.onSetThumbnail}
          onClose={mockApis.onClose}
        />
      );

      const valueField = screen.getByDisplayValue('100');
      await user.clear(valueField);
      await user.type(valueField, '200');
      await user.tab();

      // Field should still show updated value even though API failed
      expect(valueField).toHaveValue('200');
    });
  });

  describe('Validation', () => {
    it('prevents negative replacement values', async () => {
      const user = userEvent.setup();
      render(
        <ItemDetailsPanel
          item={mockItem}
          onUpdateItem={mockApis.onUpdateItem}
          onRemovePhoto={mockApis.onRemovePhoto}
          onSetThumbnail={mockApis.onSetThumbnail}
          onClose={mockApis.onClose}
        />
      );

      const valueField = screen.getByDisplayValue('100');
      await user.clear(valueField);
      await user.type(valueField, '-50');
      await user.tab();

      expect(mockApis.onUpdateItem).not.toHaveBeenCalled();
      expect(global.fetch).not.toHaveBeenCalled();
      expect(screen.getByText('Value must be positive')).toBeInTheDocument();
    });

    it('prevents empty required fields', async () => {
      const user = userEvent.setup();
      render(
        <ItemDetailsPanel
          item={mockItem}
          onUpdateItem={mockApis.onUpdateItem}
          onRemovePhoto={mockApis.onRemovePhoto}
          onSetThumbnail={mockApis.onSetThumbnail}
          onClose={mockApis.onClose}
        />
      );

      const nameField = screen.getByDisplayValue('Test Item');
      await user.clear(nameField);
      await user.tab();

      expect(mockApis.onUpdateItem).not.toHaveBeenCalled();
      expect(global.fetch).not.toHaveBeenCalled();
      expect(screen.getByText('Name is required')).toBeInTheDocument();
    });
  });
});
