# Question System Integration with Other Components

## Overview
The question system is designed to integrate seamlessly with other components of the writing application, including the chapter editor, progress tracking, content export, and user analytics. This document outlines these integrations and how they work together to create a cohesive writing experience.

## Core Integration Points

### Chapter Editor Integration

#### Real-time Chapter Context
The question system stays synchronized with chapter content changes:

```typescript
// frontend/src/hooks/useChapterSync.ts
export const useChapterSync = (chapterId: string) => {
  const [chapterData, setChapterData] = useState(null);
  
  // Listen for chapter content changes
  useEffect(() => {
    const handleChapterUpdate = (updatedChapter) => {
      // Trigger question relevance re-evaluation
      questionService.updateChapterContext(chapterId, {
        title: updatedChapter.title,
        content: updatedChapter.content,
        wordCount: updatedChapter.wordCount,
        lastModified: updatedChapter.lastModified
      });
    };

    chapterEventBus.on('chapter:updated', handleChapterUpdate);
    return () => chapterEventBus.off('chapter:updated', handleChapterUpdate);
  }, [chapterId]);
};
```

#### Smart Question Suggestions
Questions adapt based on chapter writing progress:

```python
# backend/app/services/adaptive_questions.py
class AdaptiveQuestionService:
    async def suggest_questions_for_writing_stage(
        self, 
        chapter_id: str, 
        writing_stage: str
    ) -> List[str]:
        """Suggest questions based on writing progress."""
        
        stages = {
            'outline': ['character', 'setting', 'plot'],
            'first_draft': ['character', 'dialogue', 'pacing'],
            'revision': ['theme', 'consistency', 'depth'],
            'editing': ['clarity', 'flow', 'impact']
        }
        
        focus_types = stages.get(writing_stage, ['general'])
        
        return await self.question_service.generate_questions(
            chapter_id=chapter_id,
            focus=focus_types,
            count=5,
            difficulty='medium'
        )
```

#### Content Insertion from Responses
Responses can be integrated into chapter content:

```typescript
// frontend/src/services/contentIntegration.ts
export class ContentIntegrationService {
  async insertResponseIntoChapter(
    chapterId: string,
    questionResponse: QuestionResponse,
    insertionPoint: 'beginning' | 'end' | 'cursor'
  ): Promise<void> {
    const chapter = await chapterAPI.getChapter(chapterId);
    const processedContent = this.processResponseForInsertion(questionResponse);
    
    let updatedContent: string;
    
    switch (insertionPoint) {
      case 'beginning':
        updatedContent = processedContent + '\n\n' + chapter.content;
        break;
      case 'end':
        updatedContent = chapter.content + '\n\n' + processedContent;
        break;
      case 'cursor':
        updatedContent = this.insertAtCursor(chapter.content, processedContent);
        break;
    }
    
    await chapterAPI.updateChapter(chapterId, { content: updatedContent });
  }

  private processResponseForInsertion(response: QuestionResponse): string {
    // Convert question response to chapter content format
    return `<!-- Question Response: ${response.question_id} -->
${response.response_text}
<!-- End Question Response -->`;
  }
}
```

### Table of Contents (TOC) Integration

#### Chapter Progress Visualization
Questions progress appears in the TOC:

```typescript
// frontend/src/components/toc/EnhancedTocItem.tsx
interface TocItemWithQuestions extends TocItem {
  questionProgress?: {
    total: number;
    completed: number;
    percentage: number;
  };
}

export const EnhancedTocItem: React.FC<{ item: TocItemWithQuestions }> = ({ item }) => {
  return (
    <div className="toc-item">
      <div className="toc-title">{item.title}</div>
      <div className="toc-indicators">
        <ChapterStatusIndicator status={item.status} />
        {item.questionProgress && (
          <QuestionProgressIndicator 
            completed={item.questionProgress.completed}
            total={item.questionProgress.total}
            percentage={item.questionProgress.percentage}
          />
        )}
      </div>
    </div>
  );
};
```

#### Bulk Question Operations
Generate questions for multiple chapters from TOC:

