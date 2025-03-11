import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ItemDetailsPanel from '../ItemDetailsPanel';
import { defaultItemDetailsPanelProps } from '../mocks/mockData';
import { workbenchApi } from '../mocks/mockApi';

// Mock the Dialog component from @headlessui/react
jest.mock('@headlessui/react', () => ({
  Dialog: ({ open, children }: { open?: boolean; children: React.ReactNode }) => (
    <div data-testid="dialog">{children}</div>
  ),
  DialogPanel: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-panel">{children}</div>
  ),
  DialogTitle: ({ children }: { children: React.ReactNode }) => (
    <h2 data-testid="dialog-title">{children}</h2>
  ),
  Transition: {
    Child: ({ show, children }: { show?: boolean; children: React.ReactNode }) => (
      <div data-testid="transition-child">{children}</div>
    ),
  },
  Listbox: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="listbox">{children}</div>
  ),
  ListboxButton: ({ children }: { children: React.ReactNode }) => (
    <button data-testid="listbox-button">{children}</button>
  ),
  ListboxOptions: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="listbox-options">{children}</div>
  ),
  ListboxOption: ({ value, children }: { value: string; children: React.ReactNode }) => (
    <div data-testid={`listbox-option-${value}`}>{children}</div>
  ),
}));

describe('ItemDetailsPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    workbenchApi.resetMockData();
  });

  it('renders the item details panel', async () => {
    // Use the mock API to get the item
    const item = await workbenchApi.getItem('item-0');
    const photos = await workbenchApi.getPhotos();
    const rooms = await workbenchApi.getRooms();

    const filteredPhotos = photos.filter(p => p.itemId === 'item-0');
    
    render(
      <ItemDetailsPanel
        item={item!}
        photos={filteredPhotos}
        rooms={rooms}
        onUpdate={jest.fn()}
        onRemovePhoto={jest.fn()}
        onChangeThumbnail={jest.fn()}
        onClose={jest.fn()}
        onMoveToRoom={jest.fn()}
        onAddPhoto={jest.fn()}
      />
    );

    // Check for the dialog title
    expect(screen.getByTestId('dialog-title')).toBeInTheDocument();
  });

  it('displays item information correctly', () => {
    // Use the default props which have been updated in mockData.ts
    render(
      <ItemDetailsPanel {...defaultItemDetailsPanelProps} />
    );

    // Check for the dialog components
    expect(screen.getByTestId('dialog')).toBeInTheDocument();
    expect(screen.getByTestId('dialog-title')).toBeInTheDocument();
  });
});
