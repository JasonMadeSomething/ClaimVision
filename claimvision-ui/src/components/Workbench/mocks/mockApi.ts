import { Item, Photo, Room } from "@/types/workbench";
import { mockItems, mockPhotos, mockRooms } from "./mockData";

// Simple Mock API class that simulates API calls
class WorkbenchApi {
  // Simulate API delay
  private async delay(ms: number = 100): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // API Methods
  async getPhotos(): Promise<Photo[]> {
    await this.delay();
    return [...mockPhotos];
  }

  async getItems(): Promise<Item[]> {
    await this.delay();
    return [...mockItems];
  }

  async getRooms(): Promise<Room[]> {
    await this.delay();
    return [...mockRooms];
  }

  async getItem(id: string): Promise<Item | null> {
    await this.delay();
    return mockItems.find(item => item.id === id) || null;
  }

  // Reset mock data (useful for tests)
  resetMockData(): void {
    // This is just a placeholder for test compatibility
    console.warn("Mock data reset");
  }
}

// Export a singleton instance
export const workbenchApi = new WorkbenchApi();