```typescript
// frontend/src/hooks/useBulkQuestionOperations.ts
export const useBulkQuestionOperations = () => {
  const generateQuestionsForChapters = async (
    chapterIds: string[],
    options: GenerateQuestionsRequest
  ) => {
    const results = await Promise.allSettled(
      chapterIds.map(chapterId => 
        questionAPI.generateQuestions(bookId, chapterId, options)
      )
    );
    
    return results.map((result, index) => ({
      chapterId: chapterIds[index],
      success: result.status === 'fulfilled',
      data: result.status === 'fulfilled' ? result.value : null,
      error: result.status === 'rejected' ? result.reason : null
    }));
  };

  return { generateQuestionsForChapters };
};
```

### Progress Tracking Integration

#### Cross-Component Progress Metrics
Questions contribute to overall book completion:

```python
# backend/app/services/progress_aggregation.py
class ProgressAggregationService:
    async def calculate_book_progress(self, book_id: str, user_id: str) -> Dict[str, Any]:
        """Calculate comprehensive book progress including questions."""
        
        chapters = await self.get_book_chapters(book_id)
        
        progress_data = {
            'chapters': {
                'total': len(chapters),
                'completed': 0,
                'word_count': 0
            },
            'questions': {
                'total': 0,
                'answered': 0,
                'completed': 0
            },
            'overall_percentage': 0
        }
        
        for chapter in chapters:
            # Chapter progress
            if chapter.status == 'completed':
                progress_data['chapters']['completed'] += 1
            progress_data['chapters']['word_count'] += chapter.word_count or 0
            
            # Question progress
            question_progress = await self.question_service.get_chapter_progress(
                book_id, chapter.id, user_id
            )
            progress_data['questions']['total'] += question_progress.total
            progress_data['questions']['answered'] += question_progress.answered
            progress_data['questions']['completed'] += question_progress.completed
        
        # Calculate weighted overall progress
        chapter_weight = 0.7
        question_weight = 0.3
        
        chapter_percentage = (
            progress_data['chapters']['completed'] / 
            max(progress_data['chapters']['total'], 1)
        )
        question_percentage = (
            progress_data['questions']['completed'] / 
            max(progress_data['questions']['total'], 1)
        )
        
        progress_data['overall_percentage'] = (
            chapter_percentage * chapter_weight + 
            question_percentage * question_weight
        ) * 100
        
        return progress_data
```

#### Progress Dashboard Integration
Questions appear in the main progress dashboard:

```typescript
// frontend/src/components/dashboard/ProgressOverview.tsx
export const ProgressOverview: React.FC<{ bookId: string }> = ({ bookId }) => {
  const { data: progress } = useQuery({
    queryKey: ['book-progress', bookId],
    queryFn: () => progressAPI.getBookProgress(bookId)
  });

  return (
    <div className="progress-overview">
      <div className="progress-grid">
        <ProgressCard
          title="Chapters"
          completed={progress?.chapters.completed}
          total={progress?.chapters.total}
          icon="📖"
        />
        <ProgressCard
          title="Questions"
          completed={progress?.questions.completed}
          total={progress?.questions.total}
          icon="❓"
        />
        <ProgressCard
          title="Word Count"
          value={progress?.chapters.word_count}
          target={progress?.target_word_count}
          icon="📝"
        />
      </div>
      
      <OverallProgressBar percentage={progress?.overall_percentage || 0} />
    </div>
  );
};
```

### Export System Integration

#### Question Responses in Export
Include question responses in book exports:

```python
# backend/app/services/export_service.py
class BookExportService:
    async def export_book_with_questions(
        self, 
        book_id: str, 
        user_id: str,
        format: str = 'docx',
        include_questions: bool = True
    ) -> bytes:
        """Export book with optional question responses."""
        
        book_data = await self.get_book_with_chapters(book_id)
        
        if include_questions:
            for chapter in book_data.chapters:
                questions = await self.question_service.get_questions_for_chapter(
                    book_id, chapter.id, user_id
                )
                chapter.questions = questions
        
        if format == 'docx':
            return await self.export_to_docx(book_data, include_questions)
        elif format == 'pdf':
            return await self.export_to_pdf(book_data, include_questions)
        elif format == 'json':
            return await self.export_to_json(book_data, include_questions)
        
    async def export_to_docx(self, book_data, include_questions: bool) -> bytes:
        """Export to DOCX format with question responses."""
        document = Document()
        
        # Add title page
        document.add_heading(book_data.title, 0)
        
        for chapter in book_data.chapters:
            # Add chapter
            document.add_heading(chapter.title, 1)
            document.add_paragraph(chapter.content)
            
            # Add question responses if requested
            if include_questions and hasattr(chapter, 'questions'):
                document.add_heading('Development Notes', 2)
                
                for question in chapter.questions:
                    if question.response:
                        # Add question
                        q_para = document.add_paragraph()
                        q_para.add_run('Q: ').bold = True
                        q_para.add_run(question.question_text)
                        
                        # Add response
                        r_para = document.add_paragraph()
                        r_para.add_run('A: ').bold = True
                        r_para.add_run(question.response.response_text)
                        
                        document.add_paragraph()  # Spacing
        
        # Save to bytes
        doc_buffer = BytesIO()
        document.save(doc_buffer)
        return doc_buffer.getvalue()
```

#### Export Configuration
Users can customize what question data to include:

```typescript
// frontend/src/components/export/ExportConfigurationModal.tsx
export const ExportConfigurationModal: React.FC = () => {
  const [config, setConfig] = useState({
    includeQuestions: true,
    questionTypes: ['character', 'plot', 'setting', 'theme'],
    responseStatus: ['completed'],
    includeRatings: false,
    includeMetadata: false
  });

  return (
    <Modal title="Export Configuration">
      <div className="export-config">
        <fieldset>
          <legend>Question Data</legend>
          
          <label>
            <input
              type="checkbox"
              checked={config.includeQuestions}
              onChange={(e) => setConfig(prev => ({
                ...prev,
                includeQuestions: e.target.checked
              }))}
            />
            Include question responses
          </label>
          
          {config.includeQuestions && (
            <>
              <div className="question-types">
                <label>Question Types:</label>
                {['character', 'plot', 'setting', 'theme', 'research'].map(type => (
                  <label key={type}>
                    <input
                      type="checkbox"
                      checked={config.questionTypes.includes(type)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setConfig(prev => ({
                            ...prev,
                            questionTypes: [...prev.questionTypes, type]
                          }));
                        } else {
                          setConfig(prev => ({
                            ...prev,
                            questionTypes: prev.questionTypes.filter(t => t !== type)
                          }));
                        }
                      }}
                    />
                    {type}
                  </label>
                ))}
              </div>
              
              <div className="response-status">
                <label>Response Status:</label>
                <select
                  multiple
                  value={config.responseStatus}
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, option => option.value);
                    setConfig(prev => ({ ...prev, responseStatus: values }));
                  }}
                >
                  <option value="draft">Draft</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
            </>
          )}
        </fieldset>
      </div>
    </Modal>
  );
};
```

### Search and Discovery Integration

#### Question-Based Search
Search through question responses:

```python
# backend/app/services/search_service.py
class SearchService:
    async def search_questions_and_responses(
        self, 
        book_id: str,
        user_id: str,
        query: str,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search through questions and responses."""
        
        search_query = """
        SELECT 
            q.id as question_id,
            q.question_text,
            q.question_type,
            q.difficulty,
            qr.response_text,
            qr.status as response_status,
            ch.title as chapter_title,
            ch.id as chapter_id,
            ts_rank(
                to_tsvector('english', q.question_text || ' ' || COALESCE(qr.response_text, '')),
                plainto_tsquery('english', $1)
            ) as relevance_score
        FROM questions q
        LEFT JOIN question_responses qr ON q.id = qr.question_id AND qr.user_id = $2
        JOIN chapters ch ON q.chapter_id = ch.id
        WHERE q.book_id = $3
            AND to_tsvector('english', q.question_text || ' ' || COALESCE(qr.response_text, '')) 
                @@ plainto_tsquery('english', $1)
        """
        
        # Add filters
        params = [query, user_id, book_id]
        param_count = 4
        
        if filters:
            if 'question_type' in filters:
                search_query += f" AND q.question_type = ANY(${param_count})"
                params.append(filters['question_type'])
                param_count += 1
                
            if 'difficulty' in filters:
                search_query += f" AND q.difficulty = ANY(${param_count})"
                params.append(filters['difficulty'])
                param_count += 1
                
            if 'response_status' in filters:
                search_query += f" AND qr.status = ANY(${param_count})"
                params.append(filters['response_status'])
                param_count += 1
        
        search_query += " ORDER BY relevance_score DESC, q.created_at DESC LIMIT 50"
        
        return await self.database.fetch_all(search_query, params)
```

