"""
Content Analysis Service - Analyzes chapter content to score question relevance.
"""

import re
import string
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import Counter, defaultdict
import logging
import math

logger = logging.getLogger(__name__)


class ContentAnalysisService:
    """Service for analyzing chapter content and scoring question relevance."""
    
    def __init__(self):
        # Common stop words to filter out
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'this', 'that', 'these', 'those'
        }
        
        # Thematic keywords for different categories
        self.thematic_keywords = {
            'character': {
                'emotions': ['angry', 'sad', 'happy', 'afraid', 'love', 'hate', 'joy', 'fear', 'excited', 'nervous'],
                'relationships': ['friend', 'family', 'parent', 'child', 'sibling', 'spouse', 'partner', 'enemy'],
                'personality': ['brave', 'coward', 'kind', 'cruel', 'smart', 'foolish', 'honest', 'deceptive'],
                'actions': ['said', 'thought', 'felt', 'decided', 'chose', 'refused', 'agreed', 'argued']
            },
            'plot': {
                'events': ['happened', 'occurred', 'began', 'ended', 'started', 'finished', 'changed'],
                'conflict': ['problem', 'challenge', 'obstacle', 'difficulty', 'struggle', 'fight', 'battle'],
                'progression': ['then', 'next', 'after', 'before', 'meanwhile', 'suddenly', 'finally'],
                'tension': ['suspense', 'mystery', 'surprise', 'shock', 'reveal', 'discover', 'secret']
            },
            'setting': {
                'place': ['house', 'room', 'city', 'country', 'forest', 'mountain', 'ocean', 'street'],
                'time': ['morning', 'afternoon', 'evening', 'night', 'day', 'week', 'month', 'year'],
                'atmosphere': ['dark', 'bright', 'cold', 'warm', 'quiet', 'loud', 'peaceful', 'chaotic'],
                'sensory': ['saw', 'heard', 'felt', 'smelled', 'tasted', 'sound', 'sight', 'touch']
            },
            'theme': {
                'concepts': ['freedom', 'justice', 'truth', 'beauty', 'power', 'identity', 'belonging'],
                'values': ['right', 'wrong', 'good', 'evil', 'moral', 'ethical', 'principle', 'belief'],
                'growth': ['learn', 'understand', 'realize', 'discover', 'change', 'transform', 'mature'],
                'society': ['community', 'culture', 'tradition', 'society', 'civilization', 'human']
            }
        }
    
    def analyze_chapter_content(
        self,
        chapter_content: str,
        chapter_title: str = "",
        book_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze chapter content to extract themes, topics, and key elements.
        
        Args:
            chapter_content: The text content of the chapter
            chapter_title: Title of the chapter
            book_metadata: Optional metadata about the book
            
        Returns:
            Comprehensive analysis of the chapter content
        """
        if not chapter_content or len(chapter_content.strip()) < 50:
            return {
                'error': 'Insufficient content for analysis',
                'content_length': len(chapter_content),
                'analysis_possible': False
            }
        
        # Basic content metrics
        content_metrics = self._calculate_content_metrics(chapter_content)
        
        # Extract key terms and concepts
        key_terms = self._extract_key_terms(chapter_content)
        
        # Identify themes and topics
        thematic_analysis = self._analyze_themes(chapter_content, key_terms)
        
        # Analyze narrative elements
        narrative_elements = self._analyze_narrative_elements(chapter_content)
        
        # Generate content summary
        content_summary = self._generate_content_summary(
            content_metrics, key_terms, thematic_analysis, narrative_elements
        )
        
        # Analyze chapter focus
        chapter_focus = self._determine_chapter_focus(
            chapter_title, thematic_analysis, narrative_elements
        )
        
        return {
            'content_metrics': content_metrics,
            'key_terms': key_terms,
            'thematic_analysis': thematic_analysis,
            'narrative_elements': narrative_elements,
            'content_summary': content_summary,
            'chapter_focus': chapter_focus,
            'analysis_confidence': self._calculate_analysis_confidence(content_metrics, key_terms)
        }
    
    def score_question_relevance(
        self,
        question: Dict[str, Any],
        content_analysis: Dict[str, Any],
        chapter_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Score how relevant a question is to the chapter content.
        
        Args:
            question: Question dictionary with text and metadata
            content_analysis: Results from analyze_chapter_content
            chapter_context: Optional additional chapter context
            
        Returns:
            Relevance score and detailed breakdown
        """
        if content_analysis.get('error'):
            return {
                'relevance_score': 0.5,  # Neutral score when analysis not possible
                'confidence': 0.1,
                'reasoning': 'Unable to analyze content for relevance scoring'
            }
        
        question_text = question.get('question_text', '').lower()
        question_type = question.get('question_type', 'general')
        
        # Score different aspects of relevance
        scores = {}
        
        # 1. Keyword overlap score
        scores['keyword_overlap'] = self._score_keyword_overlap(
            question_text, content_analysis.get('key_terms', {})
        )
        
        # 2. Thematic alignment score
        scores['thematic_alignment'] = self._score_thematic_alignment(
            question_text, question_type, content_analysis.get('thematic_analysis', {})
        )
        
        # 3. Narrative element relevance
        scores['narrative_relevance'] = self._score_narrative_relevance(
            question_text, question_type, content_analysis.get('narrative_elements', {})
        )
        
        # 4. Chapter focus alignment
        scores['focus_alignment'] = self._score_focus_alignment(
            question_type, content_analysis.get('chapter_focus', {})
        )
        
        # 5. Content depth appropriateness
        scores['depth_appropriateness'] = self._score_depth_appropriateness(
            question, content_analysis.get('content_metrics', {})
        )
        
        # Calculate weighted overall score
        weights = {
            'keyword_overlap': 0.25,
            'thematic_alignment': 0.25,
            'narrative_relevance': 0.2,
            'focus_alignment': 0.15,
            'depth_appropriateness': 0.15
        }
        
        overall_score = sum(scores[key] * weights[key] for key in scores.keys())
        
        # Generate detailed reasoning
        reasoning = self._generate_relevance_reasoning(scores, question_type)
        
        # Calculate confidence in the scoring
        confidence = self._calculate_relevance_confidence(
            scores, content_analysis.get('analysis_confidence', 0.5)
        )
        
        return {
            'relevance_score': round(overall_score, 3),
            'confidence': round(confidence, 3),
            'component_scores': {k: round(v, 3) for k, v in scores.items()},
            'reasoning': reasoning,
            'recommendations': self._generate_relevance_recommendations(scores, overall_score)
        }
    
    def rank_questions_by_relevance(
        self,
        questions: List[Dict[str, Any]],
        content_analysis: Dict[str, Any],
        chapter_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank a list of questions by their relevance to the chapter content.
        
        Args:
            questions: List of questions to rank
            content_analysis: Content analysis results
            chapter_context: Optional chapter context
            
        Returns:
            Questions ranked by relevance score (highest first)
        """
        scored_questions = []
        
        for question in questions:
            relevance_analysis = self.score_question_relevance(
                question, content_analysis, chapter_context
            )
            
            # Add relevance information to question
            question_with_relevance = question.copy()
            question_with_relevance['relevance_analysis'] = relevance_analysis
            question_with_relevance['relevance_score'] = relevance_analysis['relevance_score']
            
            scored_questions.append(question_with_relevance)
        
        # Sort by relevance score (highest first)
        scored_questions.sort(key=lambda q: q['relevance_score'], reverse=True)
        
        return scored_questions
    
    def suggest_content_based_questions(
        self,
        content_analysis: Dict[str, Any],
        question_count: int = 5,
        focus_areas: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest questions based on content analysis.
        
        Args:
            content_analysis: Results from content analysis
            question_count: Number of questions to suggest
            focus_areas: Optional list of areas to focus on
            
        Returns:
            List of suggested questions with relevance scores
        """
        if content_analysis.get('error'):
            return []
        
        suggestions = []
        
        # Get chapter focus areas
        chapter_focus = content_analysis.get('chapter_focus', {})
        thematic_analysis = content_analysis.get('thematic_analysis', {})
        key_terms = content_analysis.get('key_terms', {})
        
        # Determine what to focus on
        if focus_areas:
            target_areas = focus_areas
        else:
            target_areas = list(chapter_focus.get('primary_elements', ['character', 'plot']))
        
        # Generate suggestions for each focus area
        for area in target_areas:
            area_suggestions = self._generate_area_specific_questions(
                area, thematic_analysis, key_terms, chapter_focus
            )
            suggestions.extend(area_suggestions)
        
        # Score suggestions for relevance
        scored_suggestions = []
        for suggestion in suggestions:
            relevance_analysis = self.score_question_relevance(
                suggestion, content_analysis
            )
            suggestion['relevance_analysis'] = relevance_analysis
            suggestion['relevance_score'] = relevance_analysis['relevance_score']
            scored_suggestions.append(suggestion)
        
        # Sort by relevance and return top results
        scored_suggestions.sort(key=lambda q: q['relevance_score'], reverse=True)
        
        return scored_suggestions[:question_count]
    
    def _calculate_content_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate basic metrics about the content."""
        # Clean content
        cleaned_content = re.sub(r'[^\w\s]', ' ', content.lower())
        words = cleaned_content.split()
        
        # Remove stop words for more meaningful analysis
        meaningful_words = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        # Calculate metrics
        metrics = {
            'total_words': len(words),
            'meaningful_words': len(meaningful_words),
            'unique_words': len(set(meaningful_words)),
            'avg_word_length': sum(len(w) for w in meaningful_words) / len(meaningful_words) if meaningful_words else 0,
            'sentences': len(re.split(r'[.!?]+', content)),
            'paragraphs': len([p for p in content.split('\n\n') if p.strip()]),
            'complexity_score': len(set(meaningful_words)) / len(meaningful_words) if meaningful_words else 0
        }
        
        return metrics
    
    def _extract_key_terms(self, content: str, top_n: int = 20) -> Dict[str, Any]:
        """Extract key terms and their frequencies from content."""
        # Clean and tokenize
        cleaned_content = re.sub(r'[^\w\s]', ' ', content.lower())
        words = cleaned_content.split()
        
        # Filter meaningful words
        meaningful_words = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        # Count word frequencies
        word_freq = Counter(meaningful_words)
        
        # Extract key terms (most frequent meaningful words)
        key_terms = dict(word_freq.most_common(top_n))
        
        # Extract potential proper nouns (capitalized words)
        proper_nouns = []
        for word in re.findall(r'\b[A-Z][a-z]+\b', content):
            if word not in ['The', 'A', 'An', 'This', 'That'] and len(word) > 2:
                proper_nouns.append(word)
        
        proper_noun_freq = Counter(proper_nouns)
        
        # Extract phrases (simple bigrams that appear multiple times)
        words_original_case = re.sub(r'[^\w\s]', ' ', content).split()
        bigrams = [f"{words_original_case[i]} {words_original_case[i+1]}" 
                  for i in range(len(words_original_case)-1)]
        bigram_freq = Counter(bigrams)
        significant_phrases = {phrase: count for phrase, count in bigram_freq.items() 
                              if count > 1 and len(phrase) > 5}
        
        return {
            'key_words': key_terms,
            'proper_nouns': dict(proper_noun_freq.most_common(10)),
            'key_phrases': dict(list(significant_phrases.items())[:10]),
            'total_unique_terms': len(set(meaningful_words))
        }
    
    def _analyze_themes(self, content: str, key_terms: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze thematic content of the chapter."""
        content_lower = content.lower()
        theme_scores = {}
        
        # Score each thematic category
        for main_theme, sub_themes in self.thematic_keywords.items():
            theme_score = 0
            theme_details = {}
            
            for sub_theme, keywords in sub_themes.items():
                # Count keyword occurrences
                keyword_count = sum(content_lower.count(keyword) for keyword in keywords)
                
                if keyword_count > 0:
                    theme_details[sub_theme] = keyword_count
                    theme_score += keyword_count
            
            if theme_score > 0:
                theme_scores[main_theme] = {
                    'total_score': theme_score,
                    'details': theme_details,
                    'prominence': min(1.0, theme_score / 20)  # Normalize to 0-1
                }
        
        # Identify dominant themes
        if theme_scores:
            dominant_theme = max(theme_scores.keys(), key=lambda k: theme_scores[k]['total_score'])
            secondary_themes = sorted([k for k in theme_scores.keys() if k != dominant_theme],
                                    key=lambda k: theme_scores[k]['total_score'], reverse=True)[:2]
        else:
            dominant_theme = None
            secondary_themes = []
        
        return {
            'theme_scores': theme_scores,
            'dominant_theme': dominant_theme,
            'secondary_themes': secondary_themes,
            'thematic_richness': len(theme_scores)
        }
    
    def _analyze_narrative_elements(self, content: str) -> Dict[str, Any]:
        """Analyze narrative elements present in the content."""
        content_lower = content.lower()
        
        elements = {
            'dialogue_present': bool(re.search(r'["\'].*["\']|said|asked|replied|answered', content)),
            'action_heavy': len(re.findall(r'\b(ran|jumped|fought|grabbed|threw|hit)\b', content_lower)) > 5,
            'descriptive_rich': len(re.findall(r'\b(beautiful|dark|bright|large|small|ancient|new)\b', content_lower)) > 10,
            'emotional_content': len(re.findall(r'\b(felt|emotion|angry|sad|happy|afraid|love|hate)\b', content_lower)) > 3,
            'conflict_present': bool(re.search(r'\b(conflict|problem|challenge|struggle|fight|argument)\b', content_lower)),
            'mystery_elements': bool(re.search(r'\b(secret|mystery|hidden|unknown|discover|reveal)\b', content_lower)),
            'time_references': len(re.findall(r'\b(yesterday|today|tomorrow|morning|evening|night|hour|minute)\b', content_lower)),
            'place_references': len(re.findall(r'\b(here|there|room|house|city|country|forest|mountain)\b', content_lower))
        }
        
        # Calculate narrative style indicators
        narrative_style = []
        if elements['dialogue_present']:
            narrative_style.append('dialogue-driven')
        if elements['action_heavy']:
            narrative_style.append('action-oriented')
        if elements['descriptive_rich']:
            narrative_style.append('descriptive')
        if elements['emotional_content']:
            narrative_style.append('emotional')
        
        elements['narrative_style'] = narrative_style
        elements['complexity_indicators'] = {
            'temporal_complexity': elements['time_references'] > 5,
            'spatial_complexity': elements['place_references'] > 5,
            'emotional_complexity': elements['emotional_content']
        }
        
        return elements
    
    def _generate_content_summary(
        self,
        content_metrics: Dict[str, Any],
        key_terms: Dict[str, Any],
        thematic_analysis: Dict[str, Any],
        narrative_elements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a summary of the content analysis."""
        summary = {
            'content_length': 'short' if content_metrics['total_words'] < 500 else 
                            'medium' if content_metrics['total_words'] < 2000 else 'long',
            'content_complexity': 'simple' if content_metrics['complexity_score'] < 0.3 else
                                'moderate' if content_metrics['complexity_score'] < 0.6 else 'complex',
            'primary_focus': thematic_analysis.get('dominant_theme', 'general'),
            'narrative_characteristics': narrative_elements.get('narrative_style', []),
            'key_concepts': list(key_terms.get('key_words', {}).keys())[:5],
            'analysis_depth': 'surface' if content_metrics['total_words'] < 200 else
                            'moderate' if content_metrics['total_words'] < 1000 else 'deep'
        }
        
        return summary
    
    def _determine_chapter_focus(
        self,
        chapter_title: str,
        thematic_analysis: Dict[str, Any],
        narrative_elements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine what the chapter primarily focuses on."""
        focus_scores = defaultdict(float)
        
        # Analyze title for clues
        if chapter_title:
            title_lower = chapter_title.lower()
            for theme in ['character', 'plot', 'setting', 'theme']:
                if any(keyword in title_lower for keyword in self.thematic_keywords.get(theme, {}).get('concepts', [])):
                    focus_scores[theme] += 0.3
        
        # Use thematic analysis
        theme_scores = thematic_analysis.get('theme_scores', {})
        for theme, score_data in theme_scores.items():
            focus_scores[theme] += score_data['prominence']
        
        # Use narrative elements
        if narrative_elements.get('dialogue_present'):
            focus_scores['character'] += 0.2
        if narrative_elements.get('action_heavy'):
            focus_scores['plot'] += 0.2
        if narrative_elements.get('descriptive_rich'):
            focus_scores['setting'] += 0.2
        if narrative_elements.get('emotional_content'):
            focus_scores['character'] += 0.1
            focus_scores['theme'] += 0.1
        
        # Determine primary and secondary focus
        if focus_scores:
            sorted_focus = sorted(focus_scores.items(), key=lambda x: x[1], reverse=True)
            primary_focus = sorted_focus[0][0] if sorted_focus else 'general'
            secondary_focus = [item[0] for item in sorted_focus[1:3] if item[1] > 0.1]
        else:
            primary_focus = 'general'
            secondary_focus = []
        
        return {
            'primary_focus': primary_focus,
            'secondary_focus': secondary_focus,
            'focus_scores': dict(focus_scores),
            'focus_strength': max(focus_scores.values()) if focus_scores else 0.0
        }
    
    def _calculate_analysis_confidence(
        self,
        content_metrics: Dict[str, Any],
        key_terms: Dict[str, Any]
    ) -> float:
        """Calculate confidence in the content analysis."""
        confidence = 0.0
        
        # Content length factor
        word_count = content_metrics.get('total_words', 0)
        if word_count > 1000:
            confidence += 0.4
        elif word_count > 500:
            confidence += 0.3
        elif word_count > 200:
            confidence += 0.2
        else:
            confidence += 0.1
        
        # Content complexity factor
        complexity = content_metrics.get('complexity_score', 0)
        confidence += min(0.3, complexity)
        
        # Key terms richness
        unique_terms = key_terms.get('total_unique_terms', 0)
        if unique_terms > 100:
            confidence += 0.3
        elif unique_terms > 50:
            confidence += 0.2
        else:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _score_keyword_overlap(self, question_text: str, key_terms: Dict[str, Any]) -> float:
        """Score overlap between question and content keywords."""
        question_words = set(re.findall(r'\b\w+\b', question_text.lower()))
        
        # Check overlap with key words
        key_words = set(key_terms.get('key_words', {}).keys())
        word_overlap = len(question_words.intersection(key_words))
        
        # Check overlap with proper nouns
        proper_nouns = set(term.lower() for term in key_terms.get('proper_nouns', {}).keys())
        noun_overlap = len(question_words.intersection(proper_nouns))
        
        # Check overlap with key phrases
        phrase_overlap = 0
        key_phrases = key_terms.get('key_phrases', {})
        for phrase in key_phrases:
            if phrase.lower() in question_text:
                phrase_overlap += 1
        
        # Calculate combined score
        max_possible_overlap = min(10, len(key_words) + len(proper_nouns))
        if max_possible_overlap == 0:
            return 0.5  # Neutral score when no key terms available
        
        overlap_score = (word_overlap + noun_overlap * 1.5 + phrase_overlap * 2) / max_possible_overlap
        return min(1.0, overlap_score)
    
    def _score_thematic_alignment(
        self,
        question_text: str,
        question_type: str,
        thematic_analysis: Dict[str, Any]
    ) -> float:
        """Score how well the question aligns with chapter themes."""
        theme_scores = thematic_analysis.get('theme_scores', {})
        
        if not theme_scores:
            return 0.5  # Neutral score when no themes identified
        
        # Get the prominence of the question's theme category
        question_theme_score = theme_scores.get(question_type, {}).get('prominence', 0)
        
        # Check if question contains thematic keywords
        question_lower = question_text.lower()
        thematic_keyword_count = 0
        
        if question_type in self.thematic_keywords:
            for sub_theme, keywords in self.thematic_keywords[question_type].items():
                thematic_keyword_count += sum(1 for keyword in keywords if keyword in question_lower)
        
        # Combine prominence and keyword scores
        alignment_score = (question_theme_score * 0.7) + (min(1.0, thematic_keyword_count / 3) * 0.3)
        
        return min(1.0, alignment_score)
    
    def _score_narrative_relevance(
        self,
        question_text: str,
        question_type: str,
        narrative_elements: Dict[str, Any]
    ) -> float:
        """Score relevance to narrative elements."""
        question_lower = question_text.lower()
        relevance_score = 0.0
        
        # Check relevance to narrative style
        narrative_style = narrative_elements.get('narrative_style', [])
        
        if question_type == 'character':
            if 'dialogue-driven' in narrative_style:
                relevance_score += 0.3
            if 'emotional' in narrative_style:
                relevance_score += 0.3
            if narrative_elements.get('dialogue_present'):
                relevance_score += 0.2
            if narrative_elements.get('emotional_content'):
                relevance_score += 0.2
        
        elif question_type == 'plot':
            if 'action-oriented' in narrative_style:
                relevance_score += 0.3
            if narrative_elements.get('action_heavy'):
                relevance_score += 0.2
            if narrative_elements.get('conflict_present'):
                relevance_score += 0.3
            if narrative_elements.get('mystery_elements'):
                relevance_score += 0.2
        
        elif question_type == 'setting':
            if 'descriptive' in narrative_style:
                relevance_score += 0.3
            if narrative_elements.get('descriptive_rich'):
                relevance_score += 0.3
            if narrative_elements.get('place_references', 0) > 3:
                relevance_score += 0.2
            if narrative_elements.get('time_references', 0) > 3:
                relevance_score += 0.2
        
        # General narrative element alignment
        element_keywords = {
            'dialogue': ['dialogue', 'conversation', 'speak', 'say', 'talk'],
            'action': ['action', 'event', 'happen', 'occur', 'do'],
            'description': ['describe', 'detail', 'appearance', 'look', 'scene'],
            'emotion': ['emotion', 'feel', 'mood', 'atmosphere', 'tone']
        }
        
        for element, keywords in element_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                if element in narrative_style or narrative_elements.get(f'{element}_present', False):
                    relevance_score += 0.1
        
        return min(1.0, relevance_score)
    
    def _score_focus_alignment(
        self,
        question_type: str,
        chapter_focus: Dict[str, Any]
    ) -> float:
        """Score alignment with chapter's primary focus."""
        primary_focus = chapter_focus.get('primary_focus', 'general')
        secondary_focus = chapter_focus.get('secondary_focus', [])
        focus_strength = chapter_focus.get('focus_strength', 0.0)
        
        alignment_score = 0.0
        
        # Primary focus alignment
        if question_type == primary_focus:
            alignment_score += 0.6 * focus_strength
        
        # Secondary focus alignment
        if question_type in secondary_focus:
            alignment_score += 0.3 * focus_strength
        
        # Base alignment for any recognized type
        if question_type in ['character', 'plot', 'setting', 'theme']:
            alignment_score += 0.1
        
        return min(1.0, alignment_score)
    
    def _score_depth_appropriateness(
        self,
        question: Dict[str, Any],
        content_metrics: Dict[
str, Any]
    ) -> float:
        """Score whether question depth is appropriate for content length/complexity."""
        question_text = question.get('question_text', '')
        question_difficulty = question.get('difficulty', 'medium')
        
        content_length = content_metrics.get('total_words', 0)
        content_complexity = content_metrics.get('complexity_score', 0)
        
        # Simple content should have simpler questions
        if content_length < 300:
            if question_difficulty == 'easy':
                return 1.0
            elif question_difficulty == 'medium':
                return 0.7
            else:
                return 0.4
        
        # Complex content can handle more complex questions
        elif content_length > 1000 and content_complexity > 0.5:
            if question_difficulty == 'hard':
                return 1.0
            elif question_difficulty == 'medium':
                return 0.8
            else:
                return 0.6
        
        # Medium content works well with medium questions
        else:
            if question_difficulty == 'medium':
                return 1.0
            else:
                return 0.7
    
    def _generate_relevance_reasoning(self, scores: Dict[str, float], question_type: str) -> str:
        """Generate human-readable reasoning for relevance score."""
        reasons = []
        
        if scores.get('keyword_overlap', 0) > 0.7:
            reasons.append("strong keyword overlap with content")
        elif scores.get('keyword_overlap', 0) > 0.4:
            reasons.append("moderate keyword overlap with content")
        
        if scores.get('thematic_alignment', 0) > 0.7:
            reasons.append(f"excellent alignment with {question_type} themes")
        elif scores.get('thematic_alignment', 0) > 0.4:
            reasons.append(f"good thematic alignment")
        
        if scores.get('narrative_relevance', 0) > 0.6:
            reasons.append("matches narrative style well")
        
        if scores.get('focus_alignment', 0) > 0.6:
            reasons.append("aligns with chapter's primary focus")
        
        if not reasons:
            reasons.append("limited alignment with chapter content")
        
        return "; ".join(reasons)
    
    def _calculate_relevance_confidence(
        self, 
        scores: Dict[str, float], 
        analysis_confidence: float
    ) -> float:
        """Calculate confidence in relevance scoring."""
        # Base confidence on analysis quality
        confidence = analysis_confidence * 0.6
        
        # Add confidence based on score consistency
        score_values = list(scores.values())
        if score_values:
            score_variance = sum((s - sum(score_values)/len(score_values))**2 for s in score_values) / len(score_values)
            consistency_bonus = max(0, 0.3 - score_variance)
            confidence += consistency_bonus
        
        # Add confidence if multiple scoring dimensions agree
        high_scores = sum(1 for score in score_values if score > 0.6)
        if high_scores >= 3:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_relevance_recommendations(
        self, 
        scores: Dict[str, float], 
        overall_score: float
    ) -> List[str]:
        """Generate recommendations for improving question relevance."""
        recommendations = []
        
        if overall_score < 0.4:
            recommendations.append("Consider revising question to better match chapter content")
        
        if scores.get('keyword_overlap', 0) < 0.3:
            recommendations.append("Include more specific terms from the chapter")
        
        if scores.get('thematic_alignment', 0) < 0.4:
            recommendations.append("Align question more closely with chapter themes")
        
        if scores.get('focus_alignment', 0) < 0.3:
            recommendations.append("Consider the chapter's primary focus area")
        
        if overall_score > 0.8:
            recommendations.append("Excellent relevance - use as a model")
        
        return recommendations
    
    def _generate_area_specific_questions(
        self,
        area: str,
        thematic_analysis: Dict[str, Any],
        key_terms: Dict[str, Any],
        chapter_focus: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate questions specific to a focus area."""
        questions = []
        
        # Get key terms for context
        key_words = list(key_terms.get('key_words', {}).keys())[:5]
        
        if area == 'character':
            templates = [
                "How do the characters in this chapter demonstrate {concept}?",
                "What motivates the main character's actions regarding {concept}?",
                "How do relationships between characters evolve around {concept}?",
                "What character traits are revealed through {concept}?"
            ]
        elif area == 'plot':
            templates = [
                "How does {concept} drive the plot forward in this chapter?",
                "What conflicts arise from {concept} in this chapter?",
                "How does {concept} create tension or resolution?",
                "What events in this chapter are influenced by {concept}?"
            ]
        elif area == 'setting':
            templates = [
                "How does the setting enhance {concept} in this chapter?",
                "What role does {concept} play in establishing atmosphere?",
                "How does the environment reflect {concept}?",
                "What sensory details support {concept} in this chapter?"
            ]
        elif area == 'theme':
            templates = [
                "What deeper meaning about {concept} emerges in this chapter?",
                "How does {concept} relate to the overall message of the story?",
                "What questions about {concept} does this chapter raise?",
                "How might readers interpret {concept} differently?"
            ]
        else:
            templates = [
                "How does {concept} function in this chapter?",
                "What role does {concept} play in the chapter's development?",
                "How does {concept} contribute to the reader's understanding?"
            ]
        
        # Generate questions using key terms
        for i, template in enumerate(templates[:3]):  # Limit to 3 per area
            if key_words and i < len(key_words):
                concept = key_words[i]
                question_text = template.format(concept=concept)
                
                questions.append({
                    'question_text': question_text,
                    'question_type': area,
                    'difficulty': 'medium',
                    'generated_from': 'content_analysis',
                    'focus_concept': concept
                })
        
        return questions


# Singleton instance
content_analysis_service = ContentAnalysisService()
