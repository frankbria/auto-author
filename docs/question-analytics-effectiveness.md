# Analytics Documentation for Question Effectiveness Tracking

## Overview
This documentation covers the comprehensive analytics system for tracking question effectiveness, measuring user engagement, analyzing performance metrics, and using data-driven insights to improve the question generation system.

## Analytics Framework

### Key Performance Indicators (KPIs)

#### Question Generation Metrics
- **Generation Success Rate**: Percentage of successful question generations
- **Generation Speed**: Average time to generate questions
- **Quality Score Distribution**: Distribution of AI-generated question quality scores
- **Cache Hit Rate**: Percentage of requests served from cache
- **Error Rate**: Failed generation attempts per time period

#### User Engagement Metrics
- **Question Response Rate**: Percentage of questions that receive responses
- **Response Completion Rate**: Percentage of responses marked as completed
- **Average Response Length**: Word count distribution of user responses
- **Time to First Response**: How quickly users start answering questions
- **Session Duration**: Time spent in question interface per session

#### Question Quality Metrics
- **User Rating Distribution**: 1-5 star ratings across all questions
- **Rating Correlation**: Relationship between AI quality scores and user ratings
- **Question Regeneration Rate**: How often users regenerate questions
- **Question Type Effectiveness**: Performance by question category
- **Difficulty Appropriateness**: Match between intended and perceived difficulty

## Analytics Data Collection

### Event Tracking System
Comprehensive event tracking for all question interactions:

```python
# backend/app/services/analytics_collector.py
class QuestionAnalyticsCollector:
    def __init__(self):
        self.event_store = EventStore()
        self.metrics_aggregator = MetricsAggregator()
        self.real_time_processor = RealTimeProcessor()
    
    async def track_question_event(
        self,
        event_type: str,
        user_id: str,
        question_id: str,
        context: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        """Track question-related events for analytics."""
        
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': event_type,
            'user_id': user_id,
            'question_id': question_id,
            'timestamp': timestamp or datetime.utcnow(),
            'context': context,
            'session_id': context.get('session_id'),
            'book_id': context.get('book_id'),
            'chapter_id': context.get('chapter_id')
        }
        
        # Store raw event
        await self.event_store.store_event(event)
        
        # Real-time processing for immediate metrics
        await self.real_time_processor.process_event(event)
        
        # Trigger aggregation if needed
        if event_type in ['question_rated', 'response_completed']:
            await self.metrics_aggregator.update_metrics(event)
    
    async def track_question_generation(
        self,
        user_id: str,
        book_id: str,
        chapter_id: str,
        generation_params: Dict,
        result: Dict
    ):
        """Track question generation events."""
        
        context = {
            'book_id': book_id,
            'chapter_id': chapter_id,
            'generation_params': generation_params,
            'questions_generated': result.get('count', 0),
            'generation_time_ms': result.get('generation_time', 0) * 1000,
            'source': result.get('source', 'ai'),  # ai, cache, template
            'quality_scores': [q.get('quality_score') for q in result.get('questions', [])],
            'question_types': [q.get('question_type') for q in result.get('questions', [])]
        }
        
        await self.track_question_event(
            'question_generation',
            user_id,
            None,  # No specific question ID for generation
            context
        )
    
    async def track_question_interaction(
        self,
        event_type: str,
        user_id: str,
        question_id: str,
        interaction_data: Dict
    ):
        """Track user interactions with specific questions."""
        
        context = {
            'interaction_type': event_type,
            'question_metadata': interaction_data.get('question_metadata', {}),
            'response_data': interaction_data.get('response_data', {}),
            'time_spent_ms': interaction_data.get('time_spent_ms', 0),
            'edit_count': interaction_data.get('edit_count', 0),
            'word_count': interaction_data.get('word_count', 0)
        }
        
        await self.track_question_event(
            event_type,
            user_id,
            question_id,
            context
        )
```

### Data Pipeline Architecture
Scalable data processing pipeline for analytics:

```python
# backend/app/services/analytics_pipeline.py
class AnalyticsPipeline:
    def __init__(self):
        self.stream_processor = StreamProcessor()
        self.batch_processor = BatchProcessor()
        self.data_warehouse = DataWarehouse()
        self.notification_service = NotificationService()
    
    async def process_analytics_stream(self):
        """Process real-time analytics events."""
        
        async for event_batch in self.stream_processor.get_event_batches():
            try:
                # Process each event in the batch
                processed_events = []
                for event in event_batch:
                    processed_event = await self._enrich_event(event)
                    processed_events.append(processed_event)
                
                # Update real-time metrics
                await self._update_real_time_metrics(processed_events)
                
                # Check for alerts
                await self._check_alert_conditions(processed_events)
                
                # Store for batch processing
                await self.batch_processor.queue_events(processed_events)
                
            except Exception as e:
                logger.error(f"Error processing analytics batch: {str(e)}")
                await self.notification_service.send_error_alert(
                    "Analytics Pipeline Error",
                    str(e)
                )
    
    async def _enrich_event(self, event: Dict) -> Dict:
        """Enrich event with additional context."""
        
        enriched_event = event.copy()
        
        # Add user context
        if event.get('user_id'):
            user_info = await self._get_user_context(event['user_id'])
            enriched_event['user_context'] = user_info
        
        # Add book/chapter context
        if event.get('book_id'):
            book_info = await self._get_book_context(event['book_id'])
            enriched_event['book_context'] = book_info
        
        # Add temporal context
        enriched_event['temporal_context'] = {
            'hour_of_day': event['timestamp'].hour,
            'day_of_week': event['timestamp'].weekday(),
            'is_weekend': event['timestamp'].weekday() >= 5,
            'month': event['timestamp'].month
        }
        
        return enriched_event
    
    async def run_daily_batch_processing(self):
        """Run daily batch processing for comprehensive analytics."""
        
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # Process question effectiveness metrics
        await self._process_question_effectiveness(yesterday)
        
        # Calculate user engagement metrics
        await self._process_user_engagement(yesterday)
        
        # Generate quality insights
        await self._process_quality_insights(yesterday)
        
        # Update recommendation models
        await self._update_recommendation_models(yesterday)
        
        # Generate daily reports
        await self._generate_daily_reports(yesterday)
```

## Question Effectiveness Metrics

### Question Performance Analysis
Comprehensive analysis of individual question performance:

```python
# backend/app/services/question_effectiveness.py
class QuestionEffectivenessAnalyzer:
    def __init__(self):
        self.metrics_calculator = MetricsCalculator()
        self.statistical_analyzer = StatisticalAnalyzer()
        self.ml_model = QuestionEffectivenessModel()
    
    async def analyze_question_effectiveness(
        self,
        question_id: str,
        time_period: str = '30d'
    ) -> Dict[str, Any]:
        """Analyze effectiveness of a specific question."""
        
        # Get question data
        question_data = await self.get_question_with_responses(question_id)
        
        # Calculate core metrics
        metrics = {
            'response_rate': await self._calculate_response_rate(question_id, time_period),
            'completion_rate': await self._calculate_completion_rate(question_id, time_period),
            'average_response_length': await self._calculate_avg_response_length(question_id),
            'response_quality_score': await self._calculate_response_quality(question_id),
            'user_satisfaction': await self._calculate_user_satisfaction(question_id),
            'time_to_respond': await self._calculate_time_to_respond(question_id),
            'regeneration_rate': await self._calculate_regeneration_rate(question_id)
        }
        
        # Calculate effectiveness score
        effectiveness_score = await self._calculate_effectiveness_score(metrics)
        
        # Generate insights
        insights = await self._generate_question_insights(question_data, metrics)
        
        # Predict future performance
        predicted_performance = await self.ml_model.predict_performance(
            question_data, metrics
        )
        
        return {
            'question_id': question_id,
            'effectiveness_score': effectiveness_score,
            'metrics': metrics,
            'insights': insights,
            'predicted_performance': predicted_performance,
            'recommendations': await self._generate_recommendations(metrics, insights)
        }
    
    async def _calculate_response_rate(self, question_id: str, time_period: str) -> float:
        """Calculate the percentage of users who responded to this question."""
        
        query = """
        SELECT 
            COUNT(DISTINCT q.user_id) as total_users,
            COUNT(DISTINCT qr.user_id) as responding_users
        FROM questions q
        LEFT JOIN question_responses qr ON q.id = qr.question_id
        WHERE q.id = $1
        AND q.generated_at >= NOW() - INTERVAL $2
        """
        
        result = await self.database.fetch_one(query, [question_id, time_period])
        
        if result['total_users'] == 0:
            return 0.0
        
        return result['responding_users'] / result['total_users']
    
    async def _calculate_effectiveness_score(self, metrics: Dict) -> float:
        """Calculate overall effectiveness score (0-100)."""
        
        # Weighted scoring model
        weights = {
            'response_rate': 0.25,
            'completion_rate': 0.20,
            'user_satisfaction': 0.20,
            'response_quality_score': 0.15,
            'average_response_length': 0.10,
            'time_to_respond': 0.10
        }
        
        # Normalize metrics to 0-1 scale
        normalized_metrics = {}
        
        # Response rate is already 0-1
        normalized_metrics['response_rate'] = metrics['response_rate']
        
        # Completion rate is already 0-1
        normalized_metrics['completion_rate'] = metrics['completion_rate']
        
        # User satisfaction (1-5 scale) normalized to 0-1
        normalized_metrics['user_satisfaction'] = (metrics['user_satisfaction'] - 1) / 4
        
        # Response quality score is already 0-1
        normalized_metrics['response_quality_score'] = metrics['response_quality_score']
        
        # Response length normalized (target around 200 words)
        target_length = 200
        actual_length = metrics['average_response_length']
        length_score = min(actual_length / target_length, 1.0) if actual_length > 0 else 0
        normalized_metrics['average_response_length'] = length_score
        
        # Time to respond normalized (lower is better, target < 5 minutes)
        time_minutes = metrics['time_to_respond'] / 60
        time_score = max(0, 1 - (time_minutes / 10))  # 0 at 10+ minutes
        normalized_metrics['time_to_respond'] = time_score
        
        # Calculate weighted score
        effectiveness_score = sum(
            normalized_metrics[metric] * weight
            for metric, weight in weights.items()
        ) * 100
        
        return round(effectiveness_score, 2)
```

### Cohort Analysis
Analyze question performance across different user cohorts:

```python
# backend/app/services/cohort_analysis.py
class QuestionCohortAnalyzer:
    def __init__(self):
        self.cohort_builder = CohortBuilder()
        self.statistical_analyzer = StatisticalAnalyzer()
    
    async def analyze_question_cohorts(
        self,
        question_id: str,
        cohort_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze question performance across different user cohorts."""
        
        # Build cohorts based on criteria
        cohorts = await self.cohort_builder.build_cohorts(cohort_criteria)
        
        cohort_analysis = {}
        
        for cohort_name, cohort_users in cohorts.items():
            cohort_metrics = await self._analyze_cohort_performance(
                question_id,
                cohort_users
            )
            
            cohort_analysis[cohort_name] = {
                'user_count': len(cohort_users),
                'metrics': cohort_metrics,
                'statistical_significance': await self._test_statistical_significance(
                    cohort_metrics,
                    cohort_analysis.get('baseline', {}).get('metrics', {})
                )
            }
        
        # Compare cohorts
        comparison = await self._compare_cohorts(cohort_analysis)
        
        return {
            'cohort_analysis': cohort_analysis,
            'comparison': comparison,
            'insights': await self._generate_cohort_insights(cohort_analysis)
        }
    
    async def _analyze_cohort_performance(
        self,
        question_id: str,
        user_ids: List[str]
    ) -> Dict[str, float]:
        """Analyze question performance for a specific cohort."""
        
        query = """
        SELECT 
            COUNT(*) as total_exposures,
            COUNT(qr.id) as total_responses,
            COUNT(CASE WHEN qr.status = 'completed' THEN 1 END) as completed_responses,
            AVG(qr.word_count) as avg_word_count,
            AVG(qrat.rating) as avg_rating,
            AVG(EXTRACT(EPOCH FROM qr.created_at - q.generated_at)) as avg_time_to_respond
        FROM questions q
        LEFT JOIN question_responses qr ON q.id = qr.question_id
        LEFT JOIN question_ratings qrat ON q.id = qrat.question_id
        WHERE q.id = $1 AND q.user_id = ANY($2)
        """
        
        result = await self.database.fetch_one(query, [question_id, user_ids])
        
        return {
            'response_rate': result['total_responses'] / max(result['total_exposures'], 1),
            'completion_rate': result['completed_responses'] / max(result['total_responses'], 1),
            'avg_word_count': result['avg_word_count'] or 0,
            'avg_rating': result['avg_rating'] or 0,
            'avg_time_to_respond': result['avg_time_to_respond'] or 0
        }
```

