# Question Security Measures and Content Safety Features

## Overview
The question generation system implements comprehensive security measures and content safety features to protect users and ensure appropriate content. This document covers authentication, authorization, content filtering, data protection, and safety mechanisms.

## Authentication and Authorization

### User Authentication
Secure user access to question functionality:

```python
# backend/app/core/auth.py
class QuestionAuthService:
    def __init__(self):
        self.jwt_handler = JWTHandler()
        self.session_manager = SessionManager()
    
    async def authenticate_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate user for question access."""
        try:
            # Verify JWT token
            payload = self.jwt_handler.decode_token(token)
            
            # Check token expiration
            if payload['exp'] < time.time():
                raise AuthenticationError("Token expired")
            
            # Verify user exists and is active
            user = await self.get_user_by_id(payload['user_id'])
            if not user or not user.get('is_active'):
                raise AuthenticationError("User not found or inactive")
            
            # Check for suspicious activity
            if await self.check_suspicious_activity(user['id']):
                raise AuthenticationError("Account temporarily locked")
            
            return user
            
        except (JWTDecodeError, KeyError, ValueError) as e:
            raise AuthenticationError("Invalid token")
    
    async def check_suspicious_activity(self, user_id: str) -> bool:
        """Check for suspicious user activity."""
        recent_activities = await self.get_recent_activities(user_id, hours=1)
        
        # Check for rapid-fire requests
        if len(recent_activities) > 100:  # 100 requests per hour
            await self.log_security_event(user_id, "RATE_LIMIT_EXCEEDED")
            return True
        
        # Check for unusual patterns
        if await self.detect_unusual_patterns(recent_activities):
            await self.log_security_event(user_id, "UNUSUAL_ACTIVITY")
            return True
        
        return False
```

### Resource Authorization
Control access to questions and related resources:

```python
# backend/app/services/question_authorization.py
class QuestionAuthorizationService:
    def __init__(self):
        self.permissions = {
            'owner': ['read', 'write', 'delete', 'share'],
            'collaborator': ['read', 'write'],
            'viewer': ['read'],
            'guest': []
        }
    
    async def check_question_access(
        self,
        user_id: str,
        question_id: str,
        required_permission: str
    ) -> bool:
        """Check if user has permission to access a question."""
        
        # Get question details
        question = await self.get_question_by_id(question_id)
        if not question:
            return False
        
        # Get user's role for this book
        user_role = await self.get_user_book_role(user_id, question['book_id'])
        
        # Check if user has required permission
        user_permissions = self.permissions.get(user_role, [])
        
        if required_permission not in user_permissions:
            await self.log_access_denied(user_id, question_id, required_permission)
            return False
        
        # Additional checks for sensitive operations
        if required_permission == 'delete':
            return await self.check_delete_permission(user_id, question)
        
        return True
    
    async def check_bulk_operation_permission(
        self,
        user_id: str,
        question_ids: List[str],
        operation: str
    ) -> Dict[str, bool]:
        """Check permissions for bulk operations."""
        results = {}
        
        for question_id in question_ids:
            try:
                has_permission = await self.check_question_access(
                    user_id, question_id, operation
                )
                results[question_id] = has_permission
            except Exception as e:
                logger.warning(f"Permission check failed for {question_id}: {str(e)}")
                results[question_id] = False
        
        # Log bulk operation attempt
        await self.log_bulk_operation(user_id, operation, results)
        
        return results
```

## Content Safety and Filtering

### Content Validation Pipeline
Multi-layered content validation for questions and responses:

```python
# backend/app/services/content_safety.py
class ContentSafetyService:
    def __init__(self):
        self.profanity_filter = ProfanityFilter()
        self.toxicity_detector = ToxicityDetector()
        self.content_classifier = ContentClassifier()
        self.moderation_queue = ModerationQueue()
    
    async def validate_question_content(self, question_text: str) -> ContentValidationResult:
        """Comprehensive content validation for questions."""
        
        result = ContentValidationResult()
        
        # Stage 1: Basic text validation
        basic_validation = await self._basic_text_validation(question_text)
        result.add_validation_step('basic', basic_validation)
        
        if not basic_validation.passed:
            return result
        
        # Stage 2: Profanity detection
        profanity_check = await self.profanity_filter.check_content(question_text)
        result.add_validation_step('profanity', profanity_check)
        
        if profanity_check.severity > ContentSeverity.LOW:
            await self.handle_inappropriate_content(question_text, 'profanity', profanity_check)
            return result
        
        # Stage 3: Toxicity detection
        toxicity_check = await self.toxicity_detector.analyze(question_text)
        result.add_validation_step('toxicity', toxicity_check)
        
        if toxicity_check.score > 0.7:  # High toxicity threshold
            await self.handle_inappropriate_content(question_text, 'toxicity', toxicity_check)
            return result
        
        # Stage 4: Content classification
        classification = await self.content_classifier.classify(question_text)
        result.add_validation_step('classification', classification)
        
        # Check for inappropriate categories
        blocked_categories = ['adult', 'violence', 'harassment', 'illegal']
        if any(cat in classification.categories for cat in blocked_categories):
            await self.handle_inappropriate_content(question_text, 'classification', classification)
            return result
        
        # Stage 5: Context appropriateness
        context_check = await self._check_context_appropriateness(question_text)
        result.add_validation_step('context', context_check)
        
        result.overall_passed = all(step.passed for step in result.validation_steps.values())
        
        return result
    
    async def _basic_text_validation(self, text: str) -> ValidationStep:
        """Basic text validation checks."""
        issues = []
        
        # Length checks
        if len(text.strip()) < 10:
            issues.append("Text too short")
        elif len(text) > 2000:
            issues.append("Text too long")
        
        # Character validation
        if not re.search(r'\?', text):
            issues.append("Questions should end with a question mark")
        
        # Suspicious patterns
        if re.search(r'http[s]?://', text):
            issues.append("URLs not allowed in questions")
        
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):  # SSN pattern
            issues.append("Personal information detected")
        
        return ValidationStep(
            passed=len(issues) == 0,
            issues=issues,
            severity=ContentSeverity.HIGH if issues else ContentSeverity.NONE
        )
    
    async def handle_inappropriate_content(
        self,
        content: str,
        violation_type: str,
        details: Any
    ):
        """Handle detection of inappropriate content."""
        
        # Log the violation
        await self.log_content_violation(
            content=content[:100],  # First 100 chars only
            violation_type=violation_type,
            details=details,
            timestamp=datetime.utcnow()
        )
        
        # Add to moderation queue for review
        await self.moderation_queue.add_item({
            'content_hash': hashlib.sha256(content.encode()).hexdigest(),
            'violation_type': violation_type,
            'severity': details.severity if hasattr(details, 'severity') else 'medium',
            'requires_human_review': True
        })
        
        # Update user safety score
        await self.update_user_safety_score(violation_type)
```

### AI-Generated Content Filtering
Special filtering for AI-generated questions:

```python
# backend/app/services/ai_content_filter.py
class AIContentFilter:
    def __init__(self):
        self.bias_detector = BiasDetector()
        self.coherence_checker = CoherenceChecker()
        self.quality_assessor = QualityAssessor()
    
    async def filter_ai_generated_questions(
        self,
        questions: List[Dict],
        context: Dict[str, Any]
    ) -> List[Dict]:
        """Filter and validate AI-generated questions."""
        
        filtered_questions = []
        
        for question in questions:
            try:
                # Check for bias in question content
                bias_check = await self.bias_detector.analyze(
                    question['question_text'],
                    context.get('book_genre'),
                    context.get('target_audience')
                )
                
                if bias_check.has_bias:
                    await self.log_bias_detection(question, bias_check)
                    continue
                
                # Check question coherence
                coherence_score = await self.coherence_checker.score(
                    question['question_text'],
                    context.get('chapter_content', '')
                )
                
                if coherence_score < 0.6:  # Minimum coherence threshold
                    await self.log_coherence_issue(question, coherence_score)
                    continue
                
                # Assess overall quality
                quality_score = await self.quality_assessor.evaluate(question)
                
                if quality_score < 0.5:  # Minimum quality threshold
                    await self.log_quality_issue(question, quality_score)
                    continue
                
                # Add safety metadata
                question['safety_metadata'] = {
                    'bias_score': bias_check.score,
                    'coherence_score': coherence_score,
                    'quality_score': quality_score,
                    'filtered_at': datetime.utcnow().isoformat(),
                    'filter_version': '1.0'
                }
                
                filtered_questions.append(question)
                
            except Exception as e:
                logger.error(f"Error filtering question: {str(e)}")
                # Err on the side of caution - exclude questionable content
                continue
        
        return filtered_questions
```