#### Smart Content Discovery
Suggest related questions based on content:

```typescript
// frontend/src/services/contentDiscovery.ts
export class ContentDiscoveryService {
  async findRelatedQuestions(
    bookId: string,
    chapterId: string,
    keywords: string[]
  ): Promise<Question[]> {
    const response = await fetch(`/api/v1/books/${bookId}/chapters/${chapterId}/related-questions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keywords })
    });
    
    return response.json();
  }

  async suggestQuestionsBasedOnContent(
    chapterContent: string
  ): Promise<string[]> {
    // Extract key themes and entities from content
    const analysis = await this.analyzeContent(chapterContent);
    
    const suggestions = [];
    
    // Character-based suggestions
    if (analysis.characters.length > 0) {
      suggestions.push(
        `How do ${analysis.characters.join(' and ')} interact in this chapter?`,
        `What motivates ${analysis.characters[0]}'s actions here?`
      );
    }
    
    // Plot-based suggestions
    if (analysis.events.length > 0) {
      suggestions.push(
        `What are the consequences of ${analysis.events[0]}?`,
        `How does this chapter advance the main plot?`
      );
    }
    
    // Theme-based suggestions
    if (analysis.themes.length > 0) {
      suggestions.push(
        `How does this chapter explore the theme of ${analysis.themes[0]}?`
      );
    }
    
    return suggestions;
  }
}
```

### Analytics Integration

#### Question Effectiveness Tracking
Track how questions contribute to writing productivity:

```python
# backend/app/services/analytics_service.py
class QuestionAnalyticsService:
    async def track_question_effectiveness(
        self,
        user_id: str,
        book_id: str,
        chapter_id: str,
        question_id: str,
        metrics: Dict[str, Any]
    ):
        """Track question effectiveness metrics."""
        
        await self.analytics_db.insert_event({
            'event_type': 'question_interaction',
            'user_id': user_id,
            'book_id': book_id,
            'chapter_id': chapter_id,
            'question_id': question_id,
            'timestamp': datetime.utcnow(),
            'metrics': {
                'time_to_respond': metrics.get('time_to_respond'),
                'response_length': metrics.get('response_length'),
                'edit_count': metrics.get('edit_count'),
                'final_rating': metrics.get('final_rating'),
                'led_to_chapter_edits': metrics.get('led_to_chapter_edits', False),
                'response_reused': metrics.get('response_reused', False)
            }
        })
    
    async def generate_question_insights(
        self,
        user_id: str,
        time_period: str = '30d'
    ) -> Dict[str, Any]:
        """Generate insights about question usage patterns."""
        
        insights = {
            'most_effective_types': await self.get_most_effective_question_types(user_id, time_period),
            'optimal_difficulty': await self.get_optimal_difficulty_level(user_id, time_period),
            'response_patterns': await self.analyze_response_patterns(user_id, time_period),
            'productivity_correlation': await self.calculate_productivity_correlation(user_id, time_period)
        }
        
        return insights