## User Engagement Analytics

### Engagement Metrics Dashboard
Track user engagement with the question system:

```python
# backend/app/services/engagement_analytics.py
class EngagementAnalytics:
    def __init__(self):
        self.session_analyzer = SessionAnalyzer()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.retention_analyzer = RetentionAnalyzer()
    
    async def generate_engagement_report(
        self,
        time_period: str = '30d',
        user_segments: List[str] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive engagement analytics report."""
        
        report = {
            'time_period': time_period,
            'generated_at': datetime.utcnow().isoformat(),
            'metrics': {}
        }
        
        # Session metrics
        session_metrics = await self._calculate_session_metrics(time_period, user_segments)
        report['metrics']['sessions'] = session_metrics
        
        # Question interaction metrics
        interaction_metrics = await self._calculate_interaction_metrics(time_period, user_segments)
        report['metrics']['interactions'] = interaction_metrics
        
        # User journey analysis
        journey_analysis = await self._analyze_user_journeys(time_period, user_segments)
        report['metrics']['user_journeys'] = journey_analysis
        
        # Retention analysis
        retention_analysis = await self._analyze_retention(time_period, user_segments)
        report['metrics']['retention'] = retention_analysis
        
        # Engagement patterns
        patterns = await self._identify_engagement_patterns(time_period, user_segments)
        report['patterns'] = patterns
        
        return report
    
    async def _calculate_session_metrics(
        self,
        time_period: str,
        user_segments: List[str] = None
    ) -> Dict[str, Any]:
        """Calculate session-based engagement metrics."""
        
        query = """
        WITH session_data AS (
            SELECT 
                user_id,
                session_id,
                MIN(timestamp) as session_start,
                MAX(timestamp) as session_end,
                COUNT(*) as events_count,
                COUNT(DISTINCT question_id) as unique_questions,
                COUNT(CASE WHEN event_type = 'response_saved' THEN 1 END) as responses_saved,
                COUNT(CASE WHEN event_type = 'response_completed' THEN 1 END) as responses_completed
            FROM question_events
            WHERE timestamp >= NOW() - INTERVAL $1
            GROUP BY user_id, session_id
        )
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(EXTRACT(EPOCH FROM session_end - session_start)) as avg_session_duration,
            AVG(events_count) as avg_events_per_session,
            AVG(unique_questions) as avg_questions_per_session,
            AVG(responses_saved) as avg_responses_per_session,
            SUM(responses_completed) / SUM(responses_saved) as completion_rate
        FROM session_data
        WHERE session_end > session_start  -- Valid sessions only
        """
        
        result = await self.database.fetch_one(query, [time_period])
        
        return {
            'total_sessions': result['total_sessions'],
            'unique_users': result['unique_users'],
            'avg_session_duration_minutes': result['avg_session_duration'] / 60,
            'avg_events_per_session': round(result['avg_events_per_session'], 2),
            'avg_questions_per_session': round(result['avg_questions_per_session'], 2),
            'avg_responses_per_session': round(result['avg_responses_per_session'], 2),
            'session_completion_rate': round(result['completion_rate'], 3)
        }
    
    async def _analyze_user_journeys(
        self,
        time_period: str,
        user_segments: List[str] = None
    ) -> Dict[str, Any]:
        """Analyze common user journey patterns."""
        
        # Get user journey sequences
        journey_sequences = await self._get_journey_sequences(time_period, user_segments)
        
        # Identify common patterns
        common_patterns = await self._identify_common_patterns(journey_sequences)
        
        # Calculate conversion rates at each step
        conversion_funnel = await self._calculate_conversion_funnel(journey_sequences)
        
        # Identify drop-off points
        drop_off_analysis = await self._analyze_drop_off_points(journey_sequences)
        
        return {
            'common_patterns': common_patterns,
            'conversion_funnel': conversion_funnel,
            'drop_off_analysis': drop_off_analysis,
            'journey_length_distribution': await self._analyze_journey_lengths(journey_sequences)
        }
```

