#!/usr/bin/env python3
"""
Consumer Pain Point Deep Dive Module

Provides specialized deep-dive capabilities for detecting consumer problems
across social media platforms. Focuses on:
- High-intent consumer complaint detection
- Problem validation through discussion analysis
- SaaS opportunity identification from consumer pain
- Competitive gap analysis
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConsumerProblem:
    """Represents a validated consumer problem."""
    problem_id: str
    platform: str
    source_url: str
    
    # Problem description
    title: str
    description: str
    
    # Categorization
    primary_category: str  # pricing, usability, reliability, support, features
    pain_types: List[str]  # financial, time_waste, complexity, emotional
    
    # Severity metrics
    severity_score: int  # 1-10
    frequency_indicators: List[str]  # e.g., "every day", "constantly", "always"
    impact_scope: str  # personal, team, business-wide
    
    # Validation metrics
    validation_signals: int  # Number of "me too" responses
    discussion_depth: int  # Number of replies/comments
    workaround_mentions: int  # People mentioning workarounds
    
    # Opportunity metrics
    willingness_to_pay_signals: List[str]
    current_solution_frustration: str
    proposed_solutions: List[str]
    
    # Metadata
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    author_info: Dict[str, Any] = field(default_factory=dict)
    related_posts: List[str] = field(default_factory=list)


class ConsumerDeepDiveAnalyzer:
    """
    Deep dive analyzer for consumer problems.
    
    Analyzes posts and discussions to extract validated consumer problems
    with SaaS opportunity potential.
    """
    
    # High-intent complaint indicators
    HIGH_INTENT_PATTERNS = {
        'willingness_to_pay': [
            r'(?:would|i\'d) pay (?:for|money|\$?\d+)(?:\s+(?:for|to))?',
            r'(?:happy|willing) to pay',
            r'take my money',
            r'shut up and take my money',
            r'how much (?:would|does) it cost',
            r'is there a paid version',
            r'premium version',
        ],
        'current_solution_fails': [
            r'currently using (?:.*?) but',
            r'switched from (?:.*?) because',
            r'tried (?:.*?) but(?: it)? (?:didn\'t|doesn\'t|wasn\'t|failed)',
            r'(?:excel|spreadsheet|manual|google sheets) (?:isn\'t|not) (?:working|cutting|enough)',
            r'outgrew (?:our|my) current',
        ],
        'actively_seeking': [
            r'looking for (?:a|an|the) (?:alternative|replacement|solution|tool|app)',
            r'any recommendations for',
            r'what (?:do you|are you) using (?:for|to)',
            r'switching from',
            r'migrating away from',
        ],
        'business_impact': [
            r'losing (?:money|revenue|customers?|time)',
            r'costing (?:me|us) (?:\$?\d+|money)',
            r'(?:every|each) (?:day|week|month) (?:this|it) (?:costs|wastes)',
            r'impact(?:ing|s)? (?:my|our) (?:business|revenue|bottom.line)',
        ]
    }
    
    # Problem validation patterns (indicates widespread issue)
    VALIDATION_PATTERNS = [
        r'^(?:same|same here|me too|me also)$',
        r'(?:happening|happens) to me too',
        r'(?:i|we) have (?:the )?same (?:problem|issue)',
        r'^(?:yes|yeah|yep),? (?:exactly|precisely|right)',
        r'(?:so|this) much (?:this|that|^$)',
        r'couldn\'t agree more',
        r'thank (?:god|goodness) (?:it\'s|someone said) (?:not )?just me',
    ]
    
    # Workaround indicators (people finding DIY solutions = opportunity)
    WORKAROUND_PATTERNS = [
        r'(?:my|our) workaround',
        r'(?:what|how) (?:i|we) do(?: it)?',
        r'(?:i|we) (?:just|usually|typically)',
        r'(?:temporary|hacky) (?:fix|solution)',
        r'(?:use|using) (?:excel|sheets|docs|notion|airtable) (?:to|for)',
        r'(?:built|created|made) (?:a|an|my own) (?:script|spreadsheet|tool)',
        r'(?:manual|hand) (?:process|workaround)',
    ]
    
    def __init__(self):
        self.problems_found = []
    
    def analyze_post_deep(self, post: Dict[str, Any], replies: List[str] = None) -> Optional[ConsumerProblem]:
        """
        Perform deep analysis on a single post to extract a validated consumer problem.
        
        Args:
            post: The post data
            replies: List of replies/comments to the post
            
        Returns:
            ConsumerProblem if a validated problem is found, None otherwise
        """
        text = f"{post.get('title', '')} {post.get('body', '')}"
        text_lower = text.lower()
        
        # Check for high-intent signals
        intent_signals = self._detect_intent_signals(text_lower)
        if not any(intent_signals.values()):
            return None  # No high-intent signals, skip
        
        # Analyze discussion for validation
        discussion_analysis = self._analyze_discussion(text_lower, replies or [])
        
        # Extract problem details
        title = post.get('title', '')[:100] or text[:100]
        description = self._extract_problem_description(text)
        
        # Categorize the problem
        category, pain_types = self._categorize_problem_deep(text_lower)
        
        # Calculate severity
        severity = self._calculate_severity_deep(text_lower, intent_signals, discussion_analysis)
        
        # Extract proposed solutions
        proposed_solutions = self._extract_proposed_solutions(replies or [])
        
        # Check for willingness to pay
        willingness_signals = self._extract_willingness_signals(text_lower, replies or [])
        
        # Create problem object
        problem = ConsumerProblem(
            problem_id=f"{post.get('platform', 'unknown')}_{post.get('id', 'unknown')}",
            platform=post.get('platform', 'unknown'),
            source_url=post.get('url', ''),
            title=title,
            description=description,
            primary_category=category,
            pain_types=pain_types,
            severity_score=severity,
            frequency_indicators=self._extract_frequency_indicators(text_lower),
            impact_scope=self._detect_impact_scope(text_lower),
            validation_signals=discussion_analysis['validation_count'],
            discussion_depth=discussion_analysis['total_replies'],
            workaround_mentions=discussion_analysis['workaround_count'],
            willingness_to_pay_signals=willingness_signals,
            current_solution_frustration=self._extract_current_solution_frustration(text_lower),
            proposed_solutions=proposed_solutions,
            author_info={
                'username': post.get('author', ''),
                'engagement': post.get('engagement', 0),
            }
        )
        
        return problem
    
    def _detect_intent_signals(self, text: str) -> Dict[str, int]:
        """Detect high-intent signals indicating a real problem."""
        signals = {}
        for signal_type, patterns in self.HIGH_INTENT_PATTERNS.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, text, re.IGNORECASE))
            signals[signal_type] = count
        return signals
    
    def _analyze_discussion(self, post_text: str, replies: List[str]) -> Dict[str, int]:
        """Analyze discussion for validation signals."""
        analysis = {
            'total_replies': len(replies),
            'validation_count': 0,
            'workaround_count': 0,
            'solution_suggestions': 0,
        }
        
        for reply in replies:
            reply_lower = reply.lower()
            
            # Check for validation
            for pattern in self.VALIDATION_PATTERNS:
                if re.search(pattern, reply_lower, re.IGNORECASE):
                    analysis['validation_count'] += 1
                    break
            
            # Check for workarounds
            for pattern in self.WORKAROUND_PATTERNS:
                if re.search(pattern, reply_lower, re.IGNORECASE):
                    analysis['workaround_count'] += 1
                    break
            
            # Check for solution suggestions
            solution_keywords = ['try', 'solution', 'fix', 'use', 'check out', 'recommend']
            if any(kw in reply_lower for kw in solution_keywords):
                analysis['solution_suggestions'] += 1
        
        return analysis
    
    def _extract_problem_description(self, text: str) -> str:
        """Extract a clean problem description from text."""
        # Find sentences that describe the problem
        sentences = re.split(r'[.!?]+', text)
        problem_sentences = []
        
        problem_indicators = ['wish', 'frustrated', 'annoying', 'difficult', 'problem', 
                             'issue', 'hate', 'tired', 'waste', 'expensive', 'broken']
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(ind in sentence.lower() for ind in problem_indicators):
                problem_sentences.append(sentence)
        
        description = '. '.join(problem_sentences[:2])
        return description[:300] if description else text[:200]
    
    def _categorize_problem_deep(self, text: str) -> Tuple[str, List[str]]:
        """Deep categorization of problem type."""
        pain_types = []
        
        # Detect pain types
        pain_keywords = {
            'financial': ['expensive', 'cost', 'money', 'price', 'afford', 'cheap', 'budget'],
            'time_waste': ['time', 'slow', 'long', 'wait', 'manual', 'hours', 'waste'],
            'complexity': ['complicated', 'complex', 'difficult', 'hard', 'confusing', 'learn'],
            'reliability': ['crash', 'bug', 'broken', 'error', 'fail', 'unreliable', 'glitch'],
            'emotional': ['frustrated', 'annoyed', 'angry', 'hate', 'disappointed', 'stress'],
        }
        
        for pain_type, keywords in pain_keywords.items():
            if any(kw in text for kw in keywords):
                pain_types.append(pain_type)
        
        # Primary category based on strongest signal
        category_scores = {
            'pricing': len(re.findall(r'expensive|cost|price|money|afford', text)),
            'usability': len(re.findall(r'difficult|hard|complicated|confusing|intuitive', text)),
            'reliability': len(re.findall(r'crash|bug|broken|error|fail|glitch', text)),
            'support': len(re.findall(r'support|service|help|response|reply', text)),
            'features': len(re.findall(r'feature|missing|need|want|functionality', text)),
        }
        
        primary = max(category_scores, key=category_scores.get)
        if category_scores[primary] == 0:
            primary = 'general'
        
        return primary, pain_types
    
    def _calculate_severity_deep(self, text: str, intent_signals: Dict, discussion: Dict) -> int:
        """Calculate comprehensive severity score."""
        base_severity = 5
        
        # Intent signals increase severity
        intent_score = sum(intent_signals.values()) * 0.5
        
        # Discussion validation increases severity
        validation_bonus = min(discussion['validation_count'] * 0.5, 3)
        
        # Workarounds indicate real problem
        workaround_bonus = min(discussion['workaround_count'] * 1, 2)
        
        # Emotional intensity
        emotional_words = ['hate', 'terrible', 'awful', 'nightmare', 'worst', 'extremely', 'very']
        emotional_count = sum(1 for w in emotional_words if w in text)
        emotional_bonus = min(emotional_count * 0.5, 2)
        
        total = base_severity + intent_score + validation_bonus + workaround_bonus + emotional_bonus
        return min(int(total), 10)
    
    def _extract_frequency_indicators(self, text: str) -> List[str]:
        """Extract indicators of problem frequency."""
        patterns = [
            r'every (?:day|week|month|time)',
            r'constantly',
            r'always',
            r'all the time',
            r'repeatedly',
            r'keeps? (?:happening|occurring)',
        ]
        
        indicators = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            indicators.extend(matches)
        
        return indicators[:3]
    
    def _detect_impact_scope(self, text: str) -> str:
        """Detect the scope of business impact."""
        if re.search(r'(?:my|our) (?:team|company|business|clients?|customers?)', text, re.IGNORECASE):
            return 'business-wide'
        elif re.search(r'(?:my|our) (?:workflow|process|work)', text, re.IGNORECASE):
            return 'workflow'
        return 'personal'
    
    def _extract_willingness_signals(self, post_text: str, replies: List[str]) -> List[str]:
        """Extract signals of willingness to pay."""
        all_text = post_text + ' ' + ' '.join(replies)
        signals = []
        
        for pattern in self.HIGH_INTENT_PATTERNS['willingness_to_pay']:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            signals.extend(matches)
        
        return signals[:3]
    
    def _extract_current_solution_frustration(self, text: str) -> str:
        """Extract mentions of current solution frustrations."""
        patterns = [
            r'(?:excel|spreadsheet|sheets|docs) (?:is|are|just)? (?:not|isn\'t) (?:cutting|working|enough)',
            r'currently (?:using|doing) (.*?) but',
            r'(?:tried|using) (.*?) (?:but|and) (?:it|they) (?:didn\'t|don\'t|failed)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)[:100]
        
        return ""
    
    def _extract_proposed_solutions(self, replies: List[str]) -> List[str]:
        """Extract solution suggestions from replies."""
        solutions = []
        
        for reply in replies:
            # Look for "try X" or "use X" or "check out X"
            patterns = [
                r'(?:try|use|check out|look into|consider) (?:using)? ([^.]+?)(?:\.|,|for|to)',
                r'(?:recommend|suggest) (?:using|trying)? ([^.]+?)(?:\.|,)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, reply, re.IGNORECASE)
                solutions.extend([m.strip()[:50] for m in matches])
        
        return list(set(solutions))[:5]  # Deduplicate and limit
    
    def generate_opportunity_report(self, problems: List[ConsumerProblem]) -> Dict[str, Any]:
        """
        Generate a comprehensive SaaS opportunity report from analyzed problems.
        
        Returns:
            Dictionary with opportunity analysis
        """
        if not problems:
            return {"error": "No problems analyzed"}
        
        # Category breakdown
        category_counts = {}
        pain_type_counts = {}
        severity_distribution = []
        
        for problem in problems:
            category_counts[problem.primary_category] = category_counts.get(problem.primary_category, 0) + 1
            for pt in problem.pain_types:
                pain_type_counts[pt] = pain_type_counts.get(pt, 0) + 1
            severity_distribution.append(problem.severity_score)
        
        # High-value problems (severity >= 7 with validation)
        high_value = [p for p in problems if p.severity_score >= 7 and p.validation_signals >= 2]
        
        # Willingness to pay indicators
        willingness_count = sum(1 for p in problems if p.willingness_to_pay_signals)
        
        # Workaround indicators (DIY solutions = opportunity)
        workaround_count = sum(1 for p in problems if p.workaround_mentions > 0)
        
        return {
            'total_problems_analyzed': len(problems),
            'high_value_problems': len(high_value),
            'category_breakdown': dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)),
            'pain_type_distribution': dict(sorted(pain_type_counts.items(), key=lambda x: x[1], reverse=True)),
            'avg_severity': sum(severity_distribution) / len(severity_distribution) if severity_distribution else 0,
            'willingness_to_pay_indicators': willingness_count,
            'workaround_indicators': workaround_count,
            'top_opportunities': [
                {
                    'title': p.title[:80],
                    'category': p.primary_category,
                    'severity': p.severity_score,
                    'platform': p.platform,
                    'url': p.source_url
                }
                for p in sorted(high_value, key=lambda x: x.severity_score, reverse=True)[:10]
            ]
        }