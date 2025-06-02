# Developer Guide: Extending Question Functionality

## Overview
This guide provides comprehensive information for developers working on the question generation and management system, including architecture, extension points, and implementation patterns.

## System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   AI Service    │
│   Components    │◄──►│   API Layer     │◄──►│   Integration   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   State Mgmt    │    │   Service Layer │    │   External AI   │
│   (React Query) │    │   Business Logic│    │   APIs (OpenAI) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Local Storage │    │   Database      │
│   Caching       │    │   PostgreSQL    │
└─────────────────┘    └─────────────────┘
```

### Core Components

#### Backend Services
- **QuestionGenerationService**: Main orchestrator for question creation
- **QuestionQualityService**: Quality scoring and filtering algorithms  
- **QuestionFeedbackService**: User feedback processing and learning
- **AIService**: Integration with external AI providers
- **GenreQuestionTemplates**: Genre-specific question templates
- **UserLevelAdaptation**: Adaptive difficulty and personalization

#### Frontend Components
- **QuestionContainer**: Main wrapper component
- **QuestionGenerator**: Generation interface and controls
- **QuestionDisplay**: Individual question rendering
- **QuestionProgress**: Progress tracking and visualization
- **QuestionNavigation**: Navigation between questions

## Extension Points

### Adding New Question Types

#### 1. Update Schema Enums
```python
# backend/app/schemas/book.py
class QuestionType(str, Enum):
    CHARACTER = "character"
    PLOT = "plot"
    SETTING = "setting"
    THEME = "theme"
    RESEARCH = "research"
    DIALOGUE = "dialogue"  # New type
    PACING = "pacing"      # New type
```

#### 2. Update Frontend Types
```typescript
// frontend/src/types/chapter-questions.ts
export enum QuestionType {
  CHARACTER = "character",
  PLOT = "plot",
  SETTING = "setting",
  THEME = "theme",
  RESEARCH = "research",
  DIALOGUE = "dialogue",  // New type
  PACING = "pacing"       // New type
}
```

#### 3. Add Template Questions
```python
# backend/app/services/genre_question_templates.py
class GenreQuestionTemplates:
    def __init__(self):
        self.templates = {
            # ... existing templates ...
            QuestionType.DIALOGUE: {
                "fiction": [
                    "How does dialogue reveal character personality in this chapter?",
                    "What subtext exists in the conversations between characters?",
                    "How does dialogue drive the plot forward?"
                ],
                "general": [
                    "What key conversations take place in this chapter?",
                    "How do characters communicate their intentions?"
                ]
            }
        }
```

#### 4. Update Quality Scoring
```python
# backend/app/services/question_quality_service.py
def _get_type_specific_criteria(self, question_type: QuestionType) -> Dict[str, float]:
    """Get quality criteria weights specific to question type."""
    criteria = {
        QuestionType.DIALOGUE: {
            'dialogue_keywords': 0.3,
            'conversation_focus': 0.25,
            'character_interaction': 0.2
        }
        # ... other types
    }
    return criteria.get(question_type, self.default_criteria)
```

### Creating Custom Question Generators

#### 1. Implement Generator Interface
```python
# backend/app/services/custom_generators/base_generator.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.schemas.book import QuestionCreate

class QuestionGeneratorInterface(ABC):
    @abstractmethod
    async def generate_questions(
        self,
        chapter_context: Dict[str, Any],
        count: int,
        **kwargs
    ) -> List[QuestionCreate]:
        """Generate questions for a chapter."""
        pass

    @abstractmethod
    def get_supported_genres(self) -> List[str]:
        """Return list of supported genres."""
        pass

    @abstractmethod
    def get_generator_name(self) -> str:
        """Return unique generator name."""
        pass
```

#### 2. Implement Custom Generator
```python
# backend/app/services/custom_generators/poetry_generator.py
class PoetryQuestionGenerator(QuestionGeneratorInterface):
    async def generate_questions(
        self,
        chapter_context: Dict[str, Any],
        count: int,
        **kwargs
    ) -> List[QuestionCreate]:
        """Generate poetry-specific questions."""
        questions = []
        
        templates = [
            "What poetic devices are used in this section?",
            "How does the rhythm contribute to the meaning?",
            "What imagery stands out in this passage?",
            "How does the structure support the theme?"
        ]
        
        for i, template in enumerate(templates[:count]):
            question = QuestionCreate(
                question_text=template,
                question_type=QuestionType.THEME,
                difficulty=QuestionDifficulty.MEDIUM,
                category="poetry analysis",
                order=i + 1,
                metadata=QuestionMetadata(
                    suggested_response_length="100-200 words",
                    help_text="Consider literary devices and their effects",
                    examples=["Metaphor usage", "Alliteration impact"]
                )
            )
            questions.append(question)
        
        return questions

    def get_supported_genres(self) -> List[str]:
        return ["poetry", "verse", "literary fiction"]

    def get_generator_name(self) -> str:
        return "poetry_specialist"
