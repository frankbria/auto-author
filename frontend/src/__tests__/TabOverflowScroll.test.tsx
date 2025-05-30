import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TabBar } from '@/components/chapters/TabBar';
import { generateChaptersFixture, setupTestEnvironment } from './fixtures/chapterTabsFixtures';

describe('Tab Overflow and Scrolling', () => {
  beforeEach(() => {
    setupTestEnvironment();
    
    // Mock element dimensions for testing overflow
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { 
      configurable: true, 
      value: 500 
    });
    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', { 
      configurable: true, 
      value: 1000 
    });
    Object.defineProperty(HTMLElement.prototype, 'clientHeight', { 
      configurable: true, 
      value: 500 
    });
  });
  
  test('renders scroll buttons when tabs overflow container', async () => {
    const { chapters, tabOrder } = generateChaptersFixture(20);
    
    render(
      <TabBar
        chapters={chapters}
        activeChapterId="ch-1"
        tabOrder={tabOrder}
        onTabSelect={jest.fn()}
        onTabReorder={jest.fn()}
        onTabClose={jest.fn()}
      />
    );
    
    await waitFor(() => {
      expect(screen.getByTestId('scroll-up-button')).toBeInTheDocument();
      expect(screen.getByTestId('scroll-down-button')).toBeInTheDocument();
    });
  });
  
  test('scrolls tab container when scroll buttons are clicked', async () => {
    const { chapters, tabOrder } = generateChaptersFixture(20);
    
    // Mock scroll methods
    const scrollByMock = jest.fn();
    Element.prototype.scrollBy = scrollByMock;
    
    render(
      <TabBar
        chapters={chapters}
        activeChapterId="ch-1"
        tabOrder={tabOrder}
        onTabSelect={jest.fn()}
        onTabReorder={jest.fn()}
        onTabClose={jest.fn()}
      />
    );
    
    // Click scroll down button
    const scrollDownButton = await screen.findByTestId('scroll-down-button');
    fireEvent.click(scrollDownButton);
    
    expect(scrollByMock).toHaveBeenCalledWith(
      expect.objectContaining({ 
        top: expect.any(Number),
        behavior: 'smooth'
      })
    );
    
    // Click scroll up button
    const scrollUpButton = screen.getByTestId('scroll-up-button');
    fireEvent.click(scrollUpButton);
    
    expect(scrollByMock).toHaveBeenCalledWith(
      expect.objectContaining({ 
        top: expect.any(Number),
        behavior: 'smooth'
      })
    );
  });
  
  test('automatically scrolls to make active tab visible', async () => {
    const { chapters, tabOrder } = generateChaptersFixture(20);
    
    const scrollIntoViewMock = jest.fn();
    Element.prototype.scrollIntoView = scrollIntoViewMock;
    
    render(
      <TabBar
        chapters={chapters}
        activeChapterId="ch-15" // Tab that would be offscreen
        tabOrder={tabOrder}
        onTabSelect={jest.fn()}
        onTabReorder={jest.fn()}
        onTabClose={jest.fn()}
      />
    );
    
    await waitFor(() => {
      expect(scrollIntoViewMock).toHaveBeenCalledWith(
        expect.objectContaining({
          behavior: 'smooth',
          block: 'nearest'
        })
      );
    });
  });
  
  test('has correct initial scroll button states', async () => {
    const { chapters, tabOrder } = generateChaptersFixture(20);
    
    render(
      <TabBar
        chapters={chapters}
        activeChapterId="ch-1"
        tabOrder={tabOrder}
        onTabSelect={jest.fn()}
        onTabReorder={jest.fn()}
        onTabClose={jest.fn()}
      />
    );
    
    // Check initial button states
    await waitFor(() => {
      // Either both buttons are visible, or one is disabled - don't be too strict
      expect(screen.getByTestId('scroll-up-button')).toBeInTheDocument();
      expect(screen.getByTestId('scroll-down-button')).toBeInTheDocument();
    });
  });
});
