# Performance Optimization Guide for Question Generation

## Overview
This guide provides comprehensive strategies for optimizing the performance of the question generation system, covering both backend AI processing and frontend user experience optimizations.

## Backend Performance Optimization

### AI Service Optimization

#### Request Batching and Pooling
Optimize AI API calls through intelligent batching:

```python
# backend/app/services/ai_optimization.py
class AIRequestOptimizer:
    def __init__(self):
        self.request_queue = asyncio.Queue()
        self.batch_processor = None
        self.batch_size = 5
        self.batch_timeout = 2.0  # seconds
        
    async def start_batch_processor(self):
        """Start the background batch processor."""
        self.batch_processor = asyncio.create_task(self._process_batches())
    
    async def _process_batches(self):
        """Process AI requests in batches for efficiency."""
        while True:
            batch = []
            deadline = time.time() + self.batch_timeout
            
            # Collect requests until batch is full or timeout
            while len(batch) < self.batch_size and time.time() < deadline:
                try:
                    request = await asyncio.wait_for(
                        self.request_queue.get(), 
                        timeout=max(0.1, deadline - time.time())
                    )
                    batch.append(request)
                except asyncio.TimeoutError:
                    break
            
            if batch:
                await self._process_batch(batch)
    
    async def _process_batch(self, batch: List[Dict]):
        """Process a batch of AI requests simultaneously."""
        # Combine similar requests for efficiency
        grouped_requests = self._group_similar_requests(batch)
        
        tasks = []
        for group in grouped_requests:
            if len(group) > 1:
                # Batch similar requests together
                task = self._process_grouped_requests(group)
            else:
                # Process single request
                task = self._process_single_request(group[0])
            tasks.append(task)
        
        # Execute all batches concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _group_similar_requests(self, batch: List[Dict]) -> List[List[Dict]]:
        """Group requests with similar parameters."""
        groups = defaultdict(list)
        
        for request in batch:
            # Create a key based on request similarity
            key = (
                request.get('difficulty'),
                tuple(sorted(request.get('focus', []))),
                request.get('book_genre'),
                request.get('chapter_type')
            )
            groups[key].append(request)
        
        return list(groups.values())
```

#### Response Caching Strategy
Implement intelligent caching for AI responses:

```python
# backend/app/services/question_cache.py
class QuestionCacheService:
    def __init__(self):
        self.redis_client = redis.Redis()
        self.cache_ttl = {
            'questions': 3600,      # 1 hour
            'templates': 86400,     # 24 hours
            'quality_scores': 1800  # 30 minutes
        }
    
    async def get_cached_questions(
        self, 
        cache_key: str,
        context_hash: str
    ) -> Optional[List[Dict]]:
        """Retrieve cached questions if available and still relevant."""
        
        cache_data = await self.redis_client.hget(cache_key, context_hash)
        if not cache_data:
            return None
        
        try:
            cached = json.loads(cache_data)
            
            # Check if cache is still valid
            if time.time() - cached['timestamp'] < self.cache_ttl['questions']:
                # Verify context hasn't changed significantly
                if self._is_context_similar(cached['context'], context_hash):
                    return cached['questions']
        except (json.JSONDecodeError, KeyError):
            pass
        
        return None
    
    async def cache_questions(
        self,
        cache_key: str,
        context_hash: str,
        questions: List[Dict],
        context_data: Dict
    ):
        """Cache generated questions with context."""
        cache_data = {
            'questions': questions,
            'context': context_hash,
            'context_data': context_data,
            'timestamp': time.time()
        }
        
        await self.redis_client.hset(
            cache_key,
            context_hash,
            json.dumps(cache_data)
        )
        
        # Set expiration for the hash key
        await self.redis_client.expire(cache_key, self.cache_ttl['questions'])
    
    def _generate_context_hash(self, chapter_data: Dict) -> str:
        """Generate a hash representing chapter context for caching."""
        context_items = [
            chapter_data.get('title', ''),
            chapter_data.get('content', '')[:500],  # First 500 chars
            chapter_data.get('genre', ''),
            str(chapter_data.get('word_count', 0) // 100)  # Rounded word count
        ]
        
        context_string = '|'.join(str(item) for item in context_items)
        return hashlib.md5(context_string.encode()).hexdigest()
    
    def _is_context_similar(self, cached_hash: str, current_hash: str) -> bool:
        """Check if contexts are similar enough to use cached results."""
        # For now, require exact match, but could implement fuzzy matching
        return cached_hash == current_hash
```