```

#### 3. Register Generator
```python
# backend/app/services/question_generation_service.py
class QuestionGenerationService:
    def __init__(self):
        self.custom_generators = {
            "poetry": PoetryQuestionGenerator(),
            "technical": TechnicalQuestionGenerator(),
            "children": ChildrensBookGenerator()
        }

    async def generate_chapter_questions(self, **kwargs):
        # Check if custom generator exists for genre
        book_genre = kwargs.get('book_metadata', {}).get('genre', '').lower()
        
        if book_genre in self.custom_generators:
            generator = self.custom_generators[book_genre]
            return await generator.generate_questions(**kwargs)
        
        # Fall back to default generation
        return await self._default_generation(**kwargs)
```

### Adding Quality Metrics

#### 1. Define New Metric
```python
# backend/app/services/quality_metrics/readability_metric.py
class ReadabilityMetric:
    def calculate_score(self, question_text: str) -> float:
        """Calculate readability score (0.0 - 1.0)."""
        words = question_text.split()
        avg_word_length = sum(len(word) for word in words) / len(words)
        sentence_count = question_text.count('?') + question_text.count('.') + 1
        
        # Simple readability calculation
        complexity = (avg_word_length * 0.6) + (len(words) / sentence_count * 0.4)
        
        # Normalize to 0-1 scale (optimal complexity around 4-6)
        if complexity < 4:
            return complexity / 4  # Too simple
        elif complexity > 8:
            return max(0, 1 - (complexity - 8) / 4)  # Too complex
        else:
            return 1.0  # Optimal range
```

#### 2. Integrate into Quality Service
```python
# backend/app/services/question_quality_service.py
class QuestionQualityService:
    def __init__(self):
        self.metrics = {
            'readability': ReadabilityMetric(),
            'relevance': RelevanceMetric(),
            'specificity': SpecificityMetric()
        }

    def score_question_quality(self, question: Dict[str, Any], chapter_context: Dict[str, Any]) -> float:
        scores = {}
        
        for metric_name, metric in self.metrics.items():
            scores[metric_name] = metric.calculate_score(
                question.get('question_text', ''),
                chapter_context
            )
        
        # Weighted combination
        final_score = (
            scores['readability'] * 0.3 +
            scores['relevance'] * 0.4 +
            scores['specificity'] * 0.3
        )
        
        return final_score