## Data Protection and Privacy

### Personal Information Protection
Prevent exposure of personal information in questions:

```python
# backend/app/services/privacy_protection.py
class PrivacyProtectionService:
    def __init__(self):
        self.pii_detector = PIIDetector()
        self.data_anonymizer = DataAnonymizer()
        self.encryption_service = EncryptionService()
    
    async def protect_question_data(self, question_data: Dict) -> Dict:
        """Protect personal information in question data."""
        
        protected_data = question_data.copy()
        
        # Scan for PII in question text
        pii_results = await self.pii_detector.scan(protected_data.get('question_text', ''))
        
        if pii_results.found_pii:
            # Anonymize detected PII
            protected_data['question_text'] = await self.data_anonymizer.anonymize(
                protected_data['question_text'],
                pii_results.detected_types
            )
            
            # Log PII detection for compliance
            await self.log_pii_detection(question_data['id'], pii_results)
        
        # Encrypt sensitive metadata
        if 'user_metadata' in protected_data:
            protected_data['user_metadata'] = await self.encryption_service.encrypt(
                json.dumps(protected_data['user_metadata'])
            )
        
        # Remove or hash identifying information
        if 'user_ip' in protected_data:
            protected_data['user_ip_hash'] = hashlib.sha256(
                protected_data['user_ip'].encode()
            ).hexdigest()
            del protected_data['user_ip']
        
        return protected_data
    
    async def sanitize_user_response(self, response_text: str) -> str:
        """Sanitize user responses to remove PII."""
        
        # Common PII patterns
        pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        }
        
        sanitized_text = response_text
        replacements_made = []
        
        for pii_type, pattern in pii_patterns.items():
            matches = re.findall(pattern, sanitized_text)
            if matches:
                for match in matches:
                    # Replace with placeholder
                    placeholder = f"[{pii_type.upper()}_REMOVED]"
                    sanitized_text = sanitized_text.replace(match, placeholder)
                    replacements_made.append((pii_type, match[:4] + "..."))
        
        # Log sanitization if PII was found
        if replacements_made:
            await self.log_pii_sanitization(replacements_made)
        
        return sanitized_text
```

### Data Encryption and Storage
Secure storage of sensitive question data:

```python
# backend/app/services/secure_storage.py
class SecureQuestionStorage:
    def __init__(self):
        self.encryption_key = self._load_encryption_key()
        self.crypto = Fernet(self.encryption_key)
        self.audit_logger = AuditLogger()
    
    async def store_sensitive_question_data(
        self,
        question_id: str,
        sensitive_data: Dict,
        user_id: str
    ) -> str:
        """Securely store sensitive question data."""
        
        try:
            # Encrypt the data
            encrypted_data = self.crypto.encrypt(
                json.dumps(sensitive_data).encode()
            )
            
            # Store with metadata
            storage_record = {
                'question_id': question_id,
                'encrypted_data': encrypted_data,
                'user_id': user_id,
                'encryption_version': '1.0',
                'created_at': datetime.utcnow(),
                'access_count': 0
            }
            
            record_id = await self.database.insert_secure_record(storage_record)
            
            # Audit log
            await self.audit_logger.log_data_storage(
                user_id=user_id,
                question_id=question_id,
                record_id=record_id,
                data_type='sensitive_question_data'
            )
            
            return record_id
            
        except Exception as e:
            await self.audit_logger.log_storage_error(
                user_id=user_id,
                question_id=question_id,
                error=str(e)
            )
            raise StorageError("Failed to store sensitive data securely")
    
    async def retrieve_sensitive_question_data(
        self,
        record_id: str,
        user_id: str,
        question_id: str
    ) -> Dict:
        """Securely retrieve sensitive question data."""
        
        # Verify access permissions
        if not await self.verify_access_permission(user_id, record_id):
            raise AccessDeniedError("Insufficient permissions")
        
        try:
            # Get encrypted record
            record = await self.database.get_secure_record(record_id)
            
            if not record or record['user_id'] != user_id:
                raise AccessDeniedError("Record not found or access denied")
            
            # Decrypt data
            decrypted_data = self.crypto.decrypt(record['encrypted_data'])
            sensitive_data = json.loads(decrypted_data.decode())
            
            # Update access count
            await self.database.increment_access_count(record_id)
            
            # Audit log
            await self.audit_logger.log_data_access(
                user_id=user_id,
                question_id=question_id,
                record_id=record_id
            )
            
            return sensitive_data
            
        except Exception as e:
            await self.audit_logger.log_access_error(
                user_id=user_id,
                question_id=question_id,
                record_id=record_id,
                error=str(e)
            )
            raise RetrievalError("Failed to retrieve sensitive data")
```

## Input Validation and Sanitization

### Comprehensive Input Validation
Validate all user inputs to prevent injection attacks:

```python
# backend/app/services/input_validation.py
class InputValidationService:
    def __init__(self):
        self.validators = {
            'question_text': self._validate_question_text,
            'response_text': self._validate_response_text,
            'metadata': self._validate_metadata,
            'search_query': self._validate_search_query
        }
    
    async def validate_question_input(self, data: Dict) -> ValidationResult:
        """Validate question-related input data."""
        
        result = ValidationResult()
        
        for field, value in data.items():
            if field in self.validators:
                validator = self.validators[field]
                field_result = await validator(value)
                result.add_field_result(field, field_result)
        
        # Cross-field validation
        if result.is_valid:
            cross_validation = await self._cross_field_validation(data)
            result.add_cross_validation(cross_validation)
        
        return result
    
    async def _validate_question_text(self, text: str) -> FieldValidationResult:
        """Validate question text input."""
        errors = []
        warnings = []
        
        # Length validation
        if len(text.strip()) < 10:
            errors.append("Question text must be at least 10 characters")
        elif len(text) > 1000:
            errors.append("Question text cannot exceed 1000 characters")
        
        # HTML/Script injection prevention
        if re.search(r'<[^>]*script[^>]*>', text, re.IGNORECASE):
            errors.append("Script tags are not allowed")
        
        if re.search(r'<[^>]*>.*</[^>]*>', text):
            warnings.append("HTML tags detected and will be removed")
            # Sanitize HTML
            text = self._sanitize_html(text)
        
        # SQL injection prevention
        sql_patterns = [
            r'\bUNION\b.*\bSELECT\b',
            r'\bDROP\b.*\bTABLE\b',
            r'\bINSERT\b.*\bINTO\b',
            r'\bDELETE\b.*\bFROM\b'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append("Suspicious SQL pattern detected")
                break
        
        # NoSQL injection prevention
        nosql_patterns = [r'\$where', r'\$ne', r'\$or', r'\$and']
        for pattern in nosql_patterns:
            if pattern in text:
                errors.append("Suspicious NoSQL pattern detected")
                break
        
        return FieldValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=text,
            errors=errors,
            warnings=warnings
        )
    
    def _sanitize_html(self, text: str) -> str:
        """Sanitize HTML content while preserving safe formatting."""
        # Allow only safe tags
        allowed_tags = ['p', 'br', 'strong', 'em', 'u']
        
        # Use bleach library for safe HTML sanitization
        import bleach
        
        sanitized = bleach.clean(
            text,
            tags=allowed_tags,
            attributes={},
            strip=True
        )
        
        return sanitized
```