#### Connection Pooling and Circuit Breakers
Optimize external AI service connections:

```python
# backend/app/services/ai_connection_manager.py
class AIConnectionManager:
    def __init__(self):
        self.connection_pool = None
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=30,
            recovery_timeout=60
        )
        self.retry_policy = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=10.0,
            max_retries=3
        )
    
    async def initialize_pool(self):
        """Initialize connection pool for AI service."""
        connector = aiohttp.TCPConnector(
            limit=20,           # Total connection pool size
            limit_per_host=10,  # Max connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=60,      # Total request timeout
            connect=10,    # Connection timeout
            sock_read=30   # Socket read timeout
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'QuestionGenerator/1.0'}
        )
    
    @circuit_breaker
    async def make_ai_request(self, prompt: str, **kwargs) -> Dict:
        """Make AI request with circuit breaker protection."""
        return await self.retry_policy.execute(
            self._make_request_with_timeout,
            prompt=prompt,
            **kwargs
        )
    
    async def _make_request_with_timeout(self, prompt: str, **kwargs) -> Dict:
        """Make the actual AI request with timeout handling."""
        try:
            async with self.session.post(
                self.ai_service_url,
                json={
                    'prompt': prompt,
                    'max_tokens': kwargs.get('max_tokens', 1000),
                    'temperature': kwargs.get('temperature', 0.7)
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    await asyncio.sleep(retry_after)
                    raise RateLimitError("AI service rate limited")
                
                response.raise_for_status()
                return await response.json()
                
        except asyncio.TimeoutError:
            raise AIServiceTimeout("AI service request timed out")
        except aiohttp.ClientError as e:
            raise AIServiceError(f"AI service error: {str(e)}")
```

### Database Optimization

#### Query Optimization
Optimize database queries for question operations:

```sql
-- Optimized query for loading questions with responses
-- Uses CTEs and optimized joins
WITH question_stats AS (
    SELECT 
        q.id,
        q.chapter_id,
        q.question_text,
        q.question_type,
        q.difficulty,
        q.order_index,
        q.metadata,
        q.generated_at,
        CASE 
            WHEN qr.id IS NOT NULL THEN qr.status
            ELSE NULL 
        END as response_status,
        CASE 
            WHEN qr.id IS NOT NULL THEN qr.word_count
            ELSE 0 
        END as response_word_count,
        qr.updated_at as response_updated_at,
        COALESCE(AVG(qrat.rating), 0) as avg_rating,
        COUNT(qrat.id) as rating_count
    FROM questions q
    LEFT JOIN question_responses qr ON q.id = qr.question_id AND qr.user_id = $1
    LEFT JOIN question_ratings qrat ON q.id = qrat.question_id
    WHERE q.chapter_id = $2
    GROUP BY q.id, qr.id, qr.status, qr.word_count, qr.updated_at
)
SELECT * FROM question_stats
ORDER BY order_index;

-- Index optimization for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_questions_chapter_user_type 
ON questions (chapter_id, user_id, question_type) 
INCLUDE (id, difficulty, order_index);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_question_responses_user_status 
ON question_responses (user_id, status, updated_at DESC)
WHERE status = 'completed';

-- Materialized view for question analytics
CREATE MATERIALIZED VIEW question_analytics_summary AS
SELECT 
    DATE_TRUNC('day', q.generated_at) as date,
    q.question_type,
    q.difficulty,
    COUNT(*) as questions_generated,
    COUNT(qr.id) as questions_answered,
    AVG(qr.word_count) as avg_response_length,
    AVG(qrat.rating) as avg_rating
FROM questions q
LEFT JOIN question_responses qr ON q.id = qr.question_id
LEFT JOIN question_ratings qrat ON q.id = qrat.question_id
WHERE q.generated_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE_TRUNC('day', q.generated_at), q.question_type, q.difficulty;

-- Refresh schedule for materialized view
CREATE OR REPLACE FUNCTION refresh_question_analytics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY question_analytics_summary;
END;
$$ LANGUAGE plpgsql;

-- Schedule refresh every hour
SELECT cron.schedule('refresh-question-analytics', '0 * * * *', 'SELECT refresh_question_analytics();');
```

