"""
Viability Scoring Module for SaaS Idea Finder.

Implements a comprehensive 0-100 scoring rubric for evaluating Micro-SaaS ideas
across 8 weighted categories with red flag detection and success booster identification.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ViabilityScore:
    """Container for viability scoring results."""
    total_score: int
    category_scores: Dict[str, int]
    rating: str
    recommendation: str
    red_flags: List[str]
    success_boosters: List[str]


class ViabilityScorer:
    """
    Comprehensive viability scoring system for Micro-SaaS ideas.
    
    Evaluates ideas across 8 weighted categories (0-100 total):
    - Problem Quality (20%)
    - Market Opportunity (15%)
    - Competitive Position (10%)
    - Unit Economics (15%)
    - Technical Feasibility (10%)
    - Founder-Market Fit (15%)
    - Timing (10%)
    - Execution Clarity (5%)
    """
    
    # Category weights (must sum to 100)
    WEIGHTS = {
        'problem_quality': 20,
        'market_opportunity': 15,
        'competitive_position': 10,
        'unit_economics': 15,
        'technical_feasibility': 10,
        'founder_market_fit': 15,
        'timing': 10,
        'execution_clarity': 5
    }
    
    # Urgency levels mapping
    URGENCY_LEVELS = {
        'critical': 20,
        'high': 15,
        'medium': 10,
        'low': 5
    }
    
    # Market maturity levels
    MARKET_MATURITY = {
        'early': 10,
        'growth': 8,
        'mature': 5,
        'declining': 2
    }
    
    # Differentiation levels
    DIFFERENTIATION = {
        '10x_better': 10,
        'significant': 7,
        'moderate': 5,
        'minimal': 2,
        'none': 0
    }
    
    # Moat potential levels
    MOAT_POTENTIAL = {
        'strong': 10,
        'moderate': 6,
        'weak': 3,
        'none': 0
    }
    
    def calculate_score(self, idea_data: Dict) -> ViabilityScore:
        """
        Calculate overall viability score for a SaaS idea.
        
        Args:
            idea_data: Dictionary containing fields for each category:
                - problem_quality: Dict with pain_evidence, urgency, workaround_evidence
                - market_opportunity: Dict with tam, sam, som, growth_rate
                - competitive_position: Dict with differentiation, competitors, moat_potential
                - unit_economics: Dict with cac, price, ltv
                - technical_feasibility: Dict with complexity, team_size, dependencies
                - founder_market_fit: Dict with domain_expertise, personal_pain, network
                - timing: Dict with market_maturity, trend_alignment, urgency
                - execution_clarity: Dict with validation_plan, mvp_scope
        
        Returns:
            ViabilityScore object with total score, category scores, rating, and recommendations
        """
        # Calculate individual category scores
        category_scores = {}
        
        # Problem Quality (20 points)
        pq_data = idea_data.get('problem_quality', {})
        category_scores['problem_quality'] = self.calculate_problem_quality(
            pain_evidence=pq_data.get('pain_evidence', []),
            urgency=pq_data.get('urgency', 'medium'),
            workaround_evidence=pq_data.get('workaround_evidence', False)
        )
        
        # Market Opportunity (15 points)
        mo_data = idea_data.get('market_opportunity', {})
        category_scores['market_opportunity'] = self.calculate_market_opportunity(
            tam=mo_data.get('tam', 0),
            sam=mo_data.get('sam', 0),
            som=mo_data.get('som', 0),
            growth_rate=mo_data.get('growth_rate', 0)
        )
        
        # Competitive Position (10 points)
        cp_data = idea_data.get('competitive_position', {})
        category_scores['competitive_position'] = self.calculate_competitive_position(
            differentiation=cp_data.get('differentiation', 'minimal'),
            competitors=cp_data.get('competitors', 0),
            moat_potential=cp_data.get('moat_potential', 'weak')
        )
        
        # Unit Economics (15 points)
        ue_data = idea_data.get('unit_economics', {})
        category_scores['unit_economics'] = self.calculate_unit_economics(
            cac=ue_data.get('cac', 0),
            price=ue_data.get('price', 0),
            ltv=ue_data.get('ltv', 0)
        )
        
        # Technical Feasibility (10 points)
        tf_data = idea_data.get('technical_feasibility', {})
        category_scores['technical_feasibility'] = self.calculate_technical_feasibility(
            complexity=tf_data.get('complexity', 3),
            team_size=tf_data.get('team_size', 1),
            dependencies=tf_data.get('dependencies', [])
        )
        
        # Founder-Market Fit (15 points)
        fmf_data = idea_data.get('founder_market_fit', {})
        category_scores['founder_market_fit'] = self.calculate_founder_market_fit(
            domain_expertise=fmf_data.get('domain_expertise', 1),
            personal_pain=fmf_data.get('personal_pain', False),
            network=fmf_data.get('network', False)
        )
        
        # Timing (10 points)
        timing_data = idea_data.get('timing', {})
        category_scores['timing'] = self.calculate_timing(
            market_maturity=timing_data.get('market_maturity', 'mature'),
            trend_alignment=timing_data.get('trend_alignment', False),
            urgency=timing_data.get('urgency', 'medium')
        )
        
        # Execution Clarity (5 points)
        ec_data = idea_data.get('execution_clarity', {})
        category_scores['execution_clarity'] = self.calculate_execution_clarity(
            validation_plan=ec_data.get('validation_plan', ''),
            mvp_scope=ec_data.get('mvp_scope', '')
        )
        
        # Calculate weighted total score
        total_score = sum(
            (category_scores[cat] * self.WEIGHTS[cat]) // max(self.WEIGHTS.values())
            for cat in category_scores
        )
        
        # Determine rating and recommendation
        rating = self.get_rating(total_score)
        recommendation = self.get_recommendation(total_score)
        
        # Check red flags and success boosters
        red_flags = self.check_red_flags(idea_data)
        success_boosters = self.check_success_boosters(idea_data)
        
        return ViabilityScore(
            total_score=total_score,
            category_scores=category_scores,
            rating=rating,
            recommendation=recommendation,
            red_flags=red_flags,
            success_boosters=success_boosters
        )
    
    def calculate_problem_quality(
        self,
        pain_evidence: List[str],
        urgency: str,
        workaround_evidence: bool
    ) -> int:
        """
        Calculate Problem Quality score (0-20 points).
        
        Args:
            pain_evidence: List of evidence items showing the pain point
            urgency: Urgency level ('critical', 'high', 'medium', 'low')
            workaround_evidence: Whether there's evidence of workarounds being used
        
        Returns:
            Score from 0-20
        """
        score = 0
        
        # Evidence strength (0-8 points)
        evidence_count = len(pain_evidence)
        if evidence_count >= 10:
            score += 8
        elif evidence_count >= 5:
            score += 6
        elif evidence_count >= 3:
            score += 4
        elif evidence_count >= 1:
            score += 2
        
        # Urgency (0-8 points)
        urgency_lower = urgency.lower()
        if urgency_lower == 'critical':
            score += 8
        elif urgency_lower == 'high':
            score += 6
        elif urgency_lower == 'medium':
            score += 4
        else:
            score += 2
        
        # Workaround evidence (0-4 points)
        if workaround_evidence:
            score += 4
        
        return min(score, 20)
    
    def calculate_market_opportunity(
        self,
        tam: float,
        sam: float,
        som: float,
        growth_rate: float
    ) -> int:
        """
        Calculate Market Opportunity score (0-15 points).
        
        Args:
            tam: Total Addressable Market in dollars
            sam: Serviceable Available Market in dollars
            som: Serviceable Obtainable Market (Year 1) in dollars
            growth_rate: Annual market growth rate as percentage (e.g., 20 for 20%)
        
        Returns:
            Score from 0-15
        """
        score = 0
        
        # TAM size (0-5 points) - optimal range $10M-$1B
        if 10_000_000 <= tam <= 1_000_000_000:
            score += 5
        elif 1_000_000 <= tam < 10_000_000:
            score += 3
        elif tam > 1_000_000_000:
            score += 2  # Too big attracts big competitors
        else:
            score += 1  # Too small
        
        # SAM/SOM ratio (0-4 points)
        if sam > 0 and tam > 0:
            sam_ratio = sam / tam
            if sam_ratio >= 0.1:  # Can serve at least 10% of TAM
                score += 4
            elif sam_ratio >= 0.05:
                score += 3
            elif sam_ratio >= 0.01:
                score += 2
            else:
                score += 1
        
        # Growth rate (0-4 points)
        if growth_rate >= 30:
            score += 4
        elif growth_rate >= 20:
            score += 3
        elif growth_rate >= 10:
            score += 2
        elif growth_rate > 0:
            score += 1
        
        # SOM viability (0-2 points)
        if som >= 100_000:  # At least $100K obtainable in year 1
            score += 2
        elif som >= 50_000:
            score += 1
        
        return min(score, 15)
    
    def calculate_competitive_position(
        self,
        differentiation: str,
        competitors: int,
        moat_potential: str
    ) -> int:
        """
        Calculate Competitive Position score (0-10 points).
        
        Args:
            differentiation: Level of differentiation ('10x_better', 'significant', 
                           'moderate', 'minimal', 'none')
            competitors: Number of direct competitors
            moat_potential: Moat potential ('strong', 'moderate', 'weak', 'none')
        
        Returns:
            Score from 0-10
        """
        score = 0
        
        # Differentiation (0-5 points)
        diff_lower = differentiation.lower().replace('-', '_')
        if diff_lower == '10x_better':
            score += 5
        elif diff_lower == 'significant':
            score += 4
        elif diff_lower == 'moderate':
            score += 3
        elif diff_lower == 'minimal':
            score += 1
        
        # Competition density (0-3 points) - fewer is better
        if competitors == 0:
            score += 3
        elif competitors <= 2:
            score += 2
        elif competitors <= 5:
            score += 1
        # 6+ competitors = 0 points
        
        # Moat potential (0-2 points)
        moat_lower = moat_potential.lower()
        if moat_lower == 'strong':
            score += 2
        elif moat_lower == 'moderate':
            score += 1
        
        return min(score, 10)
    
    def calculate_unit_economics(
        self,
        cac: float,
        price: float,
        ltv: float
    ) -> int:
        """
        Calculate Unit Economics score (0-15 points).
        
        Args:
            cac: Customer Acquisition Cost in dollars
            price: Monthly price in dollars
            ltv: Lifetime Value in dollars
        
        Returns:
            Score from 0-15
        """
        score = 0
        
        if cac <= 0 or price <= 0:
            return 0  # Invalid inputs
        
        # LTV:CAC ratio (0-8 points) - 3:1 is golden, 2:1 is minimum
        ltv_cac_ratio = ltv / cac if cac > 0 else 0
        if ltv_cac_ratio >= 5:
            score += 8
        elif ltv_cac_ratio >= 3:
            score += 6
        elif ltv_cac_ratio >= 2:
            score += 4
        elif ltv_cac_ratio >= 1:
            score += 2
        
        # CAC payback period (0-4 points) - <6 months is ideal, <18 is acceptable
        monthly_margin = price * 0.7  # Assume 70% gross margin
        payback_months = cac / monthly_margin if monthly_margin > 0 else float('inf')
        
        if payback_months <= 6:
            score += 4
        elif payback_months <= 12:
            score += 3
        elif payback_months <= 18:
            score += 2
        elif payback_months <= 24:
            score += 1
        
        # Price point sustainability (0-3 points)
        if price >= 100:
            score += 3
        elif price >= 50:
            score += 2
        elif price >= 20:
            score += 1
        
        return min(score, 15)
    
    def calculate_technical_feasibility(
        self,
        complexity: int,
        team_size: int,
        dependencies: List[str]
    ) -> int:
        """
        Calculate Technical Feasibility score (0-10 points).
        
        Args:
            complexity: Technical complexity 1-5 (1=simple, 5=very complex)
            team_size: Team size (founders/developers)
            dependencies: List of third-party dependencies
        
        Returns:
            Score from 0-10
        """
        score = 0
        
        # Complexity vs team size fit (0-5 points)
        # High complexity (4-5) with small team (1-2) = major risk
        if complexity <= 2:
            score += 5
        elif complexity == 3 and team_size >= 2:
            score += 4
        elif complexity == 3:
            score += 3
        elif complexity == 4 and team_size >= 3:
            score += 3
        elif complexity == 4 and team_size >= 2:
            score += 2
        elif complexity == 5 and team_size >= 4:
            score += 2
        elif complexity == 5 and team_size >= 3:
            score += 1
        
        # Team capability (0-3 points)
        if team_size >= 3:
            score += 3
        elif team_size == 2:
            score += 2
        elif team_size == 1:
            score += 1
        
        # Dependency risk (0-2 points) - fewer is better
        dep_count = len(dependencies)
        if dep_count <= 2:
            score += 2
        elif dep_count <= 4:
            score += 1
        
        return min(score, 10)
    
    def calculate_founder_market_fit(
        self,
        domain_expertise: int,
        personal_pain: bool,
        network: bool
    ) -> int:
        """
        Calculate Founder-Market Fit score (0-15 points).
        
        Args:
            domain_expertise: Domain expertise level 1-5 (5=expert)
            personal_pain: Whether founder has experienced this pain personally
            network: Whether founder has network in target market
        
        Returns:
            Score from 0-15
        """
        score = 0
        
        # Domain expertise (0-6 points)
        if domain_expertise >= 4:
            score += 6
        elif domain_expertise == 3:
            score += 4
        elif domain_expertise == 2:
            score += 2
        elif domain_expertise == 1:
            score += 1
        
        # Personal pain point (0-5 points)
        if personal_pain:
            score += 5
        
        # Network (0-4 points)
        if network:
            score += 4
        
        return min(score, 15)
    
    def calculate_timing(
        self,
        market_maturity: str,
        trend_alignment: bool,
        urgency: str
    ) -> int:
        """
        Calculate Timing score (0-10 points).
        
        Args:
            market_maturity: Market maturity ('early', 'growth', 'mature', 'declining')
            trend_alignment: Whether idea aligns with current trends
            urgency: Market urgency ('critical', 'high', 'medium', 'low')
        
        Returns:
            Score from 0-10
        """
        score = 0
        
        # Market maturity (0-4 points) - growth phase is optimal
        maturity_lower = market_maturity.lower()
        if maturity_lower == 'growth':
            score += 4
        elif maturity_lower == 'early':
            score += 3
        elif maturity_lower == 'mature':
            score += 2
        elif maturity_lower == 'declining':
            score += 0
        
        # Trend alignment (0-3 points)
        if trend_alignment:
            score += 3
        
        # Market urgency (0-3 points)
        urgency_lower = urgency.lower()
        if urgency_lower == 'critical':
            score += 3
        elif urgency_lower == 'high':
            score += 2
        elif urgency_lower == 'medium':
            score += 1
        
        return min(score, 10)
    
    def calculate_execution_clarity(
        self,
        validation_plan: str,
        mvp_scope: str
    ) -> int:
        """
        Calculate Execution Clarity score (0-5 points).
        
        Args:
            validation_plan: Description of validation plan
            mvp_scope: Description of MVP scope
        
        Returns:
            Score from 0-5
        """
        score = 0
        
        # Validation plan clarity (0-3 points)
        if validation_plan:
            plan_length = len(validation_plan.strip())
            if plan_length >= 100:
                score += 3
            elif plan_length >= 50:
                score += 2
            elif plan_length > 0:
                score += 1
        
        # MVP scope clarity (0-2 points)
        if mvp_scope:
            scope_length = len(mvp_scope.strip())
            if scope_length >= 50:
                score += 2
            elif scope_length > 0:
                score += 1
        
        return min(score, 5)
    
    def get_rating(self, total_score: int) -> str:
        """
        Get rating label based on total score.
        
        Args:
            total_score: Total viability score (0-100)
        
        Returns:
            Rating label string
        """
        if total_score >= 85:
            return "Exceptional"
        elif total_score >= 70:
            return "Strong"
        elif total_score >= 55:
            return "Moderate"
        elif total_score >= 40:
            return "Weak"
        else:
            return "Poor"
    
    def get_recommendation(self, total_score: int) -> str:
        """
        Get recommendation text based on total score.
        
        Args:
            total_score: Total viability score (0-100)
        
        Returns:
            Recommendation text string
        """
        if total_score >= 85:
            return "Prioritize - high probability of success"
        elif total_score >= 70:
            return "Strong candidate - proceed with validation"
        elif total_score >= 55:
            return "Proceed cautiously - address weaknesses"
        elif total_score >= 40:
            return "Significant concerns - major changes needed"
        else:
            return "Avoid - fundamental flaws"
    
    def check_red_flags(self, idea_data: Dict) -> List[str]:
        """
        Check for red flags that indicate potential problems with the idea.
        
        Red Flags:
        - TAM < $1M or > $1B
        - No evidence of customers paying for workarounds
        - LTV:CAC projection < 2:1
        - CAC payback > 18 months
        - 3+ well-funded direct competitors
        - Technical complexity 5/5 for 1-2 person team
        - Requires behavior change (no existing workflow)
        - Founder has no domain expertise or network
        
        Args:
            idea_data: Dictionary with idea data
        
        Returns:
            List of red flag descriptions
        """
        red_flags = []
        
        # Check TAM
        mo = idea_data.get('market_opportunity', {})
        tam = mo.get('tam', 0)
        if tam < 1_000_000:
            red_flags.append(f"TAM too small (${tam:,.0f} < $1M) - limited market potential")
        elif tam > 1_000_000_000:
            red_flags.append(f"TAM too large (${tam:,.0f} > $1B) - attracts big competitors")
        
        # Check workaround evidence
        pq = idea_data.get('problem_quality', {})
        if not pq.get('workaround_evidence', False):
            red_flags.append("No evidence of customers paying for workarounds - 'vitamin, not painkiller'")
        
        # Check unit economics
        ue = idea_data.get('unit_economics', {})
        cac = ue.get('cac', 0)
        price = ue.get('price', 0)
        ltv = ue.get('ltv', 0)
        
        if cac > 0:
            ltv_cac_ratio = ltv / cac
            if ltv_cac_ratio < 2:
                red_flags.append(f"LTV:CAC ratio too low ({ltv_cac_ratio:.1f}:1 < 2:1) - unsustainable unit economics")
            
            # Check payback period
            monthly_margin = price * 0.7
            if monthly_margin > 0:
                payback_months = cac / monthly_margin
                if payback_months > 18:
                    red_flags.append(f"CAC payback too long ({payback_months:.0f} months > 18) - cash flow risk")
        
        # Check competition
        cp = idea_data.get('competitive_position', {})
        if cp.get('competitors', 0) >= 3:
            red_flags.append(f"{cp['competitors']}+ well-funded direct competitors - hard to differentiate")
        
        # Check technical feasibility
        tf = idea_data.get('technical_feasibility', {})
        complexity = tf.get('complexity', 1)
        team_size = tf.get('team_size', 1)
        if complexity >= 5 and team_size <= 2:
            red_flags.append(f"High complexity (5/5) with small team ({team_size}) - execution risk")
        
        # Check founder-market fit
        fmf = idea_data.get('founder_market_fit', {})
        domain_expertise = fmf.get('domain_expertise', 1)
        has_network = fmf.get('network', False)
        if domain_expertise <= 1 and not has_network:
            red_flags.append("Founder lacks domain expertise and network - slow product-market fit expected")
        
        # Check if requires behavior change (inferred from problem quality)
        if not pq.get('workaround_evidence', False) and len(pq.get('pain_evidence', [])) < 3:
            red_flags.append("May require behavior change (no existing workflow evidence) - high friction, low adoption risk")
        
        return red_flags
    
    def check_success_boosters(self, idea_data: Dict) -> List[str]:
        """
        Check for success boosters that increase probability of success.
        
        Success Boosters:
        - Founder has personal pain point
        - Customers already spending $100+/month on workarounds
        - Clear 10x improvement over status quo
        - Growing market (20%+ annually)
        - Weak or no direct competition
        - Can build MVP in 4-8 weeks
        - Network effects possible
        - High engagement use case (daily/weekly)
        
        Args:
            idea_data: Dictionary with idea data
        
        Returns:
            List of success booster descriptions
        """
        boosters = []
        
        # Check personal pain point
        fmf = idea_data.get('founder_market_fit', {})
        if fmf.get('personal_pain', False):
            boosters.append("✅ Founder has personal pain point - deep understanding of problem")
        
        # Check workaround spending
        ue = idea_data.get('unit_economics', {})
        if ue.get('price', 0) >= 100:
            boosters.append("✅ Customers willing to spend $100+/month - strong monetization potential")
        
        # Check 10x improvement
        cp = idea_data.get('competitive_position', {})
        if cp.get('differentiation', '').lower() == '10x_better':
            boosters.append("✅ Clear 10x improvement over status quo - strong competitive advantage")
        
        # Check market growth
        mo = idea_data.get('market_opportunity', {})
        if mo.get('growth_rate', 0) >= 20:
            boosters.append("✅ Growing market (20%+ annually) - tailwinds for growth")
        
        # Check competition
        if cp.get('competitors', 0) <= 1:
            boosters.append("✅ Weak or no direct competition - blue ocean opportunity")
        
        # Check MVP timeline (inferred from technical feasibility)
        tf = idea_data.get('technical_feasibility', {})
        complexity = tf.get('complexity', 3)
        if complexity <= 2:
            boosters.append("✅ Can build MVP quickly (low complexity) - fast time to market")
        
        # Check network effects potential
        if cp.get('moat_potential', '').lower() == 'strong':
            boosters.append("✅ Network effects possible - potential for strong moat")
        
        # Check engagement potential (inferred from urgency)
        pq = idea_data.get('problem_quality', {})
        if pq.get('urgency', '').lower() in ['critical', 'high']:
            boosters.append("✅ High engagement use case (critical/high urgency) - frequent usage likely")
        
        return boosters
    
    def to_dict(self, score: ViabilityScore) -> Dict:
        """
        Convert ViabilityScore to dictionary format.
        
        Args:
            score: ViabilityScore object
        
        Returns:
            Dictionary representation
        """
        return {
            'total_score': score.total_score,
            'rating': score.rating,
            'recommendation': score.recommendation,
            'category_scores': score.category_scores,
            'red_flags': score.red_flags,
            'success_boosters': score.success_boosters,
            'weights': self.WEIGHTS
        }


# Convenience function for quick scoring
def score_idea(idea_data: Dict) -> Dict:
    """
    Quick scoring function that returns a dictionary.
    
    Args:
        idea_data: Dictionary with idea data
    
    Returns:
        Dictionary with scoring results
    """
    scorer = ViabilityScorer()
    result = scorer.calculate_score(idea_data)
    return scorer.to_dict(result)