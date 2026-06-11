#!/usr/bin/env python3
"""
Enhanced scraper mixins for consumer problem detection.

This module provides enhanced capabilities for detecting consumer problems
across social media platforms, with focus on:
- Consumer-specific pain point patterns
- Sentiment and emotion detection
- Engagement quality analysis
- Problem categorization
"""
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ConsumerPainSignal:
    """Represents a detected consumer pain signal."""
    pain_type: str  # e.g., 'financial', 'time', 'complexity', 'reliability'
    severity: int  # 1-10
    confidence: float  # 0-1
    evidence: str  # The text that triggered the detection
    category: str  # e.g., 'pricing', 'usability', 'support', 'features'


class ConsumerProblemDetectionMixin:
    """
    Mixin class providing enhanced consumer problem detection capabilities.
    
    Add this to any scraper to get consumer-focused pain point detection.
    """
    
    # Consumer-specific pain point patterns (financial, time, emotional)
    CONSUMER_PAIN_PATTERNS = {
        'financial': [
            r'(?:too|so) expensive',
            r'costs? too much',
            r'can\'t afford',
            r'wasting money',
            r'overpriced',
            r'not worth (?:the )?(?:money|price|cost)',
            r'charged? (?:me )?(?:too much|extra|unexpectedly)',
            r'hidden (?:fee|cost|charge)',
            r'(?:monthly|yearly) subscription',
            r'refund (?:issue|problem|denied)',
        ],
        'time_waste': [
            r'wastes? (?:so much )?time',
            r'takes? (?:too )?long',
            r'slow(?: as)?',
            r'hours? (?:to|of) (?:setup|configure|learn)',
            r'manual(?:ly)? (?:process|work|entry)',
            r'repetitive(?: task)?',
            r'(?:have to|must) (?:do|enter) (?:it|everything) (?:manually|by hand)',
            r'waiting (?:for|on)',
            r'delayed? (?:response|shipping|delivery)',
        ],
        'complexity': [
            r'(?:too )?complicated',
            r'(?:too )?complex',
            r'difficult (?:to|for)',
            r'hard (?:to|for)',
            r'confusing',
            r'overwhelming',
            r'steep learning curve',
            r'not intuitive',
            r'counterintuitive',
            r'(?:too )?many (?:steps|clicks|options)',
        ],
        'reliability': [
            r'(?:keeps?|always) (?:crashing|breaking|failing)',
            r'bugs?',
            r'glitch(?:y|es)?',
            r'not working',
            r'broken',
            r'error (?:message|code)?',
            r'won\'t (?:load|open|save|sync)',
            r'disappeared',
            r'lost (?:my|all) (?:data|work|progress)',
        ],
        'support': [
            r'no (?:response|answer|reply)',
            r'ignored',
            r'terrible (?:support|service)',
            r'customer service',
            r'no one (?:helps|responded)',
            r'chatbot (?:only|loop)',
            r'can\'t reach (?:support|anyone)',
        ],
        'emotional': [
            r'(?:so )?frustrated',
            r'(?:so )?annoyed',
            r'(?:really )?angry',
            r'hate (?:this|it|having to)',
            r'(?:so )?disappointed',
            r'regret (?:buying|purchasing|signing up)',
            r'worst (?:experience|purchase|decision)',
            r'nightmare',
            r'headache',
            r'stress(?:ful)?',
        ]
    }
    
    # Consumer problem categorization
    PROBLEM_CATEGORIES = {
        'pricing': ['expensive', 'cost', 'price', 'afford', 'money', 'cheap', 'value'],
        'usability': ['difficult', 'hard', 'complicated', 'confusing', 'intuitive', 'easy', 'simple'],
        'features': ['missing', 'need', 'want', 'feature', 'functionality', 'ability'],
        'reliability': ['crash', 'bug', 'broken', 'error', 'fail', 'work', 'stable'],
        'support': ['help', 'support', 'response', 'service', 'assist'],
        'integration': ['integrate', 'connect', 'sync', 'import', 'export', 'compatibility'],
    }
    
    def detect_consumer_pain_signals(self, text: str) -> List[ConsumerPainSignal]:
        """
        Detect consumer pain signals in text.
        
        Returns a list of pain signals with type, severity, and confidence.
        """
        if not text:
            return []
        
        signals = []
        text_lower = text.lower()
        
        for pain_type, patterns in self.CONSUMER_PAIN_PATTERNS.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
                for match in matches:
                    # Calculate severity based on intensity words
                    severity = self._calculate_severity(text_lower, match.start())
                    confidence = min(0.5 + (len(matches) * 0.1), 0.95)
                    
                    # Determine category
                    category = self._categorize_problem(match.group(0))
                    
                    signals.append(ConsumerPainSignal(
                        pain_type=pain_type,
                        severity=severity,
                        confidence=confidence,
                        evidence=match.group(0),
                        category=category
                    ))
        
        return signals
    
    def _calculate_severity(self, text: str, position: int) -> int:
        """Calculate severity based on intensity modifiers near the match."""
        intensity_words = {
            'very': 1, 'really': 1, 'extremely': 2, 'incredibly': 2,
            'so': 1, 'totally': 1, 'absolutely': 1, 'completely': 1,
            'slightly': -1, 'a bit': -1, 'kind of': -1, 'somewhat': -1
        }
        
        # Check context around the match (30 chars before)
        context_start = max(0, position - 30)
        context = text[context_start:position]
        
        severity = 5  # Base severity
        for word, adjustment in intensity_words.items():
            if word in context:
                severity += adjustment
        
        return max(1, min(10, severity))
    
    def _categorize_problem(self, evidence: str) -> str:
        """Categorize the problem based on evidence text."""
        evidence_lower = evidence.lower()
        
        category_scores = {}
        for category, keywords in self.PROBLEM_CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in evidence_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return 'general'
    
    def calculate_consumer_opportunity_score(self, post: Any) -> Tuple[float, Dict]:
        """
        Calculate opportunity score specifically for consumer problems.
        
        Returns (score, details) where score is 0-100.
        """
        text = f"{getattr(post, 'title', '')} {getattr(post, 'body', '')}"
        
        signals = self.detect_consumer_pain_signals(text)
        
        if not signals:
            return 0.0, {'reason': 'No consumer pain signals detected'}
        
        # Calculate weighted score
        total_severity = sum(s.severity for s in signals)
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        unique_categories = len(set(s.category for s in signals))
        
        # Factors:
        # - Number of signals (more = more validation)
        # - Average severity (higher = bigger problem)
        # - Confidence (higher = more certain)
        # - Category diversity (multiple categories = systemic issues)
        
        signal_score = min(len(signals) * 10, 30)  # Max 30 points
        severity_score = (total_severity / len(signals)) * 3  # Max ~30 points
        confidence_score = avg_confidence * 20  # Max 20 points
        diversity_score = unique_categories * 5  # Max ~20 points
        
        total_score = signal_score + severity_score + confidence_score + diversity_score
        
        details = {
            'signals_detected': len(signals),
            'unique_pain_types': list(set(s.pain_type for s in signals)),
            'categories': list(set(s.category for s in signals)),
            'avg_severity': total_severity / len(signals),
            'avg_confidence': avg_confidence,
            'top_signals': [
                {'type': s.pain_type, 'severity': s.severity, 'evidence': s.evidence}
                for s in sorted(signals, key=lambda x: x.severity, reverse=True)[:3]
            ]
        }
        
        return min(total_score, 100), details
    
    def extract_problem_summary(self, posts: List[Any]) -> Dict[str, Any]:
        """
        Extract a summary of problems from a list of posts.
        
        Useful for understanding the landscape of consumer problems
        across multiple posts.
        """
        all_signals = []
        category_counts = {}
        pain_type_counts = {}
        
        for post in posts:
            text = f"{getattr(post, 'title', '')} {getattr(post, 'body', '')}"
            signals = self.detect_consumer_pain_signals(text)
            all_signals.extend(signals)
            
            for signal in signals:
                category_counts[signal.category] = category_counts.get(signal.category, 0) + 1
                pain_type_counts[signal.pain_type] = pain_type_counts.get(signal.pain_type, 0) + 1
        
        return {
            'total_signals': len(all_signals),
            'posts_with_problems': len([p for p in posts if self.detect_consumer_pain_signals(
                f"{getattr(p, 'title', '')} {getattr(p, 'body', '')}"
            )]),
            'top_categories': sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'top_pain_types': sorted(pain_type_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'avg_severity': sum(s.severity for s in all_signals) / len(all_signals) if all_signals else 0,
        }


class EngagementQualityAnalyzer:
    """
    Analyzes engagement quality to identify high-intent consumer discussions.
    """
    
    # Reply patterns that indicate problem validation
    PROBLEM_VALIDATION_PATTERNS = [
        r'(?:same|happened to me|me too)',
        r'(?:also|too) (?:have|had|having) (?:this )?problem',
        r'agree',
        r'(?:can\'t|cannot) believe',
        r'should (?:fix|change|update)',
        r'hope (?:they|someone)',
    ]
    
    def analyze_discussion_quality(self, post: Any, replies: List[str] = None) -> Dict[str, Any]:
        """
        Analyze the quality of discussion around a post.
        
        High-quality discussions for SaaS ideas have:
        - Multiple people validating the problem
        - Suggestions or workarounds
        - Emotional resonance (frustration, agreement)
        """
        text = f"{getattr(post, 'title', '')} {getattr(post, 'body', '')}"
        
        analysis = {
            'has_problem_validation': False,
            'validation_count': 0,
            'has_workaround': False,
            'emotional_resonance': 0,
            'discussion_quality_score': 0,
        }
        
        if not replies:
            return analysis
        
        # Check for problem validation in replies
        for reply in replies:
            reply_lower = reply.lower()
            
            # Check validation patterns
            for pattern in self.PROBLEM_VALIDATION_PATTERNS:
                if re.search(pattern, reply_lower, re.IGNORECASE):
                    analysis['validation_count'] += 1
                    analysis['has_problem_validation'] = True
            
            # Check for workarounds/suggestions
            workaround_keywords = ['workaround', 'solution', 'fix', 'try', 'alternative', 'use']
            if any(kw in reply_lower for kw in workaround_keywords):
                analysis['has_workaround'] = True
            
            # Emotional resonance
            emotional_words = ['frustrating', 'annoying', 'hate', 'love', 'perfect', 'terrible']
            analysis['emotional_resonance'] += sum(1 for w in emotional_words if w in reply_lower)
        
        # Calculate overall discussion quality score
        analysis['discussion_quality_score'] = (
            (5 if analysis['has_problem_validation'] else 0) +
            min(analysis['validation_count'], 10) +
            (5 if analysis['has_workaround'] else 0) +
            min(analysis['emotional_resonance'], 5)
        )
        
        return analysis