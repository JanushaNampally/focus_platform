"""
NLP Sentiment Analysis Engine for YouTube Comments

Purpose:
- Analyze YouTube comments for teaching quality indicators
- Extract sentiment scores using transformer models
- Identify quality keywords ("best explanation", "confusing")
- Update video teaching_quality_score based on comment analysis

Model: DistilBERT fine-tuned for sentiment analysis
- Accuracy: ~94% on benchmark datasets
- Speed: ~100 comments/sec on CPU
- Framework: HuggingFace transformers
"""

import numpy as np
import logging
import re
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger('ai_engine')


class CommentSentimentAnalyzer:
    """
    NLP-based YouTube comment analysis for video quality assessment
    
    Uses HuggingFace DistilBERT for sentiment classification
    Extracts teaching quality from keyword patterns
    """
    
    # Pre-trained sentiment model (lazy loaded)
    _SENTIMENT_MODEL = None
    
    # Keywords indicating teaching quality
    QUALITY_KEYWORDS = {
        'teaching_quality': [
            'best explanation', 'crystal clear', 'so clear', 'perfectly explained',
            'understood finally', 'great teacher', 'finally understood',
            'brilliant explanation', 'finally got it', 'excellently explained',
            'wonderful teaching', 'makes sense now', 'best i found',
            'helped me a lot', 'thank you for explaining'
        ],
        'clarity': [
            'confusing', 'unclear', 'lost me', 'too fast', 'too slow',
            'hard to follow', 'missing steps', 'complicated', 'difficult to understand',
            'confusing part', 'not clear', 'confused me', 'lost track'
        ],
        'criticism': [
            'could improve', 'needs work', 'should clarify', 'better if',
            'more detail needed', 'more examples', 'explain more', 'too brief',
            'rushed through', 'need explanation'
        ],
        'ineffective': [
            'waste of time', 'useless', 'bad explanation', 'boring',
            'not helpful', 'skip this', 'poor quality', 'don\'t watch',
            'complete waste', 'terrible'
        ]
    }
    
    def __init__(self):
        """Initialize sentiment analyzer with transformer model"""
        self._load_model()
    
    @classmethod
    def _load_model(cls):
        """Lazy load sentiment model (only once)"""
        if cls._SENTIMENT_MODEL is not None:
            return
        
        try:
            from transformers import pipeline
            logger.info("Loading DistilBERT sentiment model...")
            
            cls._SENTIMENT_MODEL = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                framework="pt",
                device=-1  # CPU (use 0 for GPU if CUDA available)
            )
            logger.info("Sentiment model loaded successfully")
        except ImportError:
            logger.warning(
                "transformers not installed. Install with: "
                "pip install transformers torch"
            )
            cls._SENTIMENT_MODEL = None
    
    def analyze_comment(self, comment_text: str) -> Dict[str, any]:
        """
        Analyze a single comment for sentiment and quality indicators
        
        Args:
            comment_text: Raw YouTube comment string
        
        Returns:
            Dict with sentiment, sentiment_score, quality indicators
        """
        
        if not comment_text or len(comment_text.strip()) < 3:
            return {
                'sentiment': 'NEUTRAL',
                'sentiment_score': 0.5,
                'teaching_quality': False,
                'clarity_feedback': False,
                'criticism': False,
                'ineffective': False,
                'text_length': len(comment_text)
            }
        
        result = {
            'sentiment': 'NEUTRAL',
            'sentiment_score': 0.5,
            'teaching_quality': False,
            'clarity_feedback': False,
            'criticism': False,
            'ineffective': False,
            'text_length': len(comment_text)
        }
        
        comment_lower = comment_text.lower()
        
        # Get sentiment from NLP model
        if self._SENTIMENT_MODEL is not None:
            try:
                predictions = self._SENTIMENT_MODEL(
                    comment_text[:512],  # Truncate to model max length
                    truncation=True
                )
                
                if predictions:
                    pred = predictions[0]
                    label = pred['label']  # "POSITIVE" or "NEGATIVE"
                    score = pred['score']  # 0-1 confidence
                    
                    # Convert to 0-1 sentiment scale
                    if label == 'POSITIVE':
                        result['sentiment'] = 'POSITIVE'
                        result['sentiment_score'] = score
                    else:
                        result['sentiment'] = 'NEGATIVE'
                        result['sentiment_score'] = 1 - score
                        
            except Exception as e:
                logger.error(f"NLP sentiment error: {str(e)}")
                result['sentiment_score'] = 0.5
        
        # Quality keyword detection (regex-based, case-insensitive)
        if any(kw in comment_lower for kw in self.QUALITY_KEYWORDS['teaching_quality']):
            result['teaching_quality'] = True
        
        if any(kw in comment_lower for kw in self.QUALITY_KEYWORDS['clarity']):
            result['clarity_feedback'] = True
        
        if any(kw in comment_lower for kw in self.QUALITY_KEYWORDS['criticism']):
            result['criticism'] = True
        
        if any(kw in comment_lower for kw in self.QUALITY_KEYWORDS['ineffective']):
            result['ineffective'] = True
        
        return result
    
    def batch_analyze_comments(
        self,
        comment_texts: List[str],
        batch_size: int = 32
    ) -> Dict[str, any]:
        """
        Batch analyze multiple comments efficiently
        
        Args:
            comment_texts: List of comment strings
            batch_size: Process comments in batches of N
        
        Returns:
            Aggregated sentiment statistics
        """
        
        if not comment_texts:
            logger.warning("No comments to analyze")
            return self._empty_batch_result()
        
        results = {
            'individual_results': [],
            'aggregate': {
                'total_comments': len(comment_texts),
                'avg_sentiment_score': 0.0,
                'positive_ratio': 0.0,
                'negative_ratio': 0.0,
                'neutral_ratio': 0.0,
                'teaching_quality_count': 0,
                'clarity_issues_count': 0,
                'criticism_count': 0,
                'ineffective_count': 0,
                'teaching_quality_ratio': 0.0,
            },
            'quality_score': 0.0
        }
        
        sentiment_scores = []
        sentiment_dist = {'POSITIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0}
        
        # Process in batches
        for i in range(0, len(comment_texts), batch_size):
            batch = comment_texts[i:i+batch_size]
            
            for comment in batch:
                analysis = self.analyze_comment(comment)
                results['individual_results'].append(analysis)
                
                # Track statistics
                sentiment_scores.append(analysis['sentiment_score'])
                sentiment_dist[analysis['sentiment']] += 1
                
                if analysis['teaching_quality']:
                    results['aggregate']['teaching_quality_count'] += 1
                if analysis['clarity_feedback']:
                    results['aggregate']['clarity_issues_count'] += 1
                if analysis['criticism']:
                    results['aggregate']['criticism_count'] += 1
                if analysis['ineffective']:
                    results['aggregate']['ineffective_count'] += 1
        
        # Calculate aggregates
        n = len(comment_texts)
        if n > 0:
            results['aggregate']['avg_sentiment_score'] = np.mean(sentiment_scores)
            results['aggregate']['positive_ratio'] = sentiment_dist['POSITIVE'] / n
            results['aggregate']['negative_ratio'] = sentiment_dist['NEGATIVE'] / n
            results['aggregate']['neutral_ratio'] = sentiment_dist['NEUTRAL'] / n
            results['aggregate']['teaching_quality_ratio'] = \
                results['aggregate']['teaching_quality_count'] / n
        
        # Calculate overall quality score (0-100)
        # Factors:
        # - High positive ratio (40%)
        # - High teaching quality mentions (40%)
        # - Low ineffective mentions (20%)
        quality_components = [
            results['aggregate']['positive_ratio'] * 40,
            results['aggregate']['teaching_quality_ratio'] * 40,
            max(0, (1 - results['aggregate']['ineffective_count'] / max(1, n)) * 20)
        ]
        results['quality_score'] = sum(quality_components)
        
        logger.info(
            f"Analyzed {n} comments - Avg sentiment: "
            f"{results['aggregate']['avg_sentiment_score']:.2f}, "
            f"Quality: {results['quality_score']:.1f}/100"
        )
        
        return results
    
    def extract_teaching_indicators(self, comment_text: str) -> Dict[str, any]:
        """
        Extract teaching-specific quality indicators from comment
        
        Returns: Dict with extracted metadata about teaching effectiveness
        """
        
        comment_lower = comment_text.lower()
        
        indicators = {
            'is_positive_teaching': False,
            'is_negative_teaching': False,
            'difficulty_too_high': False,
            'difficulty_too_low': False,
            'pacing_too_fast': False,
            'pacing_too_slow': False,
            'examples_provided': False,
            'solved_doubt': False,
            'confusing_section': False,
        }
        
        # Positive teaching indicators
        if any(kw in comment_lower for kw in [
            'best explanation', 'great teacher', 'brilliant',
            'clear', 'understood', 'finally got it', 'help'
        ]):
            indicators['is_positive_teaching'] = True
        
        # Negative teaching indicators
        if any(kw in comment_lower for kw in [
            'confusing', 'unclear', 'bad', 'waste', 'useless',
            'boring', 'poor'
        ]):
            indicators['is_negative_teaching'] = True
        
        # Difficulty assessment
        if any(kw in comment_lower for kw in [
            'too advanced', 'too hard', 'beyond me', 'complicated'
        ]):
            indicators['difficulty_too_high'] = True
        
        if any(kw in comment_lower for kw in [
            'too easy', 'too simple', 'already knew', 'basic stuff'
        ]):
            indicators['difficulty_too_low'] = True
        
        # Pacing assessment
        if any(kw in comment_lower for kw in [
            'too fast', 'rushed', 'hurried', 'quickly'
        ]):
            indicators['pacing_too_fast'] = True
        
        if any(kw in comment_lower for kw in [
            'too slow', 'dragging', 'boring', 'long-winded'
        ]):
            indicators['pacing_too_slow'] = True
        
        # Learning outcomes
        if any(kw in comment_lower for kw in [
            'example', 'solved', 'helped me', 'finally understand'
        ]):
            indicators['solved_doubt'] = True
        
        return indicators
    
    def _empty_batch_result(self) -> Dict[str, any]:
        """Return empty result structure"""
        return {
            'individual_results': [],
            'aggregate': {
                'total_comments': 0,
                'avg_sentiment_score': 0.0,
                'positive_ratio': 0.0,
                'negative_ratio': 0.0,
                'neutral_ratio': 0.0,
                'teaching_quality_count': 0,
                'clarity_issues_count': 0,
                'criticism_count': 0,
                'ineffective_count': 0,
                'teaching_quality_ratio': 0.0,
            },
            'quality_score': 0.0
        }


# Global singleton instance
_analyzer_instance = None


def get_sentiment_analyzer() -> CommentSentimentAnalyzer:
    """Get or create global sentiment analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = CommentSentimentAnalyzer()
    return _analyzer_instance

