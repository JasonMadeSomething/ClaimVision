import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import PhotoGrid from '../PhotoGrid';
import { defaultPhotoGridProps } from './mocks/mockData';
import { workbenchApi } from './mocks/mockApi';

// Mock the react-dnd module
jest.mock('react-dnd', () => ({
  DndProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="dnd-provider">{children}</div>,
  useDrag: () => [{ isDragging: false }, jest.fn(), jest.fn()],
  useDrop: () => [{ isOver: false }, jest.fn(), jest.fn()],
}));

// Mock react-dnd-html5-backend
jest.mock('react-dnd-html5-backend', () => ({
  HTML5Backend: jest.fn(),
}));

// Mock headlessui components
jest.mock('@headlessui/react', () => {
  const MenuButton = ({ children }: { children: React.ReactNode }) => <button data-testid="menu-button">{children}</button>;
  const MenuItem = ({ children }: { children: React.ReactNode }) => {
    if (typeof children === 'function') {
      return children({ active: false });
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
    EllipsisVerticalIcon: function EllipsisVerticalIcon() {
      return <div data-testid="ellipsis-icon">Icon</div>;
    }
  };
});

describe('PhotoGrid', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    workbenchApi.resetMockData();
  });

  it('renders with empty props', () => {
    render(<PhotoGrid {...defaultPhotoGridProps} />);
    
    // Check that the component renders
    expect(screen.getByTestId('dnd-provider')).toBeInTheDocument();
  });
});