#### Connection Pool Optimization
Configure database connection pooling:

```python
# backend/app/db/connection_pool.py
class OptimizedConnectionPool:
    def __init__(self):
        self.pool = None
        self.pool_config = {
            'min_size': 5,      # Minimum connections
            'max_size': 20,     # Maximum connections
            'max_queries': 50000,  # Queries per connection before refresh
            'max_inactive_connection_lifetime': 300,  # 5 minutes
        }
    
    async def initialize_pool(self):
        """Initialize optimized connection pool."""
        self.pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=self.pool_config['min_size'],
            max_size=self.pool_config['max_size'],
            max_queries=self.pool_config['max_queries'],
            max_inactive_connection_lifetime=self.pool_config['max_inactive_connection_lifetime'],
            command_timeout=30,
            server_settings={
                'jit': 'off',  # Disable JIT for faster simple queries
                'application_name': 'question-service'
            }
        )
    
    async def execute_optimized_query(self, query: str, *args):
        """Execute query with connection reuse optimization."""
        async with self.pool.acquire() as connection:
            # Prepare statement for reuse
            statement = await connection.prepare(query)
            return await statement.fetch(*args)
    
    async def batch_insert_questions(self, questions: List[Dict]):
        """Optimized batch insert for questions."""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                # Use COPY for bulk inserts
                await connection.copy_records_to_table(
                    'questions',
                    records=questions,
                    columns=['id', 'chapter_id', 'question_text', 'question_type', 
                            'difficulty', 'category', 'order_index', 'metadata']
                )
```

### Async Processing and Background Tasks

#### Question Generation Queue
Implement background processing for heavy operations:

```python
# backend/app/services/question_queue.py
class QuestionGenerationQueue:
    def __init__(self):
        self.redis_client = redis.Redis()
        self.queue = Queue('question_generation', connection=self.redis_client)
        self.high_priority_queue = Queue('question_generation_priority', connection=self.redis_client)
    
    async def enqueue_generation_request(
        self,
        request_data: Dict,
        priority: str = 'normal',
        delay: int = 0
    ) -> str:
        """Enqueue a question generation request."""
        
        job_data = {
            'book_id': request_data['book_id'],
            'chapter_id': request_data['chapter_id'],
            'user_id': request_data['user_id'],
            'generation_params': request_data['params'],
            'callback_url': request_data.get('callback_url'),
            'retry_count': 0,
            'max_retries': 3
        }
        
        queue = self.high_priority_queue if priority == 'high' else self.queue
        
        if delay > 0:
            job = queue.enqueue_in(
                timedelta(seconds=delay),
                'app.workers.question_worker.generate_questions',
                job_data,
                timeout=300,  # 5 minute timeout
                retry=Retry(max=3, interval=[10, 30, 60])
            )
        else:
            job = queue.enqueue(
                'app.workers.question_worker.generate_questions',
                job_data,
                timeout=300,
                retry=Retry(max=3, interval=[10, 30, 60])
            )
        
        return job.id
    
    async def get_job_status(self, job_id: str) -> Dict:
        """Get the status of a queued job."""
        try:
            job = Job.fetch(job_id, connection=self.redis_client)
            return {
                'id': job.id,
                'status': job.get_status(),
                'progress': job.meta.get('progress', 0),
                'result': job.result,
                'error': job.exc_info,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'ended_at': job.ended_at
            }
        except NoSuchJobError:
            return {'id': job_id, 'status': 'not_found'}
```

