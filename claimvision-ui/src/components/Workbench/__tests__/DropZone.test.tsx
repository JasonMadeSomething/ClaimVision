import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import DropZone from '../DropZone';

// Mock the useDrop hook
jest.mock('react-dnd', () => ({
  useDrop: () => [
    { isOver: false, canDrop: true },
    jest.fn()
  ]
}));

describe('DropZone Component', () => {
  const mockOnDrop = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders a horizontal drop zone correctly', () => {
    render(
      <DropZone
        index={0}
        acceptType="PHOTO"
        onDrop={mockOnDrop}
        orientation="horizontal"
      />
    );

    // The drop zone should be in the document
    const dropZone = screen.getByTestId('drop-zone');
    expect(dropZone).toBeInTheDocument();
    
    // It should have the transition class
    expect(dropZone).toHaveClass('transition-all');
  });

  it('renders a vertical drop zone correctly', () => {
    render(
      <DropZone
        index={0}
        acceptType="PHOTO"
        onDrop={mockOnDrop}
        orientation="vertical"
      />
    );

    // The drop zone should be in the document
    const dropZone = screen.getByTestId('drop-zone');
    expect(dropZone).toBeInTheDocument();
    
    // It should have the transition class
    expect(dropZone).toHaveClass('transition-all');
  });

  it('applies active styling when isActive is true', () => {
    render(
      <DropZone
        index={0}
        acceptType="PHOTO"
        onDrop={mockOnDrop}
        isActive={true}
      />
    );

    // The drop zone should have the active class
    const dropZone = screen.getByTestId('drop-zone');
    expect(dropZone).toHaveClass('bg-blue-100');
  });
});