```

### Implementing Response Processors

#### 1. Create Response Processor
```python
# backend/app/services/response_processors/summary_processor.py
class ResponseSummaryProcessor:
    async def process_response(
        self,
        response_text: str,
        question_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process response and extract insights."""
        
        word_count = len(response_text.split())
        sentiment = self._analyze_sentiment(response_text)
        key_themes = self._extract_themes(response_text)
        readability = self._calculate_readability(response_text)
        
        return {
            'word_count': word_count,
            'sentiment_score': sentiment,
            'key_themes': key_themes,
            'readability_score': readability,
            'completion_estimate': self._estimate_completion(response_text, question_context)
        }

    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of response (-1.0 to 1.0)."""
        # Implementation using sentiment analysis library
        pass

    def _extract_themes(self, text: str) -> List[str]:
        """Extract key themes from response."""
        # Implementation using NLP techniques
        pass
```

#### 2. Register Processor
```python
# backend/app/services/question_generation_service.py
async def save_question_response(
    self,
    question_id: str,
    response_data: QuestionResponseCreate,
    user_id: str
) -> Dict[str, Any]:
    """Save response with processing."""
    
    # Save basic response
    response = await db_save_question_response(question_id, response_data, user_id)
    
    # Process response for insights
    processor = ResponseSummaryProcessor()
    insights = await processor.process_response(
        response_data.response_text,
        {'question_id': question_id}
    )
    
    # Update response metadata
    response['metadata']['insights'] = insights
    
    return response
```

## Frontend Extension Patterns

### Creating Custom Question Components

#### 1. Base Question Component
```typescript
// frontend/src/components/questions/base/BaseQuestion.tsx
import React from 'react';
import { Question, QuestionResponse } from '@/types/chapter-questions';

interface BaseQuestionProps {
  question: Question;
  response?: QuestionResponse;
  onResponseChange: (response: string) => void;
  onSave: () => void;
  className?: string;
}

export const BaseQuestion: React.FC<BaseQuestionProps> = ({
  question,
  response,
  onResponseChange,
  onSave,
  className
}) => {
  return (
    <div className={`question-container ${className}`}>
      <div className="question-header">
        <h3>{question.question_text}</h3>
        <div className="question-meta">
          <span className="type">{question.question_type}</span>
          <span className="difficulty">{question.difficulty}</span>
        </div>
      </div>
      
      <div className="question-help">
        {question.metadata.help_text && (
          <p className="help-text">{question.metadata.help_text}</p>
        )}
      </div>
      
      <div className="response-area">
        <textarea
          value={response?.response_text || ''}
          onChange={(e) => onResponseChange(e.target.value)}
          placeholder="Enter your response..."
          className="response-input"
        />
      </div>
      
      <div className="question-actions">
        <button onClick={onSave} className="save-btn">
          Save Response
        </button>
      </div>
    </div>
  );
};
```

#### 2. Specialized Question Components
```typescript
// frontend/src/components/questions/types/CharacterQuestion.tsx
export const CharacterQuestion: React.FC<BaseQuestionProps> = (props) => {
  const { question } = props;
  
  return (
    <BaseQuestion {...props}>
      <div className="character-specific-tools">
        <div className="character-tracker">
          <h4>Character Notes</h4>
          <ul>
            {/* Character-specific helper tools */}
          </ul>
        </div>
        
        <div className="relationship-mapper">
          {/* Character relationship tools */}
        </div>
      </div>
    </BaseQuestion>
  );
};
```

#### 3. Question Component Factory
```typescript
// frontend/src/components/questions/QuestionFactory.tsx
import { QuestionType } from '@/types/chapter-questions';
import { BaseQuestion } from './base/BaseQuestion';
import { CharacterQuestion } from './types/CharacterQuestion';
import { PlotQuestion } from './types/PlotQuestion';
import { ThemeQuestion } from './types/ThemeQuestion';

const questionComponents = {
  [QuestionType.CHARACTER]: CharacterQuestion,
  [QuestionType.PLOT]: PlotQuestion,
  [QuestionType.THEME]: ThemeQuestion,
  // Fallback to base component
  default: BaseQuestion
};

export const QuestionFactory: React.FC<QuestionProps> = (props) => {
  const { question } = props;
  const Component = questionComponents[question.question_type] || questionComponents.default;
  
  return <Component {...props} />;
};
```

### State Management Patterns

#### 1. Question State Hook
```typescript
// frontend/src/hooks/useQuestionState.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { questionAPI } from '@/lib/api/questions';

export const useQuestionState = (bookId: string, chapterId: string) => {
  const queryClient = useQueryClient();
  
  const {
    data: questions,
    isLoading,
    error
  } = useQuery({
    queryKey: ['questions', bookId, chapterId],
    queryFn: () => questionAPI.getQuestions(bookId, chapterId)
  });

  const generateMutation = useMutation({
    mutationFn: (params: GenerateQuestionsRequest) =>
      questionAPI.generateQuestions(bookId, chapterId, params),
    onSuccess: () => {
      queryClient.invalidateQueries(['questions', bookId, chapterId]);
    }
  });

  const saveResponseMutation = useMutation({
    mutationFn: ({ questionId, response }: { questionId: string; response: QuestionResponseRequest }) =>
      questionAPI.saveResponse(bookId, chapterId, questionId, response),
    onSuccess: () => {
      queryClient.invalidateQueries(['questions', bookId, chapterId]);
    }
  });

  return {
    questions,
    isLoading,
    error,
    generateQuestions: generateMutation.mutate,
    saveResponse: saveResponseMutation.mutate,
    isGenerating: generateMutation.isPending,
    isSaving: saveResponseMutation.isPending
  };
};
```

#### 2. Response Auto-Save Hook
```typescript
// frontend/src/hooks/useAutoSave.ts
import { useEffect, useCallback, useRef } from 'react';
import { debounce } from 'lodash';

export const useAutoSave = (
  content: string,
  onSave: (content: string) => void,
  delay: number = 30000 // 30 seconds
) => {
  const lastSavedContent = useRef<string>('');
  const timeoutRef = useRef<NodeJS.Timeout>();

  const debouncedSave = useCallback(
    debounce((content: string) => {
      if (content !== lastSavedContent.current && content.trim().length > 0) {
        onSave(content);
        lastSavedContent.current = content;
      }
    }, delay),
    [onSave, delay]
  );

  useEffect(() => {
    debouncedSave(content);
    
    return () => {
      debouncedSave.cancel();
    };
  }, [content, debouncedSave]);

  const forceSave = useCallback(() => {
    debouncedSave.cancel();
    if (content !== lastSavedContent.current) {
      onSave(content);
      lastSavedContent.current = content;
    }
  }, [content, onSave, debouncedSave]);

  return { forceSave };
};
```

## Testing Patterns

### Backend Testing

#### 1. Service Testing
```python
# backend/tests/test_services/test_custom_generator.py
import pytest
from app.services.custom_generators.poetry_generator import PoetryQuestionGenerator

@pytest.mark.asyncio
async def test_poetry_generator():
    generator = PoetryQuestionGenerator()
    
    chapter_context = {
        'title': 'The Road Not Taken Analysis',
        'content': 'A poem about choices and their consequences...',
        'book_metadata': {'genre': 'poetry'}
    }
    
    questions = await generator.generate_questions(chapter_context, count=5)
    
    assert len(questions) == 5
    assert all(q.question_type in [QuestionType.THEME, QuestionType.RESEARCH] for q in questions)
    assert all('poetry' in q.category.lower() for q in questions)
```

#### 2. Quality Metric Testing
```python
# backend/tests/test_quality_metrics/test_readability.py
def test_readability_metric():
    metric = ReadabilityMetric()
    
    # Test simple question
    simple_score = metric.calculate_score("What happens next?")
    assert 0.4 <= simple_score <= 0.8
    
    # Test complex question
    complex_score = metric.calculate_score(
        "How does the protagonist's internal psychological transformation "
        "manifest through symbolic representations in the narrative structure?"
    )
    assert complex_score < simple_score
```

### Frontend Testing

#### 1. Component Testing
```typescript
// frontend/src/__tests__/QuestionFactory.test.tsx
import { render, screen } from '@testing-library/react';
import { QuestionFactory } from '@/components/questions/QuestionFactory';
import { QuestionType } from '@/types/chapter-questions';

describe('QuestionFactory', () => {
  it('renders character question component for character type', () => {
    const mockQuestion = {
      id: 'q1',
      question_type: QuestionType.CHARACTER,
      question_text: 'Describe the main character',
      // ... other props
    };

    render(
      <QuestionFactory
        question={mockQuestion}
        onResponseChange={jest.fn()}
        onSave={jest.fn()}
      />
    );

    expect(screen.getByText('Character Notes')).toBeInTheDocument();
  });
});
```

#### 2. Hook Testing
```typescript
// frontend/src/__tests__/hooks/useAutoSave.test.ts
import { renderHook, act } from '@testing-library/react';
import { useAutoSave } from '@/hooks/useAutoSave';

describe('useAutoSave', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('auto-saves after delay', () => {
    const onSave = jest.fn();
    const { rerender } = renderHook(
      ({ content }) => useAutoSave(content, onSave, 1000),
      { initialProps: { content: '' } }
    );

    rerender({ content: 'test content' });

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(onSave).toHaveBeenCalledWith('test content');
  });
});
```

## Performance Optimization

### Backend Optimization

#### 1. Caching Strategies
```python
# backend/app/services/caching/question_cache.py
from functools import wraps
import json
import hashlib