```

#### User Behavior Analytics
Understand how users interact with questions:

```typescript
// frontend/src/hooks/useQuestionAnalytics.ts
export const useQuestionAnalytics = () => {
  const trackQuestionView = (questionId: string) => {
    analytics.track('question_viewed', {
      question_id: questionId,
      timestamp: new Date().toISOString()
    });
  };

  const trackResponseStart = (questionId: string) => {
    analytics.track('response_started', {
      question_id: questionId,
      timestamp: new Date().toISOString()
    });
  };

  const trackResponseComplete = (
    questionId: string,
    responseLength: number,
    timeSpent: number
  ) => {
    analytics.track('response_completed', {
      question_id: questionId,
      response_length: responseLength,
      time_spent: timeSpent,
      timestamp: new Date().toISOString()
    });
  };

  const trackQuestionRating = (questionId: string, rating: number) => {
    analytics.track('question_rated', {
      question_id: questionId,
      rating: rating,
      timestamp: new Date().toISOString()
    });
  };

  return {
    trackQuestionView,
    trackResponseStart,
    trackResponseComplete,
    trackQuestionRating
  };
};
```

### Notification System Integration

#### Question-Related Notifications
Integrate with the app's notification system:

```python
# backend/app/services/notification_service.py
class QuestionNotificationService:
    async def send_question_reminders(self):
        """Send reminders for unanswered questions."""
        
        # Find users with unanswered questions
        users_with_pending = await self.get_users_with_pending_questions()
        
        for user_data in users_with_pending:
            if user_data['notification_preferences'].get('question_reminders', True):
                await self.send_notification(
                    user_id=user_data['user_id'],
                    type='question_reminder',
                    title='Unanswered Questions',
                    message=f"You have {user_data['pending_count']} unanswered questions waiting",
                    action_url=f"/books/{user_data['book_id']}/questions"
                )
    
    async def notify_quality_improvement(self, user_id: str, book_id: str):
        """Notify when question quality can be improved."""
        
        recent_ratings = await self.get_recent_question_ratings(user_id, book_id)
        avg_rating = sum(r['rating'] for r in recent_ratings) / len(recent_ratings)
        
        if avg_rating < 3.0 and len(recent_ratings) >= 5:
            await self.send_notification(
                user_id=user_id,
                type='quality_suggestion',
                title='Question Quality Notice',
                message='Your recent question ratings suggest we can generate better questions. Try regenerating with different settings.',
                action_url=f"/books/{book_id}/questions/regenerate"
            )
```

#### Progress Milestone Notifications
Celebrate question completion milestones:

```typescript
// frontend/src/services/milestoneService.ts
export class MilestoneService {
  async checkQuestionMilestones(
    bookId: string,
    chapterId: string,
    progress: QuestionProgressResponse
  ) {
    const milestones = [
      { threshold: 0.25, message: "Great start! You've answered 25% of your questions." },
      { threshold: 0.5, message: "Halfway there! 50% of questions completed." },
      { threshold: 0.75, message: "Almost done! 75% of questions answered." },
      { threshold: 1.0, message: "Excellent! All questions completed for this chapter." }
    ];

    for (const milestone of milestones) {
      if (progress.progress >= milestone.threshold && 
          !this.hasMilestoneBeenShown(chapterId, milestone.threshold)) {
        
        await this.showMilestoneNotification({
          title: 'Question Progress Milestone',
          message: milestone.message,
          type: 'success',
          bookId,
          chapterId
        });

        this.markMilestoneAsShown(chapterId, milestone.threshold);
      }
    }
  }
}
```

### Collaboration Integration

#### Shared Question Workspaces
Support collaborative question answering:

```python
# backend/app/services/collaboration_service.py
class QuestionCollaborationService:
    async def share_questions_with_collaborator(
        self,
        book_id: str,
        chapter_id: str,
        collaborator_id: str,
        question_ids: List[str],
        permissions: List[str]
    ):
        """Share specific questions with a collaborator."""
        
        for question_id in question_ids:
            await self.create_question_share(
                question_id=question_id,
                shared_with=collaborator_id,
                permissions=permissions,  # ['view', 'respond', 'comment']
                shared_by=self.current_user_id,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
    
    async def get_collaborative_responses(
        self,
        question_id: str
    ) -> List[Dict[str, Any]]:
        """Get all responses to a question from different collaborators."""
        
        return await self.database.fetch_all("""
            SELECT 
                qr.*,
                u.name as author_name,
                u.id as author_id
            FROM question_responses qr
            JOIN users u ON qr.user_id = u.id
            WHERE qr.question_id = $1
            ORDER BY qr.created_at DESC
        """, [question_id])
```

#### Real-time Collaboration Features
Live updates for collaborative question work:

```typescript
// frontend/src/hooks/useCollaborativeQuestions.ts
export const useCollaborativeQuestions = (questionId: string) => {
  const [collaborators, setCollaborators] = useState([]);
  const [liveUpdates, setLiveUpdates] = useState([]);

  useEffect(() => {
    // WebSocket connection for real-time updates
    const ws = new WebSocket(`/ws/questions/${questionId}/collaborate`);
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      
      switch (update.type) {
        case 'user_joined':
          setCollaborators(prev => [...prev, update.user]);
          break;
        case 'response_updated':
          setLiveUpdates(prev => [...prev, {
            type: 'response_update',
            user: update.user,
            timestamp: update.timestamp,
            message: `${update.user.name} updated their response`
          }]);
          break;
        case 'user_typing':
          // Show typing indicator
          break;
      }
    };

    return () => ws.close();
  }, [questionId]);

  return { collaborators, liveUpdates };
};
```

## Integration Architecture

### Event-Driven Communication
Components communicate through a centralized event system:

```typescript
// frontend/src/lib/eventBus.ts
export class EventBus {
  private events: Map<string, Function[]> = new Map();

