#!/usr/bin/env python3
"""
Pain point detection, sentiment analysis, and opportunity scoring algorithms.

Provides comprehensive text analysis for identifying SaaS opportunities from Reddit content.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from collections import Counter

from scripts.utils import ScrapedPost, ScrapedComment, VelocityMetrics, CompetitorMention, OpportunitySignal


# =============================================================================
# HIGH-INTENT PATTERN MATCHING
# =============================================================================

HIGH_INTENT_PATTERNS = [
    # Purchase intent
    (r"is there an app for\s+(.+?)(?:\?|$)", "app_request", 90),
    (r"is there a tool for\s+(.+?)(?:\?|$)", "tool_request", 90),
    (r"(?:looking for|need)\s+(?:an?|some)\s+(?:app|tool|software|platform)\s+(?:for|to)\s+(.+?)(?:\?|$)", "tool_request", 85),
    (r"would pay for\s+(.+?)(?:\.|$)", "payment_willingness", 95),
    (r"(?:i'd|i would)\s+pay\s+(?:for|money|if)\s+(.+?)(?:\.|$)", "payment_willingness", 95),
    
    # Problem expression
    (r"i hate it when\s+(.+?)(?:\.|$)", "pain_expression", 80),
    (r"(?:frustrated|annoyed|irritated)\s+(?:with|by|that)\s+(.+?)(?:\.|$)", "pain_expression", 75),
    (r"(?:tired of|sick of)\s+(.+?)(?:\.|$)", "pain_expression", 70),
    (r"(?:struggling|having trouble)\s+(?:with|to)\s+(.+?)(?:\.|$)", "pain_expression", 75),
    
    # Alternative seeking
    (r"(?:alternative|replacement)\s+(?:to|for)\s+(\w+)", "alternative_seeking", 85),
    (r"(?:switching|migrating)\s+(?:from|away from)\s+(\w+)", "alternative_seeking", 85),
    (r"(?:quitting|leaving)\s+(\w+)", "churn_signal", 90),
    (r"(?:not|stopped)\s+(?:using|paying for)\s+(\w+)", "churn_signal", 85),
    
    # Why hasn't anyone built
    (r"why (?:hasn't|has not|doesn't|does not)\s+(?:someone|anyone)\s+(?:built|created|made)\s+(.+?)(?:\?|$)", "opportunity_gap", 95),
    (r"someone should\s+(?:build|create|make)\s+(.+?)(?:\.|$)", "opportunity_gap", 90),
    (r"(?:startup|business)\s+(?:idea|opportunity)\s*[:-]?\s*(.+?)(?:\.|$)", "opportunity_gap", 80),
    
    # Manual process pain
    (r"(?:doing|managing)\s+(.+?)\s+(?:manually|by hand|in excel|in sheets)", "manual_process", 85),
    (r"(?:spending|wasting)\s+(?:hours|time)\s+(.+?)(?:\.|$)", "time_waste", 80),
    (r"(?:spreadsheet|excel)\s+(?:hell|nightmare|mess)", "tool_limitation", 85),
    
    # Feature requests
    (r"i wish\s+(\w+)\s+(?:would|had|could)\s+(.+?)(?:\.|$)", "feature_request", 70),
    (r"(?:missing|need)\s+(?:a|the)\s+feature\s+(?:to|for)\s+(.+?)(?:\.|$)", "feature_request", 75),
    
    # Price sensitivity
    (r"why is\s+(\w+)\s+so\s+(expensive|pricey|costly)", "price_pain", 80),
    (r"(?:too expensive|overpriced|can't afford)\s+(\w+)", "price_pain", 85),
    (r"(?:cheaper|affordable)\s+(?:alternative|option)\s+(?:to|for)\s+(\w+)", "price_pain", 80),
]


# =============================================================================
# FRUSTRATION LEXICON
# =============================================================================

FRUSTRATION_KEYWORDS = {
    "extreme": [
        "infuriating", "rage", "hate", "worst", "nightmare", "disaster",
        "unusable", "impossible", "broken", "terrible", "awful", "horrible"
    ],
    "high": [
        "frustrated", "annoyed", "irritated", "angry", "mad", "furious",
        "painful", "difficult", "complicated", "confusing", "stressful"
    ],
    "medium": [
        "difficult", "problem", "issue", "struggling", "trouble", "challenge",
        "annoying", "inconvenient", "bothersome", "tedious"
    ],
    "low": [
        "wish", "hope", "would be nice", "it'd be great", "ideally",
        "prefer", "rather", "suggestion"
    ],
}

INTENSIFIERS = ["very", "extremely", "incredibly", "absolutely", "totally", "really", "so", "too"]
NEGATIONS = ["not", "no", "never", "neither", "nor", "hardly", "barely", "scarcely", "doesn't", "don't", "didn't", "isn't", "aren't"]


# =============================================================================
# COMPETITOR PATTERNS
# =============================================================================

COMPETITOR_PATTERNS = [
    (r"(?:using|on)\s+(\w+)\s+(?:for|to)", "direct_usage"),
    (r"(?:compared? to|vs\.?|versus)\s+(\w+)", "comparison"),
    (r"(?:alternative|replacement)\s+(?:to|for)\s+(\w+)", "alternative"),
    (r"(?:better than|worse than)\s+(\w+)", "comparison"),
    (r"(?:switched|migrated)\s+(?:from|to)\s+(\w+)", "migration"),
    (r"(?:quitting|leaving)\s+(\w+)", "churn"),
    (r"(?:hate|love)\s+(\w+)", "sentiment"),
]


# =============================================================================
# AGREEMENT INDICATORS
# =============================================================================

AGREEMENT_PATTERNS = [
    r"\bi agree\b",
    r"\bme too\b",
    r"\bsame here\b",
    r"\bexactly\b",
    r"\bthis\s*^.?\s*(?:so much|100%|true)",
    r"\bcame here to say this\b",
    r"\byou(?:'re|r) right\b",
    r"\bcouldn't agree more\b",
    r"\bsame (?:problem|issue|situation)\b",
    r"\bhappens? to me too\b",
    r"\bi have the same\b",
    r"\bfacing the same\b",
]


# =============================================================================
# TECH STACK KEYWORDS
# =============================================================================

TECH_KEYWORDS = {
    "python": ["python", "django", "flask", "fastapi", "pandas", "numpy"],
    "javascript": ["javascript", "typescript", "node", "react", "vue", "angular", "nextjs"],
    "nocode": ["zapier", "make", "airtable", "notion", "bubble", "webflow", "softer"],
    "api": ["api", "integration", "webhook", "rest", "graphql"],
    "database": ["sql", "postgres", "mongodb", "database", "db"],
    "cloud": ["aws", "gcp", "azure", "cloud", "serverless"],
    "mobile": ["ios", "android", "flutter", "react native", "mobile app"],
}


# =============================================================================
# MONETIZATION SIGNALS
# =============================================================================

MONETIZATION_SIGNALS = [
    (r"\$[\d,]+(?:\.\d{2})?", "dollar_amount"),
    (r"\bdollar\b", "currency_mention"),
    (r"\bbudget\b", "budget_mention"),
    (r"\bpricing\b", "pricing_mention"),
    (r"\benterprise\b", "enterprise_context"),
    (r"\bworth (?:it|paying)\b", "value_acknowledgment"),
    (r"\bwould pay\b", "payment_willingness"),
    (r"\bcosts? (?:too )?much\b", "price_sensitivity"),
    (r"\bexpensive\b", "price_sensitivity"),
    (r"\baffordable\b", "price_conscious"),
    (r"\b(?:roi|return on investment)\b", "business_context"),
]


class OpportunityAnalyzer:
    """Analyzes Reddit content for SaaS opportunities."""
    
    def __init__(self):
        self.high_intent_patterns = HIGH_INTENT_PATTERNS
        self.frustration_keywords = FRUSTRATION_KEYWORDS
        
    def analyze_post(self, post: ScrapedPost) -> Dict[str, Any]:
        """
        Comprehensive analysis of a post.
        
        Returns dict with:
        - intent_signals
        - frustration_score
        - monetization_indicators
        - tech_stack_hints
        - problem_statement
        """
        text = f"{post.title} {post.body}".lower()
        
        # Extract intent signals
        intent_signals = self._extract_intent_signals(text)
        
        # Calculate frustration score
        frustration_score = self._calculate_frustration_score(text)
        
        # Detect monetization indicators
        monetization_indicators = self._detect_monetization_signals(text)
        
        # Infer tech stack
        tech_stack = self._infer_tech_stack(text)
        
        # Extract problem statement
        problem_statement = self._extract_problem_statement(text, intent_signals)
        
        return {
            "intent_signals": intent_signals,
            "frustration_score": frustration_score,
            "monetization_indicators": monetization_indicators,
            "tech_stack_hints": tech_stack,
            "problem_statement": problem_statement,
        }
    
    def _extract_intent_signals(self, text: str) -> List[Dict[str, Any]]:
        """Extract high-intent patterns from text."""
        signals = []
        
        for pattern, signal_type, base_score in self.high_intent_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract captured group if present
                capture = match.group(1) if match.groups() else ""
                
                # Adjust score based on context
                score = self._adjust_intent_score(text, match, base_score)
                
                signals.append({
                    "type": signal_type,
                    "pattern": pattern,
                    "match": match.group(0),
                    "capture": capture,
                    "score": score,
                    "position": match.start()
                })
        
        # Sort by score descending
        signals.sort(key=lambda x: x["score"], reverse=True)
        return signals
    
    def _adjust_intent_score(self, text: str, match: re.Match, base_score: int) -> int:
        """Adjust intent score based on context."""
        score = base_score
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end]
        
        # Check for negation
        words_before = text[start:match.start()].split()
        if any(neg in words_before[-3:] for neg in NEGATIONS):
            score -= 40  # Significant penalty for negation
        
        # Check for intensifiers
        if any(intens in context for intens in INTENSIFIERS):
            score += 10
        
        # Check for urgency words
        urgency_words = ["urgent", "asap", "immediately", "desperate", "critical"]
        if any(word in context for word in urgency_words):
            score += 15
        
        return max(0, min(100, score))
    
    def _calculate_frustration_score(self, text: str) -> float:
        """
        Calculate frustration/aggravation score (0-100).
        
        Uses lexicon-based approach with negation and intensifier handling.
        """
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        score = 0
        matched_keywords = []
        
        for i, word in enumerate(words):
            # Check against frustration lexicon
            for level, keywords in self.frustration_keywords.items():
                if word in keywords:
                    base_score = {
                        "extreme": 40,
                        "high": 25,
                        "medium": 15,
                        "low": 5
                    }[level]
                    
                    # Check for intensifiers in previous 3 words
                    context_start = max(0, i - 3)
                    context = words[context_start:i]
                    intensifier_count = sum(1 for w in context if w in INTENSIFIERS)
                    base_score += intensifier_count * 5
                    
                    # Check for negation
                    if any(w in NEGATIONS for w in context):
                        base_score = base_score * 0.3  # Reduce impact
                    
                    score += base_score
                    matched_keywords.append((word, level))
        
        # Normalize to 0-100
        return min(100, score)
    
    def _detect_monetization_signals(self, text: str) -> Dict[str, Any]:
        """Detect signals of willingness to pay."""
        text_lower = text.lower()
        
        signals = []
        for pattern, signal_type in MONETIZATION_SIGNALS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                signals.append({
                    "type": signal_type,
                    "match": match.group(0)
                })
        
        # Calculate score
        score = min(100, len(signals) * 15)
        
        # Bonus for explicit payment willingness
        if any(s["type"] == "payment_willingness" for s in signals):
            score += 30
        
        return {
            "score": min(100, score),
            "signals": signals,
            "count": len(signals)
        }
    
    def _infer_tech_stack(self, text: str) -> List[str]:
        """Infer suggested tech stack from context."""
        text_lower = text.lower()
        detected = []
        
        for category, keywords in TECH_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected.append(category)
                    break
        
        return detected
    
    def _extract_problem_statement(self, text: str, intent_signals: List[Dict]) -> str:
        """Extract a clean problem statement from the text."""
        if not intent_signals:
            # Fallback: extract sentences with pain keywords
            pain_sentences = []
            for level, keywords in self.frustration_keywords.items():
                for keyword in keywords:
                    pattern = rf"[^.]*\b{keyword}\b[^.]*\."
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    pain_sentences.extend(matches)
            
            if pain_sentences:
                return pain_sentences[0].strip()[:200]
            return text[:200]
        
        # Use highest scoring signal
        top_signal = intent_signals[0]
        capture = top_signal.get("capture", "")
        
        if capture:
            return capture.strip()[:200]
        
        return top_signal["match"][:200]
    
    def calculate_velocity_metrics(self, post: ScrapedPost) -> VelocityMetrics:
        """Calculate engagement velocity for a post."""
        import time
        
        try:
            created_utc = float(post.created_at)
        except (ValueError, TypeError):
            created_utc = time.time() - 86400  # Default to 1 day old
        
        hours_since_post = (time.time() - created_utc) / 3600
        hours_since_post = max(0.5, hours_since_post)  # Avoid division by zero
        
        upvotes_per_hour = post.engagement / hours_since_post
        comments_per_hour = post.comments_count / hours_since_post
        
        # High comment-to-upvote ratio often indicates controversy/pain
        engagement_ratio = post.comments_count / max(1, post.engagement)
        
        # Simple acceleration estimation (would need historical data for true calc)
        acceleration = 0.0
        
        # Viral probability based on engagement rate
        viral_probability = min(100, (upvotes_per_hour * 10) + (comments_per_hour * 20))
        
        return VelocityMetrics(
            upvotes_per_hour=round(upvotes_per_hour, 2),
            comments_per_hour=round(comments_per_hour, 2),
            engagement_ratio=round(engagement_ratio, 3),
            acceleration=round(acceleration, 3),
            viral_probability=round(viral_probability, 1),
            time_since_post=round(hours_since_post, 1)
        )
    
    def extract_competitor_mentions(
        self,
        text: str,
        known_competitors: Optional[List[str]] = None
    ) -> List[CompetitorMention]:
        """
        Extract competitor mentions from text.
        
        Args:
            text: Text to analyze
            known_competitors: List of competitor brand names to look for
        """
        text_lower = text.lower()
        mentions = []
        
        # Search for known competitors
        if known_competitors:
            for competitor in known_competitors:
                competitor_lower = competitor.lower()
                if competitor_lower in text_lower:
                    # Find context
                    idx = text_lower.find(competitor_lower)
                    start = max(0, idx - 100)
                    end = min(len(text), idx + 100)
                    context = text[start:end]
                    
                    # Determine mention type and sentiment
                    mention_type, sentiment, intent = self._analyze_competitor_context(
                        context, competitor_lower
                    )
                    
                    mentions.append(CompetitorMention(
                        brand_name=competitor,
                        mention_type=mention_type,
                        context=context,
                        sentiment=sentiment,
                        intent=intent
                    ))
        
        # Also search for pattern-based mentions
        for pattern, mention_type in COMPETITOR_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                brand = match.group(1)
                if brand and len(brand) > 2:  # Filter short matches
                    context_start = max(0, match.start() - 100)
                    context_end = min(len(text), match.end() + 100)
                    context = text[context_start:context_end]
                    
                    sentiment, intent = self._analyze_competitor_sentiment(context)
                    
                    mentions.append(CompetitorMention(
                        brand_name=brand.capitalize(),
                        mention_type=mention_type,
                        context=context,
                        sentiment=sentiment,
                        intent=intent
                    ))
        
        return mentions
    
    def _analyze_competitor_context(
        self,
        context: str,
        competitor: str
    ) -> Tuple[str, float, str]:
        """Analyze context around competitor mention."""
        context_lower = context.lower()
        
        # Determine mention type
        if any(word in context_lower for word in ["alternative", "replacement", "instead"]):
            mention_type = "alternative"
        elif any(word in context_lower for word in ["switch", "migrate", "moving"]):
            mention_type = "migration"
        elif any(word in context_lower for word in ["vs", "versus", "compared", "better", "worse"]):
            mention_type = "comparison"
        elif any(word in context_lower for word in ["quit", "leaving", "stopped"]):
            mention_type = "churn"
        else:
            mention_type = "direct"
        
        # Analyze sentiment
        sentiment = self._analyze_competitor_sentiment(context)[0]
        
        # Determine intent
        if any(word in context_lower for word in ["looking for", "recommend", "suggestion"]):
            intent = "researching"
        elif mention_type == "churn":
            intent = "switching"
        elif sentiment < 0:
            intent = "complaining"
        else:
            intent = "praising"
        
        return mention_type, sentiment, intent
    
    def _analyze_competitor_sentiment(self, context: str) -> Tuple[float, str]:
        """Analyze sentiment in competitor context."""
        context_lower = context.lower()
        
        positive = ["love", "great", "awesome", "best", "good", "like", "enjoy", "recommend"]
        negative = ["hate", "terrible", "awful", "worst", "bad", "suck", "horrible", "frustrating"]
        
        pos_count = sum(1 for word in positive if word in context_lower)
        neg_count = sum(1 for word in negative if word in context_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0, "neutral"
        
        sentiment = (pos_count - neg_count) / total
        
        if sentiment > 0.3:
            return sentiment, "praising"
        elif sentiment < -0.3:
            return sentiment, "complaining"
        else:
            return sentiment, "neutral"
    
    def analyze_comment_thread(self, comments: List[ScrapedComment]) -> Dict[str, Any]:
        """Analyze comment thread for agreement indicators and pain amplification."""
        total_agreements = 0
        total_sentiment = 0
        comment_count = 0
        
        def traverse(comments_list: List[ScrapedComment], depth: int = 0):
            nonlocal total_agreements, total_sentiment, comment_count
            
            for comment in comments_list:
                comment_count += 1
                
                # Check for agreement indicators
                text_lower = comment.body.lower()
                for pattern in AGREEMENT_PATTERNS:
                    if re.search(pattern, text_lower):
                        total_agreements += 1
                        comment.agreement_indicators += 1
                
                # Calculate sentiment
                sentiment = self._calculate_frustration_score(text_lower) / 100
                comment.sentiment_score = sentiment
                total_sentiment += sentiment
                
                # Traverse replies
                if comment.replies:
                    traverse(comment.replies, depth + 1)
        
        traverse(comments)
        
        avg_sentiment = total_sentiment / max(1, comment_count)
        agreement_ratio = total_agreements / max(1, comment_count)
        
        return {
            "total_comments": comment_count,
            "agreement_indicators": total_agreements,
            "agreement_ratio": round(agreement_ratio, 3),
            "avg_sentiment": round(avg_sentiment, 3),
            "pain_amplification": agreement_ratio > 0.2 and avg_sentiment > 0.3
        }
    
    def synthesize_opportunity(
        self,
        post: ScrapedPost,
        analysis: Dict[str, Any],
        velocity: VelocityMetrics,
        competitor_mentions: List[CompetitorMention]
    ) -> OpportunitySignal:
        """
        Synthesize all analysis into a unified opportunity signal.
        
        This combines all scores into a final opportunity assessment.
        """
        intent_signals = analysis.get("intent_signals", [])
        frustration_score = analysis.get("frustration_score", 0)
        monetization = analysis.get("monetization_indicators", {})
        
        # Calculate component scores
        intent_score = max([s["score"] for s in intent_signals], default=0)
        monetization_score = monetization.get("score", 0)
        
        # Velocity score (0-100)
        velocity_score = min(100, velocity.viral_probability)
        
        # Trend score (placeholder - would need historical data)
        trend_score = 50
        
        # Weighted opportunity score
        opportunity_score = (
            intent_score * 0.35 +
            frustration_score * 0.25 +
            velocity_score * 0.15 +
            monetization_score * 0.15 +
            trend_score * 0.10
        )
        
        # Determine priority
        if opportunity_score >= 75:
            priority = "high"
        elif opportunity_score >= 50:
            priority = "medium"
        elif opportunity_score >= 25:
            priority = "low"
        else:
            priority = "monitor"
        
        # Extract suggested features from intent captures
        suggested_features = []
        for signal in intent_signals[:3]:  # Top 3 signals
            capture = signal.get("capture", "")
            if capture and len(capture) > 5:
                suggested_features.append(capture)
        
        # Extract competitor gaps
        competitor_gaps = [
            m.context[:100] for m in competitor_mentions
            if m.sentiment < 0 or m.intent in ["complaining", "switching"]
        ]
        
        # Generate recommendation
        if priority == "high":
            action = "Immediate: Validate with target users, build MVP"
        elif priority == "medium":
            action = "Short-term: Monitor trends, conduct deeper research"
        elif priority == "low":
            action = "Long-term: Track for pattern changes"
        else:
            action = "Monitor only: Not enough signal yet"
        
        return OpportunitySignal(
            opportunity_score=round(opportunity_score, 1),
            priority=priority,
            intent_score=round(intent_score, 1),
            frustration_score=round(frustration_score, 1),
            velocity_score=round(velocity_score, 1),
            trend_score=round(trend_score, 1),
            monetization_score=round(monetization_score, 1),
            problem_statement=analysis.get("problem_statement", ""),
            target_audience=post.metadata.get("subreddit", "unknown"),
            suggested_features=suggested_features,
            tech_stack_hints=analysis.get("tech_stack_hints", []),
            competitor_gaps=competitor_gaps[:3],
            recommended_action=action
        )