#### Background Worker Implementation
Implement efficient background workers:

```python
# backend/app/workers/question_worker.py
class QuestionWorker:
    def __init__(self):
        self.question_service = QuestionGenerationService()
        self.cache_service = QuestionCacheService()
        
    async def generate_questions(self, job_data: Dict) -> Dict:
        """Background worker for question generation."""
        job_id = get_current_job().id
        
        try:
            # Update progress
            self._update_progress(job_id, 10, "Starting generation...")
            
            # Check cache first
            cache_key = self._generate_cache_key(job_data)
            cached_questions = await self.cache_service.get_cached_questions(cache_key)
            
            if cached_questions:
                self._update_progress(job_id, 100, "Retrieved from cache")
                return {
                    'questions': cached_questions,
                    'source': 'cache',
                    'generation_time': 0
                }
            
            # Generate new questions
            self._update_progress(job_id, 30, "Analyzing chapter context...")
            
            start_time = time.time()
            questions = await self.question_service.generate_chapter_questions(
                book_id=job_data['book_id'],
                chapter_id=job_data['chapter_id'],
                user_id=job_data['user_id'],
                **job_data['generation_params']
            )
            
            generation_time = time.time() - start_time
            
            self._update_progress(job_id, 80, "Saving questions...")
            
            # Save to database
            saved_questions = []
            for question in questions:
                saved_question = await self.question_service.save_question(question)
                saved_questions.append(saved_question)
            
            # Cache results
            await self.cache_service.cache_questions(cache_key, saved_questions)
            
            self._update_progress(job_id, 100, "Generation complete")
            
            # Send callback if provided
            if job_data.get('callback_url'):
                await self._send_completion_callback(job_data['callback_url'], {
                    'job_id': job_id,
                    'status': 'completed',
                    'questions': saved_questions
                })
            
            return {
                'questions': saved_questions,
                'source': 'generated',
                'generation_time': generation_time,
                'count': len(saved_questions)
            }
            
        except Exception as e:
            self._update_progress(job_id, -1, f"Error: {str(e)}")
            
            # Retry logic
            retry_count = job_data.get('retry_count', 0)
            max_retries = job_data.get('max_retries', 3)
            
            if retry_count < max_retries:
                # Schedule retry with exponential backoff
                delay = (2 ** retry_count) * 60  # 1, 2, 4 minutes
                job_data['retry_count'] = retry_count + 1
                
                queue = QuestionGenerationQueue()
                await queue.enqueue_generation_request(
                    job_data,
                    delay=delay
                )
                
                return {'status': 'retrying', 'retry_count': retry_count + 1}
            
            raise
    
    def _update_progress(self, job_id: str, progress: int, message: str):
        """Update job progress."""
        job = Job.fetch(job_id, connection=redis.Redis())
        job.meta['progress'] = progress
        job.meta['message'] = message
        job.meta['updated_at'] = datetime.utcnow().isoformat()
        job.save_meta()
    
    async def _send_completion_callback(self, callback_url: str, data: Dict):
        """Send completion callback to client."""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    callback_url,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=10)
                )
        except Exception as e:
            logger.warning(f"Failed to send callback: {str(e)}")
```

## Frontend Performance Optimization

### Component Optimization

#### Lazy Loading and Code Splitting
Optimize component loading for better performance:

```typescript
// frontend/src/components/questions/LazyQuestionComponents.tsx
import { lazy, Suspense } from 'react';
import { QuestionSkeleton } from './QuestionSkeleton';

// Lazy load heavy components
const QuestionGenerator = lazy(() => import('./QuestionGenerator'));
const QuestionAnalytics = lazy(() => import('./QuestionAnalytics'));
const QuestionExporter = lazy(() => import('./QuestionExporter'));

// Code split by question type
const CharacterQuestionEditor = lazy(() => import('./types/CharacterQuestionEditor'));
const PlotQuestionEditor = lazy(() => import('./types/PlotQuestionEditor'));
const ThemeQuestionEditor = lazy(() => import('./types/ThemeQuestionEditor'));

const questionTypeComponents = {
  character: CharacterQuestionEditor,
  plot: PlotQuestionEditor,
  setting: lazy(() => import('./types/SettingQuestionEditor')),
  theme: ThemeQuestionEditor,
  research: lazy(() => import('./types/ResearchQuestionEditor'))
};

export const LazyQuestionContainer: React.FC<QuestionContainerProps> = (props) => {
  return (
    <div className="question-container">
      <Suspense fallback={<QuestionSkeleton />}>
        <QuestionGenerator {...props} />
      </Suspense>
      
      {props.showAnalytics && (
        <Suspense fallback={<div>Loading analytics...</div>}>
          <QuestionAnalytics bookId={props.bookId} />
        </Suspense>
      )}
    </div>
  );
};

export const LazyQuestionEditor: React.FC<{ question: Question }> = ({ question }) => {
  const Component = questionTypeComponents[question.question_type];
  
  return (
    <Suspense fallback={<QuestionSkeleton />}>
      <Component question={question} />
    </Suspense>
  );
};
```

#### Virtual Scrolling for Large Lists
Implement virtual scrolling for question lists:

```typescript
// frontend/src/components/questions/VirtualizedQuestionList.tsx
import { FixedSizeList as List } from 'react-window';
import { useMemo, useCallback } from 'react';

interface VirtualizedQuestionListProps {
  questions: Question[];
  height: number;
  onQuestionSelect: (question: Question) => void;
}

export const VirtualizedQuestionList: React.FC<VirtualizedQuestionListProps> = ({
  questions,
  height,
  onQuestionSelect
}) => {
  const itemData = useMemo(() => ({
    questions,
    onQuestionSelect
  }), [questions, onQuestionSelect]);

  const QuestionItem = useCallback(({ index, style, data }) => {
    const question = data.questions[index];
    
    return (
      <div style={style} className="question-item-wrapper">
        <QuestionItem
          question={question}
          onClick={() => data.onQuestionSelect(question)}
        />
      </div>
    );
  }, []);

  return (
    <List
      height={height}
      itemCount={questions.length}
      itemSize={120} // Height of each question item
      itemData={itemData}
      overscanCount={5} // Render 5 extra items for smooth scrolling
    >
      {QuestionItem}
    </List>
  );
};
```

#### Memoization and State Optimization
Optimize React rendering with proper memoization:

```typescript
// frontend/src/components/questions/OptimizedQuestionDisplay.tsx
import React, { memo, useMemo, useCallback } from 'react';
import { useQuestionResponse } from '@/hooks/useQuestionResponse';

interface OptimizedQuestionDisplayProps {
  question: Question;
  onResponseChange: (questionId: string, response: string) => void;
  onSave: (questionId: string) => void;
}

export const OptimizedQuestionDisplay = memo<OptimizedQuestionDisplayProps>(
  ({ question, onResponseChange, onSave }) => {
    const { response, isLoading, error } = useQuestionResponse(question.id);
    
    // Memoize expensive calculations
    const questionMetrics = useMemo(() => {
      const wordCount = response?.response_text?.split(/\s+/).length || 0;
      const targetRange = question.metadata.suggested_response_length;
      const readingTime = Math.ceil(wordCount / 200); // 200 WPM
      
      return {
        wordCount,
        targetRange,
        readingTime,
        progressPercentage: Math.min((wordCount / 300) * 100, 100) // Assuming 300 target
      };
    }, [response?.response_text, question.metadata.suggested_response_length]);
    
    // Memoize handlers to prevent unnecessary re-renders
    const handleResponseChange = useCallback((newResponse: string) => {
      onResponseChange(question.id, newResponse);
    }, [question.id, onResponseChange]);
    
    const handleSave = useCallback(() => {
      onSave(question.id);
    }, [question.id, onSave]);
    
    // Memoize help content to avoid re-rendering
    const helpContent = useMemo(() => {
      if (!question.metadata.help_text) return null;
      
      return (
        <div className="question-help">
          <p>{question.metadata.help_text}</p>
          {question.metadata.examples && (
            <ul className="question-examples">
              {question.metadata.examples.map((example, index) => (
                <li key={index}>{example}</li>
              ))}
            </ul>
          )}
        </div>
      );
    }, [question.metadata.help_text, question.metadata.examples]);
    
    if (isLoading) return <QuestionSkeleton />;
    if (error) return <QuestionError error={error} />;
    
    return (
      <div className="optimized-question-display">
        <div className="question-header">
          <h3>{question.question_text}</h3>
          <div className="question-meta">
            <span className="type">{question.question_type}</span>
            <span className="difficulty">{question.difficulty}</span>
          </div>
        </div>
        
        {helpContent}
        
        <QuestionResponseEditor
          value={response?.response_text || ''}
          onChange={handleResponseChange}
          onSave={handleSave}
        />
        
        <QuestionMetrics {...questionMetrics} />
      </div>
    );
  },
  // Custom comparison function for memo
  (prevProps, nextProps) => {
    return (
      prevProps.question.id === nextProps.question.id &&
      prevProps.question.question_text === nextProps.question.question_text &&
      prevProps.onResponseChange === nextProps.onResponseChange &&
      prevProps.onSave === nextProps.onSave
    );
  }
);
```

### Data Fetching Optimization

#### Smart Query Caching
Implement intelligent query caching with React Query:

```typescript
// frontend/src/hooks/useOptimizedQuestions.ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

export const useOptimizedQuestions = (
  bookId: string,
  chapterId: string,
  options: {
    prefetchAdjacent?: boolean;
    staleTime?: number;
    backgroundRefetch?: boolean;
  } = {}
) => {
  const queryClient = useQueryClient();
  
  const queryKey = useMemo(() => 
    ['questions', bookId, chapterId], 
    [bookId, chapterId]
  );
  
  const {
    data: questions,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey,
    queryFn: () => questionAPI.getQuestions(bookId, chapterId),
    staleTime: options.staleTime || 5 * 60 * 1000, // 5 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
    refetchOnWindowFocus: options.backgroundRefetch !== false,
    refetchInterval: options.backgroundRefetch ? 30000 : false, // 30 seconds
    select: (data) => {
      // Optimize data structure for rendering
      return data.questions.map(question => ({
        ...question,
        // Pre-calculate expensive properties
        hasResponse: Boolean(question.response?.response_text),
        isCompleted: question.response?.status === 'completed',
        wordCount: question.response?.word_count || 0
      }));
    }
  });
  
  // Prefetch adjacent chapters' questions
  const prefetchAdjacent = useCallback(async (adjacentChapterIds: string[]) => {
    if (!options.prefetchAdjacent) return;
    
    const prefetchPromises = adjacentChapterIds.map(adjacentChapterId =>
      queryClient.prefetchQuery({
        queryKey: ['questions', bookId, adjacentChapterId],
        queryFn: () => questionAPI.getQuestions(bookId, adjacentChapterId),
        staleTime: 10 * 60 * 1000 // 10 minutes for prefetched data
      })
    );
    
    await Promise.allSettled(prefetchPromises);
  }, [queryClient, bookId, options.prefetchAdjacent]);
  
  // Optimistic updates for better UX
  const updateQuestionOptimistically = useCallback((
    questionId: string,
    updates: Partial<Question>
  ) => {
    queryClient.setQueryData(queryKey, (oldData: any) => {
      if (!oldData) return oldData;
      
      return {
        ...oldData,
        questions: oldData.questions.map((q: Question) =>
          q.id === questionId ? { ...q, ...updates } : q
        )
      };
    });
  }, [queryClient, queryKey]);
  
  return {
    questions,
    isLoading,
    error,
    refetch,
    prefetchA