  on(event: string, callback: Function) {
    if (!this.events.has(event)) {
      this.events.set(event, []);
    }
    this.events.get(event)!.push(callback);
  }

  emit(event: string, data?: any) {
    const callbacks = this.events.get(event) || [];
    callbacks.forEach(callback => callback(data));
  }

  off(event: string, callback: Function) {
    const callbacks = this.events.get(event) || [];
    const index = callbacks.indexOf(callback);
    if (index > -1) {
      callbacks.splice(index, 1);
    }
  }
}

// Event types for question system integration
export const QUESTION_EVENTS = {
  QUESTION_GENERATED: 'question:generated',
  RESPONSE_SAVED: 'question:response_saved',
  QUESTION_RATED: 'question:rated',
  PROGRESS_UPDATED: 'question:progress_updated',
  CHAPTER_CONTEXT_CHANGED: 'chapter:context_changed'
} as const;
```

### API Integration Patterns
Consistent patterns for API integration:

```typescript
// frontend/src/lib/api/integrationAPI.ts
export class IntegrationAPI {
  // Question-Chapter integration
  async updateChapterFromQuestions(
    chapterId: string,
    questionIds: string[]
  ): Promise<void> {
    return this.post(`/chapters/${chapterId}/integrate-questions`, {
      question_ids: questionIds
    });
  }

  // Question-Progress integration
  async getUnifiedProgress(bookId: string): Promise<UnifiedProgress> {
    return this.get(`/books/${bookId}/unified-progress`);
  }

  // Question-Export integration
  async exportWithQuestions(
    bookId: string,
    format: string,
    options: ExportOptions
  ): Promise<Blob> {
    return this.post(`/books/${bookId}/export`, {
      format,
      include_questions: options.includeQuestions,
      question_filters: options.questionFilters
    }, { responseType: 'blob' });
  }

  // Question-Search integration
  async searchAcrossQuestions(
    bookId: string,
    query: string,
    filters: SearchFilters
  ): Promise<SearchResults> {
    return this.post(`/books/${bookId}/search/questions`, {
      query,
      filters
    });
  }
}
```

## Best Practices for Integration

### Data Consistency
- Use database transactions for multi-component updates
- Implement eventual consistency for non-critical integrations
- Maintain referential integrity across components

### Performance Optimization
- Cache frequently accessed integration data
- Use pagination for large cross-component queries
- Implement lazy loading for optional integration features

### Error Handling
- Graceful degradation when integrated components are unavailable
- Clear error messages that indicate which integration failed
- Fallback mechanisms for critical integration points

### Testing Integration Points
- Integration tests for all major component interactions
- Mock external dependencies in component tests
- End-to-end tests for complete user workflows

---

*For implementation details, see [Developer Guide for Question System](developer-guide-question-system.md) and [API Documentation](api-question-endpoints.md).*