## Quality Analysis and Insights

### AI vs Human Quality Correlation
Analyze correlation between AI quality scores and human feedback:

```python
# backend/app/services/quality_correlation.py
class QualityCorrelationAnalyzer:
    def __init__(self):
        self.statistical_analyzer = StatisticalAnalyzer()
        self.ml_evaluator = MLModelEvaluator()
    
    async def analyze_quality_correlation(
        self,
        time_period: str = '90d'
    ) -> Dict[str, Any]:
        """Analyze correlation between AI quality scores and human ratings."""
        
        # Get questions with both AI scores and human ratings
        data = await self._get_quality_comparison_data(time_period)
        
        if len(data) < 30:  # Need sufficient data for meaningful analysis
            return {'error': 'Insufficient data for correlation analysis'}
        
        # Calculate correlation metrics
        correlation_analysis = await self._calculate_correlations(data)
        
        # Analyze by question type
        type_analysis = await self._analyze_by_question_type(data)
        
        # Analyze by difficulty level
        difficulty_analysis = await self._analyze_by_difficulty(data)
        
        # Model performance evaluation
        model_performance = await self._evaluate_model_performance(data)
        
        # Generate recommendations
        recommendations = await self._generate_quality_recommendations(
            correlation_analysis,
            type_analysis,
            difficulty_analysis
        )
        
        return {
            'correlation_analysis': correlation_analysis,
            'type_analysis': type_analysis,
            'difficulty_analysis': difficulty_analysis,
            'model_performance': model_performance,
            'recommendations': recommendations,
            'data_summary': {
                'total_questions': len(data),
                'time_period': time_period,
                'analysis_date': datetime.utcnow().isoformat()
            }
        }
    
    async def _calculate_correlations(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate various correlation metrics."""
        
        ai_scores = [item['ai_quality_score'] for item in data]
        human_ratings = [item['avg_human_rating'] for item in data]
        response_rates = [item['response_rate'] for item in data]
        completion_rates = [item['completion_rate'] for item in data]
        
        correlations = {
            'ai_vs_human_rating': self.statistical_analyzer.pearson_correlation(
                ai_scores, human_ratings
            ),
            'ai_vs_response_rate': self.statistical_analyzer.pearson_correlation(
                ai_scores, response_rates
            ),
            'ai_vs_completion_rate': self.statistical_analyzer.pearson_correlation(
                ai_scores, completion_rates
            ),
            'human_rating_vs_response_rate': self.statistical_analyzer.pearson_correlation(
                human_ratings, response_rates
            ),
            'human_rating_vs_completion_rate': self.statistical_analyzer.pearson_correlation(
                human_ratings, completion_rates
            )
        }
        
        # Add confidence intervals and significance tests
        for metric_name, correlation in correlations.items():
            significance_test = self.statistical_analyzer.correlation_significance_test(
                correlation, len(data)
            )
            correlations[metric_name] = {
                'correlation': correlation,
                'significance': significance_test,
                'interpretation': self._interpret_correlation(correlation)
            }
        
        return correlations
```

## Reporting and Visualization

### Automated Report Generation
Generate comprehensive analytics reports:

```python
# backend/app/services/report_generator.py
class QuestionAnalyticsReportGenerator:
    def __init__(self):
        self.template_engine = ReportTemplateEngine()
        self.chart_generator = ChartGenerator()
        self.export_service = ReportExportService()
    
    async def generate_comprehensive_report(
        self,
        report_type: str,
        time_period: str,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        
        report_data = {
            'metadata': {
                'report_type': report_type,
                'time_period': time_period,
                'generated_at': datetime.utcnow().isoformat(),
                'filters': filters or {}
            }
        }
        
        if report_type == 'executive_summary':
            report_data.update(await self._generate_executive_summary(time_period, filters))
        elif report_type == 'detailed_analytics':
            report_data.update(await self._generate_detailed_analytics(time_period, filters))
        elif report_type == 'quality_insights':
            report_data.update(await self._generate_quality_insights(time_period, filters))
        elif report_type == 'user_engagement':
            report_data.update(await self._generate_engagement_report(time_period, filters))
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        # Generate visualizations
        charts = await self._generate_charts(report_data)
        report_data['visualizations'] = charts
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(report_data)
        report_data['recommendations'] = recommendations
        
        return report_data
    
    async def _generate_executive_summary(
        self,
        time_period: str,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary report."""
        
        # Key metrics
        key_metrics = await self._get_key_metrics(time_period, filters)
        
        # Trends
        trends = await self._calculate_trends(time_period, filters)
        
        # Performance highlights
        highlights = await self._identify_performance_highlights(time_period, filters)
        
        # Areas for improvement
        improvement_areas = await self._identify_improvement_areas(time_period, filters)
        
        return {
            'key_metrics': key_metrics,
            'trends': trends,
            'highlights': highlights,
            'improvement_areas': improvement_areas
        }
    
    async def export_report(
        self,
        report_data: Dict[str, Any],
        format: str = 'pdf'
    ) -> bytes:
        """Export report in specified format."""
        
        if format == 'pdf':
            return await self.export_service.export_to_pdf(report_data)
        elif format == 'excel':
            return await self.export_service.export_to_excel(report_data)
        elif format == 'json':
            return json.dumps(report_data, indent=2).encode()
        else:
            raise ValueError(f"Unsupported export format: {format}")
```

### Real-time Analytics Dashboard
Provide real-time analytics through API endpoints:

```python
# backend/app/api/endpoints/analytics.py
@router.get("/analytics/dashboard")
async def get_analytics_dashboard(
    time_period: str = "24h",
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get real-time analytics dashboard data."""
    
    dashboard_data = await analytics_service.get_dashboard_data(
        time_period=time_period,
        user_id=current_user['id']
    )
    
    return {
        'dashboard': dashboard_data,
        'last_updated': datetime.utcnow().isoformat(),
        'refresh_interval': 30  # seconds
    }

@router.get("/analytics/question/{question_id}/effectiveness")
async def get_question_effectiveness(
    question_id: str,
    time_period: str = "30d",
    current_user: dict = Depends(get_current_user),
    effectiveness_analyzer: QuestionEffectivenessAnalyzer = Depends(get_effectiveness_analyzer)
):
    """Get effectiveness analysis for a specific question."""
    
    # Check permissions
    if not await check_question_access(current_user['id'], question_id, 'read'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    effectiveness_data = await effectiveness_analyzer.analyze_question_effectiveness(
        question_id=question_id,
        time_period=time_period
    )
    
    return effectiveness_data

@router.get("/analytics/reports")
async def list_available_reports(
    current_user: dict = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service)
):
    """List available analytics reports."""
    
    reports = await report_service.list_available_reports(
        user_id=current_user['id']
    )
    
    return {'reports': reports}

@router.post("/analytics/reports/generate")
async def generate_analytics_report(
    report_request: ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    report_generator: QuestionAnalyticsReportGenerator = Depends(get_report_generator)
):
    """Generate analytics report."""
    
    # Start report generation in background
    task_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        generate_report_task,
        task_id,
        report_request,
        current_user['id'],
        report_generator
    )
    
    return {
        'task_id': task_id,
        'status': 'started',
        'estimated_completion': datetime.utcnow() + timedelta(minutes=5)
    }
```

## Machine Learning and Predictive Analytics

### Question Effectiveness Prediction
Use ML to predict question effectiveness:

```python
# backend/app/services/ml_analytics.py
class QuestionEffectivenessMLModel:
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.model = self._load_model()
        self.model_version = "1.0"
    
    async def predict_question_effectiveness(
        self,
        question_data: Dict[str, Any]
