import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WorkbenchLayout from '../WorkbenchLayout';
import { useSettingsStore } from '@/stores/settingsStore';

// Mock the settings store
jest.mock('@/stores/settingsStore', () => ({
  useSettingsStore: jest.fn(),
}));

describe('WorkbenchLayout', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks();
    
    // Mock the settings store with default values
    (useSettingsStore as jest.Mock).mockImplementation(() => ({
      autoOpenDetailPanel: false,
    }));
  });

  describe('Item Creation', () => {
    it('creates an empty item when clicking the New Item button', async () => {
      const user = userEvent.setup();
      render(<WorkbenchLayout />);

      // Find and click the New Item button
      const newItemButton = screen.getByText('New Item');
      await user.click(newItemButton);

      // Check that a new empty item was created
      const emptyItem = screen.getByText('Untitled Item');
      expect(emptyItem).toBeInTheDocument();

      // Details panel should not be open by default
      const detailsPanel = screen.queryByText('Item Details');
      expect(detailsPanel).not.toBeInTheDocument();
    });

    it('opens details panel when creating item if autoOpenDetailPanel is true', async () => {
      // Mock settings store with autoOpenDetailPanel = true
      (useSettingsStore as jest.Mock).mockImplementation(() => ({
        autoOpenDetailPanel: true,
      }));

      const user = userEvent.setup();
      render(<WorkbenchLayout />);

      // Create a new item
      const newItemButton = screen.getByText('New Item');
      await user.click(newItemButton);

      // Details panel should be open
      const detailsPanel = screen.getByText('Item Details');
      expect(detailsPanel).toBeInTheDocument();
    });

    it('creates an item from a single photo via context menu', async () => {
      const user = userEvent.setup();
      render(<WorkbenchLayout />);

      // Find a photo and right-click it
      const photo = screen.getByAltText('Sample photo');
      await user.pointer([
        { target: photo },
        { keys: '[MouseRight]', target: photo },
      ]);

      // Check that a new item was created with the photo
      const newItem = screen.getByText('New Item');
      expect(newItem).toBeInTheDocument();
      
      // The photo should now be part of an item
      const itemIndicator = screen.getByTitle('Part of an item');
      expect(itemIndicator).toBeInTheDocument();
    });
  });

  describe('Item Modification', () => {
    it('adds a photo to an existing item via drag and drop', async () => {
      const user = userEvent.setup();
      render(<WorkbenchLayout />);

      // Create an item first
      const newItemButton = screen.getByText('New Item');
      await user.click(newItemButton);

      // Find a photo and drag it to the item
      const photo = screen.getByAltText('Sample photo');
      const item = screen.getByText('Untitled Item');

      // Simulate drag and drop
      fireEvent.dragStart(photo);
      fireEvent.drop(item);

      // The photo should now be part of the item
      const itemIndicator = screen.getByTitle('Part of an item');
      expect(itemIndicator).toBeInTheDocument();
    });

    it('removes a photo from an item', async () => {
      const user = userEvent.setup();
      render(<WorkbenchLayout />);

      // Create an item with a photo
      const photo = screen.getByAltText('Sample photo');
      await user.pointer([
        { target: photo },
        { keys: '[MouseRight]', target: photo },
      ]);

      // Open the item details
      const item = screen.getByText('New Item');
      await user.click(item);

      // Find and click the remove photo button
      const removeButton = screen.getByLabelText('Remove photo');
      await user.click(removeButton);

      // The photo should no longer be part of an item
      const itemIndicator = screen.queryByTitle('Part of an item');
      expect(itemIndicator).not.toBeInTheDocument();
    });
  });

  describe('API Integration', () => {
    it('calls the API when creating a new item', async () => {
      const user = userEvent.setup();
      render(<WorkbenchLayout />);

      // Mock the API call
      const createItemSpy = jest.spyOn(global, 'fetch');

      // Create a new item
      const newItemButton = screen.getByText('New Item');
      await user.click(newItemButton);

      // Verify API was called with correct data
      expect(createItemSpy).toHaveBeenCalledWith('/api/items', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.stringContaining('"photoIds":[]'),
      });
    });

    it('calls the API when updating an item', async () => {
      const user = userEvent.setup();
      render(<WorkbenchLayout />);

      // Create an item and open its details
      const newItemButton = screen.getByText('New Item');
      await user.click(newItemButton);
      const item = screen.getByText('Untitled Item');
      await user.click(item);

      // Mock the API call
      const updateItemSpy = jest.spyOn(global, 'fetch');

      // Edit the item name
      const nameField = screen.getByPlaceholderText('Enter a name');
      await user.type(nameField, 'Test Item');
      await user.tab(); // Trigger blur event to save

      // Verify API was called with correct data
      expect(updateItemSpy).toHaveBeenCalledWith(expect.stringContaining('/api/items/'), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.stringContaining('"name":"Test Item"'),
      });
    });
  });
});
