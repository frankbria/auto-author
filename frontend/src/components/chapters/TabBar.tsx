'use client';

import { useState, useRef } from 'react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChapterTab } from './ChapterTab';
import { TabOverflowMenu } from './TabOverflowMenu';
import { ChapterTabMetadata } from '@/types/chapter-tabs';

interface TabBarProps {
  chapters: ChapterTabMetadata[];
  activeChapterId: string | null;
  tabOrder: string[];
  onTabSelect: (chapterId: string) => void;
  onTabReorder: (sourceIndex: number, destinationIndex: number) => void;
  onTabClose: (chapterId: string) => void;
  orientation?: 'horizontal' | 'vertical';
}

export function TabBar({
  chapters,
  activeChapterId,
  tabOrder,
  onTabSelect,
  onTabReorder,
  onTabClose,
  orientation = 'vertical'
}: TabBarProps) {
  const [showOverflowMenu, setShowOverflowMenu] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return;
    onTabReorder(result.source.index, result.destination.index);
  };

  const orderedChapters = tabOrder
    .map(id => chapters.find(ch => ch.id === id))
    .filter(Boolean) as ChapterTabMetadata[];
  return (
    <div className={orientation === 'vertical' 
      ? "flex flex-col w-64 border-r bg-background h-full" 
      : "flex border-b bg-background"
    }>
      <ScrollArea 
        className={orientation === 'vertical' ? "flex-1 h-full" : "flex-1"} 
        ref={scrollAreaRef}
      >
        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable 
            droppableId="chapter-tabs" 
            direction={orientation === 'vertical' ? "vertical" : "horizontal"}
          >
            {(provided) => (
              <div
                {...provided.droppableProps}
                ref={provided.innerRef}
                className={orientation === 'vertical' ? "flex flex-col space-y-1 p-2" : "flex"}
              >
                {orderedChapters.map((chapter, index) => (
                  <Draggable
                    key={chapter.id}
                    draggableId={chapter.id}
                    index={index}
                  >
                    {(provided, snapshot) => (
                      <ChapterTab
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        {...provided.dragHandleProps}
                        chapter={chapter}
                        isActive={chapter.id === activeChapterId}
                        isDragging={snapshot.isDragging}
                        onSelect={() => onTabSelect(chapter.id)}
                        onClose={() => onTabClose(chapter.id)}
                        orientation={orientation}
                      />
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>
      </ScrollArea>

      {orientation === 'horizontal' && (
        <TabOverflowMenu
          chapters={orderedChapters}
          activeChapterId={activeChapterId}
          onTabSelect={onTabSelect}
          visible={showOverflowMenu}
          onVisibilityChange={setShowOverflowMenu}
        />
      )}
    </div>
  );
}
