# ClaimVision - Modern Disaster Claims Organization Interface

ClaimVision is a modern, intuitive disaster claims organization interface designed to help users sort and categorize photos of damaged property effortlessly. The UI is fluid, intuitive, and visually clean—more like a productivity tool than an insurance app.

## Features

- **Workbench Interface**: A primary workspace where users can freely organize their uploaded photos
- **Drag-and-Drop Functionality**: Create items by stacking related photos together
- **Room Organization**: Assign items to rooms for better organization and reduced clutter
- **Hybrid Search Modes**: 
  - "Find" mode removes non-matching photos from view
  - "Highlight" mode keeps everything visible but fades out non-matching items
- **AI Photo Labeling**: Automatically label and filter photos to help users quickly find related items
- **Item Details Panel**: View and edit item information, including associated photos, descriptions, and replacement values
- **Cached Photo Positioning**: Users don't lose their layout when switching views or filters

## Getting Started

First, run the development server:

```powershell
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Project Structure

- `/src/components/Workbench`: Contains all the components for the workbench interface
  - `WorkbenchLayout.tsx`: Main layout component for the workbench
  - `PhotoGrid.tsx`: Displays and organizes photos with drag-and-drop functionality
  - `ItemDetailsPanel.tsx`: Panel for viewing and editing item details
  - `RoomSelector.tsx`: Component for selecting and managing rooms
  - `SearchBar.tsx`: Search and filter functionality for photos
  - `WorkbenchHeader.tsx`: Header component for the workbench

- `/src/types`: Contains TypeScript interfaces for the application
  - `workbench.ts`: Types for photos, items, rooms, and search modes

## Backend Integration

The UI integrates with the ClaimVision backend API for:
- Photo uploads and management
- AI-powered label generation
- Item and room organization
- User authentication

## Technologies Used

- Next.js 15
- React 19
- TailwindCSS
- React DnD (for drag-and-drop functionality)
- AWS Amplify (for authentication and API integration)

## Design Philosophy

ClaimVision's design prioritizes user experience, reducing manual input by leveraging AI to label and filter photos. The interface feels more like productivity software such as Notion or Trello, but optimized for visual organization. It avoids rigid forms, excessive modals, and enterprise-style UI clutter.