## Rate Limiting and Abuse Prevention

### Advanced Rate Limiting
Implement sophisticated rate limiting to prevent abuse:

```python
# backend/app/services/rate_limiting.py
class QuestionRateLimiter:
    def __init__(self):
        self.redis_client = redis.Redis()
        self.limits = {
            'question_generation': {
                'requests_per_minute': 10,
                'requests_per_hour': 100,
                'requests_per_day': 500
            },
            'question_response': {
                'requests_per_minute': 50,
                'requests_per_hour': 1000,
                'requests_per_day': 5000
            },
            'question_rating': {
                'requests_per_minute': 30,
                'requests_per_hour': 500,
                'requests_per_day': 2000
            }
        }
    
    async def check_rate_limit(
        self,
        user_id: str,
        operation: str,
        ip_address: str = None
    ) -> RateLimitResult:
        """Check if user/IP is within rate limits."""
        
        if operation not in self.limits:
            return RateLimitResult(allowed=True)
        
        limits = self.limits[operation]
        
        # Check user-based limits
        user_result = await self._check_user_limits(user_id, operation, limits)
        if not user_result.allowed:
            return user_result
        
        # Check IP-based limits (if IP provided)
        if ip_address:
            ip_result = await self._check_ip_limits(ip_address, operation, limits)
            if not ip_result.allowed:
                return ip_result
        
        # Check for burst detection
        burst_result = await self._check_burst_pattern(user_id, operation)
        if not burst_result.allowed:
            return burst_result
        
        # Record the request
        await self._record_request(user_id, operation, ip_address)
        
        return RateLimitResult(allowed=True)
    
    async def _check_user_limits(
        self,
        user_id: str,
        operation: str,
        limits: Dict
    ) -> RateLimitResult:
        """Check user-specific rate limits."""
        
        for period, limit in limits.items():
            period_seconds = self._period_to_seconds(period)
            key = f"rate_limit:user:{user_id}:{operation}:{period}"
            
            current_count = await self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            if current_count >= limit:
                reset_time = await self.redis_client.ttl(key)
                return RateLimitResult(
                    allowed=False,
                    reason=f"User rate limit exceeded for {period}",
                    reset_in_seconds=reset_time,
                    current_count=current_count,
                    limit=limit
                )
        
        return RateLimitResult(allowed=True)
    
    async def _check_burst_pattern(
        self,
        user_id: str,
        operation: str
    ) -> RateLimitResult:
        """Detect and prevent burst patterns."""
        
        # Get recent request timestamps
        key = f"burst_detection:{user_id}:{operation}"
        recent_requests = await self.redis_client.lrange(key, 0, -1)
        
        if len(recent_requests) < 5:
            return RateLimitResult(allowed=True)
        
        # Check if too many requests in short time
        now = time.time()
        recent_timestamps = [float(ts) for ts in recent_requests[-5:]]
        
        # If last 5 requests were within 10 seconds, it's a burst
        if now - min(recent_timestamps) < 10:
            await self._apply_burst_penalty(user_id, operation)
            return RateLimitResult(
                allowed=False,
                reason="Burst pattern detected",
                reset_in_seconds=300  # 5 minute penalty
            )
        
        return RateLimitResult(allowed=True)
```

## Security Monitoring and Alerting

### Real-time Security Monitoring
Monitor for security threats and suspicious activity:

```python
# backend/app/services/security_monitoring.py
class SecurityMonitoringService:
    def __init__(self):
        self.alert_manager = AlertManager()
        self.threat_detector = ThreatDetector()
        self.metrics_collector = MetricsCollector()
    
    async def monitor_question_activity(
        self,
        user_id: str,
        action: str,
        context: Dict
    ):
        """Monitor question-related activity for security threats."""
        
        # Collect activity metrics
        await self.metrics_collector.record_activity(
            user_id=user_id,
            action=action,
            timestamp=datetime.utcnow(),
            context=context
        )
        
        # Check for suspicious patterns
        threats = await self.threat_detector.analyze_activity(
            user_id=user_id,
            action=action,
            context=context
        )
        
        for threat in threats:
            await self._handle_security_threat(threat, user_id, context)
    
    async def _handle_security_threat(
        self,
        threat: SecurityThreat,
        user_id: str,
        context: Dict
    ):
        """Handle detected security threats."""
        
        # Log the threat
        await self.log_security_threat(threat, user_id, context)
        
        # Take appropriate action based on threat level
        if threat.severity == ThreatSeverity.CRITICAL:
            # Immediate account suspension
            await self.suspend_user_account(user_id, threat.description)
            
            # Send immediate alert
            await self.alert_manager.send_critical_alert(
                threat_type=threat.type,
                user_id=user_id,
                description=threat.description
            )
        
        elif threat.severity == ThreatSeverity.HIGH:
            # Temporary restrictions
            await self.apply_temporary_restrictions(user_id, threat.type)
            
            # Send high priority alert
            await self.alert_manager.send_high_priority_alert(threat)
        
        elif threat.severity == ThreatSeverity.MEDIUM:
            # Increased monitoring
            await self.increase_monitoring_level(user_id)
            
            # Log for review
            await self.queue_for_manual_review(threat, user_id)
    
    async def generate_security_report(
        self,
        time_period: str = '24h'
    ) -> Dict[str, Any]:
        """Generate security monitoring report."""
        
        report = {
            'time_period': time_period,
            'generated_at': datetime.utcnow().isoformat(),
            'metrics': {}
        }
        
        # Threat statistics
        threats = await self.get_threats_in_period(time_period)
        report['metrics']['threats'] = {
            'total': len(threats),
            'by_severity': self._group_threats_by_severity(threats),
            'by_type': self._group_threats_by_type(threats)
        }
        
        # User activity statistics
        activities = await self.get_activities_in_period(time_period)
        report['metrics']['activities'] = {
            'total_activities': len(activities),
            'unique_users': len(set(a['user_id'] for a in activities)),
            'by_action': self._group_activities_by_action(activities)
        }
        
        # Content safety statistics
        content_issues = await self.get_content_issues_in_period(time_period)
        report['metrics']['content_safety'] = {
            'total_issues': len(content_issues),
            'by_type': self._group_content_issues_by_type(content_issues)
        }
        
        return report
```

## Compliance and Audit

### GDPR Compliance
Ensure GDPR compliance for question data:

```python
# backend/app/services/gdpr_compliance.py
class GDPRComplianceService:
    def __init__(self):
        self.data_processor = PersonalDataProcessor()
        self.consent_manager = ConsentManager()
        self.audit_logger = AuditLogger()
    
    async def handle_data_subject_request(
        self,
        request_type: str,
        user_id: str,
        details: Dict
    ) -> Dict[str, Any]:
        """Handle GDPR data subject requests."""
        
        request_id = str(uuid.uuid4())
        
        await self.audit_logger.log_gdpr_request(
            request_id=request_id,
            request_type=request_type,
            user_id=user_id,
            details=details
        )
        
        if request_type == 'access':
            return await self._handle_access_request(user_id, request_id)
        elif request_type == 'portability':
            return await self._handle_portability_request(user_id, request_id)
        elif request_type == 'erasure':
            return await self._handle_erasure_request(user_id, request_id)
        elif request_type == 'rectification':
            return await self._handle_rectification_request(user_id, details, request_id)
        else:
            raise ValueError(f"Unsupported request type: {request_type}")
    
    async def _handle_erasure_request(
        self,
        user_id: str,
        request_id: str
    ) -> Dict[str, Any]:
        """Handle right to erasure (right to be forgotten)."""