def cache_questions(expiry_seconds: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function arguments
            cache_key = f"questions:{hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()}"
            
            # Try to get from cache
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await redis_client.setex(cache_key, expiry_seconds, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# Usage
@cache_questions(expiry_seconds=1800)  # 30 minutes
async def generate_chapter_questions(self, **kwargs):
    # Implementation
    pass
```

#### 2. Database Optimization
```python
# backend/app/db/optimized_queries.py
async def get_questions_with_responses_optimized(
    chapter_id: str,
    user_id: str
) -> List[Dict[str, Any]]:
    """Optimized query to get questions with responses in single query."""
    query = """
    SELECT 
        q.*,
        qr.id as response_id,
        qr.response_text,
        qr.status as response_status,
        qr.word_count,
        qr.updated_at as response_updated_at
    FROM questions q
    LEFT JOIN question_responses qr ON q.id = qr.question_id AND qr.user_id = $1
    WHERE q.chapter_id = $2
    ORDER BY q.order_index
    """
    
    return await database.fetch_all(query, [user_id, chapter_id])
```

### Frontend Optimization

#### 1. Lazy Loading
```typescript
// frontend/src/components/questions/LazyQuestionList.tsx
import { lazy, Suspense } from 'react';
import { Virtuoso } from 'react-virtuoso';

const QuestionItem = lazy(() => import('./QuestionItem'));

export const LazyQuestionList: React.FC<{ questions: Question[] }> = ({ questions }) => {
  return (
    <Virtuoso
      data={questions}
      itemContent={(index, question) => (
        <Suspense fallback={<div>Loading question...</div>}>
          <QuestionItem key={question.id} question={question} />
        </Suspense>
      )}
    />
  );
};
```

#### 2. Memoization
```typescript
// frontend/src/components/questions/OptimizedQuestionDisplay.tsx
import React, { memo, useMemo } from 'react';

interface QuestionDisplayProps {
  question: Question;
  response?: QuestionResponse;
  onResponseChange: (text: string) => void;
}

export const OptimizedQuestionDisplay = memo<QuestionDisplayProps>(
  ({ question, response, onResponseChange }) => {
    const helpContent = useMemo(() => {
      if (!question.metadata.help_text) return null;
      return (
        <div className="help-content">
          {question.metadata.help_text}
        </div>
      );
    }, [question.metadata.help_text]);

    const responseMetrics = useMemo(() => {
      if (!response?.response_text) return { wordCount: 0, estimatedTime: 0 };
      
      const wordCount = response.response_text.split(/\s+/).length;
      const estimatedTime = Math.ceil(wordCount / 200); // 200 words per minute reading
      
      return { wordCount, estimatedTime };
    }, [response?.response_text]);

    return (
      <div className="question-display">
        <h3>{question.question_text}</h3>
        {helpContent}
        <div className="metrics">
          Words: {responseMetrics.wordCount} | 
          Est. read time: {responseMetrics.estimatedTime}m
        </div>
        {/* Response input */}
      </div>
    );
  }
);
```

## Deployment and Monitoring

### Environment Configuration
```python
# backend/app/core/config.py
class QuestionServiceConfig:
    # AI Service settings
    AI_SERVICE_PROVIDER: str = "openai"  # openai, anthropic, custom
    AI_SERVICE_API_KEY: str = ""
    AI_SERVICE_MODEL: str = "gpt-3.5-turbo"
    AI_SERVICE_TIMEOUT: int = 30
    
    # Generation settings
    MAX_QUESTIONS_PER_REQUEST: int = 50
    DEFAULT_QUESTION_COUNT: int = 10
    QUESTION_CACHE_TTL: int = 3600
    
    # Quality settings
    MINIMUM_QUALITY_SCORE: float = 0.6
    ENABLE_QUALITY_FILTERING: bool = True
    
    # Rate limiting
    GENERATION_RATE_LIMIT: int = 100  # per hour per user
    API_RATE_LIMIT: int = 1000  # per hour per user
```

### Monitoring and Metrics
```python
# backend/app/monitoring/question_metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics
question_generation_requests = Counter(
    'question_generation_requests_total',
    'Total question generation requests',
    ['user_id', 'book_genre', 'status']
)

question_generation_duration = Histogram(
    'question_generation_duration_seconds',
    'Time spent generating questions',
    ['book_genre', 'question_count']
)

active_question_sessions = Gauge(
    'active_question_sessions',
    'Number of active question answering sessions'
)

# Usage
async def generate_questions_with_metrics(**kwargs):
    start_time = time.time()
    
    try:
        result = await generate_questions(**kwargs)
        question_generation_requests.labels(
            user_id=kwargs['user_id'],
            book_genre=kwargs.get('book_genre', 'unknown'),
            status='success'
        ).inc()
        
        return result
    except Exception as e:
        question_generation_requests.labels(
            user_id=kwargs['user_id'],
            book_genre=kwargs.get('book_genre', 'unknown'),
            status='error'
        ).inc()
        raise
    finally:
        duration = time.time() - start_time
        question_generation_duration.labels(
            book_genre=kwargs.get('book_genre', 'unknown'),
            question_count=kwargs.get('count', 0)
        ).observe(duration)
```

## Best Practices

### Code Organization
- Keep question types as enums to ensure consistency
- Use composition over inheritance for question generators
- Implement clear interfaces for extensibility
- Separate concerns between generation, quality, and feedback

### Error Handling
- Provide meaningful error messages
- Implement fallback mechanisms for AI service failures
- Log errors with sufficient context for debugging
- Use circuit breakers for external service calls

### Security
- Validate all user inputs
- Implement rate limiting on generation endpoints
- Sanitize question and response content
- Use proper authentication and authorization

### Testing
- Write comprehensive unit tests for all services
- Test edge cases and error conditions
- Use integration tests for API endpoints
- Implement performance testing for generation workflows

---

*For additional implementation examples, see the [Question System Integration Guide](integration-question-system.md) and [Performance Optimization Guide](question-performance-optimization.md).*
