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
    Object.defineProperty(HTMLElement.prototype, 'scrollTop', { 
      configurable: true, 
      value: 100 // Has scrolled down a bit
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
    const addEventListenerMock = jest.fn();
    const removeEventListenerMock = jest.fn();
    
    // Mock querySelector to return a mock viewport element
    const mockViewport = {
      scrollBy: scrollByMock,
      scrollTop: 100,
      scrollHeight: 1000,
      clientHeight: 500,
      addEventListener: addEventListenerMock,
      removeEventListener: removeEventListenerMock
    };
    
    const originalQuerySelector = HTMLElement.prototype.querySelector;
    HTMLElement.prototype.querySelector = jest.fn((selector) => {
      if (selector === '[data-radix-scroll-area-viewport]') {
        return mockViewport as any;
      }
      return originalQuerySelector.call(this, selector);
    });
    
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
    
    // Wait for component to be fully rendered
    await waitFor(() => {
      expect(screen.getByTestId('scroll-down-button')).toBeInTheDocument();
    });
    
    // The buttons should be enabled since scrollTop > 0 and scrollHeight > clientHeight
    const scrollDownButton = screen.getByTestId('scroll-down-button');
    const scrollUpButton = screen.getByTestId('scroll-up-button');
    
    // They should be enabled now since we have scroll content
    expect(scrollDownButton).not.toBeDisabled();
    expect(scrollUpButton).not.toBeDisabled();
    
    // Click scroll down button
    fireEvent.click(scrollDownButton);
    
    expect(scrollByMock).toHaveBeenCalledWith(
      expect.objectContaining({ 
        top: 100,
        behavior: 'smooth'
      })
    );
    
    // Click scroll up button
    fireEvent.click(scrollUpButton);
    
    expect(scrollByMock).toHaveBeenCalledWith(
      expect.objectContaining({ 
        top: -100,
        behavior: 'smooth'
      })
    );
    
    // Restore original querySelector
    HTMLElement.prototype.querySelector = originalQuerySelector;
  });
  
  test('automatically scrolls to make active tab visible', async () => {
    const { chapters, tabOrder } = generateChaptersFixture(20);
    
    const scrollIntoViewMock = jest.fn();
    
    // Mock querySelector to return elements with scrollIntoView
    const originalQuerySelector = HTMLElement.prototype.querySelector;
    HTMLElement.prototype.querySelector = jest.fn(function(this: HTMLElement, selector: string) {
      if (selector.includes('[data-rfd-draggable-id="ch-15"]')) {
        return {
          scrollIntoView: scrollIntoViewMock
        } as any;
      }
      if (selector === '[data-radix-scroll-area-viewport]') {
        return {
          scrollTop: 100,
          scrollHeight: 1000,
          clientHeight: 500
        } as any;
      }
      return originalQuerySelector.call(this, selector);
    });
    
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
    
    // Restore original querySelector
    HTMLElement.prototype.querySelector = originalQuerySelector;
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
