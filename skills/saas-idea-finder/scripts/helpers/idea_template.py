"""
Enhanced Idea Template Module for SaaS Idea Finder

Provides comprehensive idea templating with market opportunity quantification,
competition analysis, unit economics projections, technical risk assessment,
and founder-market fit assessment.
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MarketMetrics:
    """Market opportunity quantification metrics."""
    tam: Optional[float] = None  # Total Addressable Market ($)
    sam: Optional[float] = None  # Serviceable Available Market ($)
    som: Optional[float] = None  # Serviceable Obtainable Market - Year 1 ($)
    target_customer_count: Optional[int] = None
    acv: Optional[float] = None  # Average Contract Value ($)


@dataclass
class Competitor:
    """Competitor information."""
    name: str
    type: str  # 'direct' or 'indirect'
    description: Optional[str] = None
    url: Optional[str] = None


@dataclass
class UnitEconomics:
    """Unit economics projections."""
    estimated_cac: Optional[float] = None  # Customer Acquisition Cost ($)
    target_monthly_price: Optional[float] = None
    projected_ltv: Optional[float] = None  # Lifetime Value ($)
    ltv_cac_ratio: Optional[float] = None
    cac_payback_months: Optional[int] = None


@dataclass
class TechnicalRisk:
    """Technical risk assessment."""
    complexity: Optional[int] = None  # 1-5
    infrastructure_requirements: Optional[str] = None
    third_party_dependencies: Optional[str] = None
    scalability_concerns: Optional[str] = None
    security_compliance_requirements: Optional[str] = None


@dataclass
class FounderFit:
    """Founder-market fit assessment."""
    domain_expertise_level: Optional[int] = None  # 1-5
    personal_pain_point: Optional[bool] = None
    existing_network: Optional[bool] = None
    technical_skills_match: Optional[bool] = None
    passion_score: Optional[int] = None  # 1-5


@dataclass
class PainPointScore:
    """Pain point severity scoring breakdown."""
    frequency_score: int = 0  # 0-30
    intensity_score: int = 0  # 0-30
    current_spend_score: int = 0  # 0-20
    workaround_score: int = 0  # 0-20
    total_score: int = 0  # 0-100


class IdeaTemplate:
    """
    Enhanced idea template for SaaS Idea Finder.
    
    Provides comprehensive templating with market analysis, competition analysis,
    unit economics, technical risk assessment, and founder-market fit evaluation.
    """
    
    # Frequency mapping for pain scoring
    FREQUENCY_SCORES = {
        'daily': 30,
        'weekly': 20,
        'monthly': 10,
        'occasional': 5
    }
    
    # Intensity mapping for pain scoring
    INTENSITY_SCORES = {
        'blocks work': 30,
        'significant frustration': 20,
        'mild annoyance': 10
    }
    
    # Current spend mapping for pain scoring
    SPEND_SCORES = {
        'high': 20,    # >$100/mo
        'medium': 15,  # $20-100/mo
        'low': 10,     # <$20/mo
        'time_only': 5
    }
    
    # Workaround mapping for pain scoring
    WORKAROUND_SCORES = {
        'complex': 20,
        'manual': 15,
        'occasional': 10,
        'none': 0
    }
    
    # Required fields for idea validation
    REQUIRED_FIELDS = [
        'title',
        'problem_statement',
        'target_audience',
        'solution_approach',
        'mvp_features'
    ]
    
    # Optional but recommended fields
    RECOMMENDED_FIELDS = [
        'market_metrics',
        'competitors',
        'unit_economics',
        'technical_risk',
        'founder_fit',
        'pain_point_score',
        'jtbd_statement'
    ]
    
    def __init__(self):
        """Initialize the IdeaTemplate."""
        pass
    
    def generate_template(self) -> str:
        """
        Generate a markdown template with all enhanced fields.
        
        Returns:
            str: Complete markdown template for idea documentation
        """
        template = """# SaaS Idea: {title}

*Generated: {timestamp}*
*Lens: {lens}*
*Source Research: {source_research}*

---

## 📋 Executive Summary

**One-liner:** {one_liner}

**Viability Score:** {viability_score}/100
**Recommendation:** {recommendation}

---

## 🎯 Problem Statement

{problem_statement}

### Pain Point Analysis

**Pain Severity Score:** {pain_score}/100
**Pain Interpretation:** {pain_interpretation}

**Jobs-to-be-Done Statement:**
> {jtbd_statement}

---

## 👥 Target Audience

{target_audience}

### Market Opportunity Quantification

| Metric | Value |
|--------|-------|
| **TAM (Total Addressable Market)** | ${tam:,.0f} |
| **SAM (Serviceable Available Market)** | ${sam:,.0f} |
| **SOM (Serviceable Obtainable Market - Year 1)** | ${som:,.0f} |
| **Target Customer Count** | {target_customer_count:,} |
| **Average Contract Value (ACV)** | ${acv:,.0f} |

---

## 💡 Solution Approach

{solution_approach}

### MVP Features

{mvp_features}

---

## 📊 Competition Analysis

### Direct Competitors

{direct_competitors}

### Indirect Competitors/Alternatives

{indirect_competitors}

### Competitive Differentiation

{competitive_differentiation}

**Market Saturation Score:** {saturation_score}/10
**Saturation Interpretation:** {saturation_interpretation}

---

## 💰 Unit Economics Projections

| Metric | Value |
|--------|-------|
| **Estimated CAC** | ${cac:,.0f} |
| **Target Monthly Price** | ${monthly_price:,.0f} |
| **Projected LTV** | ${ltv:,.0f} |
| **LTV:CAC Ratio** | {ltv_cac_ratio}:1 |
| **CAC Payback Period** | {cac_payback_months} months |

### Unit Economics Health

{unit_economics_health}

---

## ⚙️ Technical Risk Assessment

**Technical Complexity:** {complexity}/5

### Infrastructure Requirements

{infrastructure_requirements}

### Third-Party Dependencies

{third_party_dependencies}

### Scalability Concerns

{scalability_concerns}

### Security/Compliance Requirements

{security_compliance}

---

## 👤 Founder-Market Fit Assessment

| Factor | Value |
|--------|-------|
| **Domain Expertise Level** | {domain_expertise}/5 |
| **Personal Pain Point** | {personal_pain_point} |
| **Existing Network in Target Market** | {existing_network} |
| **Technical Skills Match** | {technical_skills_match} |
| **Passion Score** | {passion_score}/5 |

### Founder-Market Fit Interpretation

{founder_fit_interpretation}

---

## ⚠️ Red Flags

{red_flags}

---

## ✅ Success Probability Boosters

{success_boosters}

---

## 🛠️ Tech Stack

{tech_stack}

---

## 📈 Market Validation Plan

{market_validation}

---

## 📅 Timeline & Milestones

**Estimated Complexity:** {complexity_rating}/5
**Time to MVP:** {time_to_mvp}
**Pricing Model:** {pricing_model}

---

## 📝 Additional Notes

{additional_notes}

---

*Template generated by SaaS Idea Finder - Enhanced Template v2.0*
"""
        return template
    
    def format_idea(self, idea_data: Dict) -> str:
        """
        Format idea data into the enhanced template.
        
        Args:
            idea_data: Dictionary containing idea information
            
        Returns:
            str: Formatted markdown document
        """
        template = self.generate_template()
        
        # Extract market metrics
        market = idea_data.get('market_metrics', {})
        tam = market.get('tam', 0) if isinstance(market, dict) else 0
        sam = market.get('sam', 0) if isinstance(market, dict) else 0
        som = market.get('som', 0) if isinstance(market, dict) else 0
        target_customers = market.get('target_customer_count', 0) if isinstance(market, dict) else 0
        acv = market.get('acv', 0) if isinstance(market, dict) else 0
        
        # Extract competitors
        competitors = idea_data.get('competitors', [])
        direct = [c for c in competitors if isinstance(c, dict) and c.get('type') == 'direct']
        indirect = [c for c in competitors if isinstance(c, dict) and c.get('type') == 'indirect']
        
        direct_str = self._format_competitor_list(direct) if direct else "- *No direct competitors identified*"
        indirect_str = self._format_competitor_list(indirect) if indirect else "- *No indirect competitors identified*"
        
        # Extract unit economics
        unit_econ = idea_data.get('unit_economics', {})
        cac = unit_econ.get('estimated_cac', 0) if isinstance(unit_econ, dict) else 0
        monthly_price = unit_econ.get('target_monthly_price', 0) if isinstance(unit_econ, dict) else 0
        ltv = unit_econ.get('projected_ltv', 0) if isinstance(unit_econ, dict) else 0
        ltv_cac = unit_econ.get('ltv_cac_ratio', 0) if isinstance(unit_econ, dict) else 0
        payback = unit_econ.get('cac_payback_months', 0) if isinstance(unit_econ, dict) else 0
        
        # Unit economics health check
        unit_health = self._assess_unit_economics_health(ltv_cac, payback)
        
        # Extract technical risk
        tech_risk = idea_data.get('technical_risk', {})
        complexity = tech_risk.get('complexity', 3) if isinstance(tech_risk, dict) else 3
        infra = tech_risk.get('infrastructure_requirements', 'TBD') if isinstance(tech_risk, dict) else 'TBD'
        dependencies = tech_risk.get('third_party_dependencies', 'TBD') if isinstance(tech_risk, dict) else 'TBD'
        scalability = tech_risk.get('scalability_concerns', 'TBD') if isinstance(tech_risk, dict) else 'TBD'
        security = tech_risk.get('security_compliance_requirements', 'TBD') if isinstance(tech_risk, dict) else 'TBD'
        
        # Extract founder fit
        founder = idea_data.get('founder_fit', {})
        domain_exp = founder.get('domain_expertise_level', 3) if isinstance(founder, dict) else 3
        personal_pain = 'Yes' if founder.get('personal_pain_point') else 'No' if isinstance(founder, dict) else 'Unknown'
        network = 'Yes' if founder.get('existing_network') else 'No' if isinstance(founder, dict) else 'Unknown'
        skills_match = 'Yes' if founder.get('technical_skills_match') else 'No' if isinstance(founder, dict) else 'Unknown'
        passion = founder.get('passion_score', 3) if isinstance(founder, dict) else 3
        
        # Founder fit interpretation
        founder_fit_interp = self._interpret_founder_fit(domain_exp, personal_pain, network, skills_match, passion)
        
        # Pain point scoring
        pain_data = idea_data.get('pain_point_score', {})
        pain_score = pain_data.get('total_score', 0) if isinstance(pain_data, dict) else 0
        pain_interp = self.interpret_pain_score(pain_score)
        
        # JTBD statement
        jtbd = idea_data.get('jtbd_statement', '')
        if not jtbd and 'situation' in idea_data and 'motivation' in idea_data and 'outcome' in idea_data:
            jtbd = self.generate_jtbd_statement(
                idea_data.get('situation', ''),
                idea_data.get('motivation', ''),
                idea_data.get('outcome', '')
            )
        
        # Calculate viability score
        viability = self._calculate_viability_score(idea_data, pain_score)
        recommendation = self._get_recommendation(viability)
        
        # Market saturation
        saturation = idea_data.get('market_saturation_score', 5)
        saturation_interp = self._interpret_saturation(saturation)
        
        # Format target audience
        target_audience = idea_data.get('target_audience', [])
        if isinstance(target_audience, list):
            target_audience_str = '\n'.join([f"- {t}" for t in target_audience])
        else:
            target_audience_str = str(target_audience)
        
        # Format MVP features
        mvp_features = idea_data.get('mvp_features', [])
        if isinstance(mvp_features, list):
            mvp_features_str = '\n'.join([f"{i+1}. {f}" for i, f in enumerate(mvp_features)])
        else:
            mvp_features_str = str(mvp_features)
        
        # Format tech stack
        tech_stack = idea_data.get('tech_stack', {})
        if isinstance(tech_stack, dict):
            tech_stack_str = '\n\n'.join([f"**{k}:** {v}" for k, v in tech_stack.items()])
        else:
            tech_stack_str = str(tech_stack)
        
        # Format validation plan
        validation = idea_data.get('market_validation', [])
        if isinstance(validation, list):
            validation_str = '\n'.join([f"{i+1}. {v}" for i, v in enumerate(validation)])
        else:
            validation_str = str(validation)
        
        # Red flags and boosters
        red_flags = self._identify_red_flags(idea_data, tam, sam, som, ltv_cac, payback, complexity)
        success_boosters = self._identify_success_boosters(idea_data, pain_score)
        
        # Fill in the template
        formatted = template.format(
            title=idea_data.get('title', 'Untitled Idea'),
            timestamp=idea_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            lens=idea_data.get('lens', 'General'),
            source_research=idea_data.get('source_research', 'N/A'),
            one_liner=idea_data.get('one_liner', idea_data.get('title', 'TBD')),
            viability_score=viability,
            recommendation=recommendation,
            problem_statement=idea_data.get('problem_statement', 'TBD'),
            pain_score=pain_score,
            pain_interpretation=pain_interp,
            jtbd_statement=jtbd or 'TBD',
            target_audience=target_audience_str,
            tam=tam,
            sam=sam,
            som=som,
            target_customer_count=target_customers,
            acv=acv,
            solution_approach=idea_data.get('solution_approach', 'TBD'),
            mvp_features=mvp_features_str,
            direct_competitors=direct_str,
            indirect_competitors=indirect_str,
            competitive_differentiation=idea_data.get('competitive_differentiation', 'TBD'),
            saturation_score=saturation,
            saturation_interpretation=saturation_interp,
            cac=cac,
            monthly_price=monthly_price,
            ltv=ltv,
            ltv_cac_ratio=ltv_cac,
            cac_payback_months=payback,
            unit_economics_health=unit_health,
            complexity=complexity,
            infrastructure_requirements=infra,
            third_party_dependencies=dependencies,
            scalability_concerns=scalability,
            security_compliance=security,
            domain_expertise=domain_exp,
            personal_pain_point=personal_pain,
            existing_network=network,
            technical_skills_match=skills_match,
            passion_score=passion,
            founder_fit_interpretation=founder_fit_interp,
            red_flags=red_flags,
            success_boosters=success_boosters,
            tech_stack=tech_stack_str,
            market_validation=validation_str,
            complexity_rating=complexity,
            time_to_mvp=idea_data.get('time_to_mvp', 'TBD'),
            pricing_model=idea_data.get('pricing_model', 'TBD'),
            additional_notes=idea_data.get('additional_notes', '')
        )
        
        return formatted
    
    def extract_market_metrics(self, research_text: str) -> Dict:
        """
        Extract TAM/SAM/SOM from research text using regex/pattern matching.
        
        Args:
            research_text: Research text to analyze
            
        Returns:
            Dict with extracted market metrics
        """
        metrics = {
            'tam': None,
            'sam': None,
            'som': None,
            'target_customer_count': None,
            'acv': None
        }
        
        # TAM patterns
        tam_patterns = [
            r'TAM[^\d]*(?:is|:|=)?[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
            r'total addressable market[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
            r'market size[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
        ]
        
        # SAM patterns
        sam_patterns = [
            r'SAM[^\d]*(?:is|:|=)?[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
            r'serviceable available market[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
            r'addressable market[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
        ]
        
        # SOM patterns
        som_patterns = [
            r'SOM[^\d]*(?:is|:|=)?[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
            r'serviceable obtainable market[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
            r'obtainable market[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
            r'year 1[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|B|M|T)',
        ]
        
        # Customer count patterns
        customer_patterns = [
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|thousand|billion)?\s*(?:potential |target )?customers',
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|thousand|billion)?\s*(?:target|addressable)\s+(?:users|businesses)',
        ]
        
        # ACV patterns
        acv_patterns = [
            r'ACV[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'average contract value[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'average deal size[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
        ]
        
        def parse_value(match, text) -> Optional[float]:
            """Parse a matched value with multiplier."""
            if not match:
                return None
            try:
                num = float(match.group(1).replace(',', ''))
                multiplier_str = match.group(2).lower() if len(match.groups()) > 1 and match.group(2) else ''
                multiplier = 1
                if 'trillion' in multiplier_str or multiplier_str == 't':
                    multiplier = 1_000_000_000_000
                elif 'billion' in multiplier_str or multiplier_str == 'b':
                    multiplier = 1_000_000_000
                elif 'million' in multiplier_str or multiplier_str == 'm':
                    multiplier = 1_000_000
                elif 'thousand' in multiplier_str or multiplier_str == 'k':
                    multiplier = 1_000
                return num * multiplier
            except (ValueError, IndexError):
                return None
        
        text_lower = research_text.lower()
        
        # Extract TAM
        for pattern in tam_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                metrics['tam'] = parse_value(match, research_text)
                break
        
        # Extract SAM
        for pattern in sam_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                metrics['sam'] = parse_value(match, research_text)
                break
        
        # Extract SOM
        for pattern in som_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                metrics['som'] = parse_value(match, research_text)
                break
        
        # Extract customer count
        for pattern in customer_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                num = match.group(1).replace(',', '')
                mult_str = match.group(2).lower() if match.group(2) else ''
                mult = 1
                if 'million' in mult_str:
                    mult = 1_000_000
                elif 'billion' in mult_str:
                    mult = 1_000_000_000
                elif 'thousand' in mult_str:
                    mult = 1_000
                metrics['target_customer_count'] = int(float(num) * mult)
                break
        
        # Extract ACV
        for pattern in acv_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                acv_str = match.group(1).replace(',', '')
                metrics['acv'] = float(acv_str)
                break
        
        return metrics
    
    def extract_competitors(self, research_text: str) -> List[Dict]:
        """
        Extract competitor mentions from research text.
        
        Args:
            research_text: Research text to analyze
            
        Returns:
            List of competitor dictionaries
        """
        competitors = []
        
        # Direct competitor patterns
        direct_patterns = [
            r'(?:direct competitors?|competitors? include|main competitors?|competing with|similar to)\s*:?\s*([^\n]+)',
            r'(?:companies like|players like|tools like)\s+([^\n]+(?:such as|including)[^\n]+)',
        ]
        
        # Indirect competitor patterns
        indirect_patterns = [
            r'(?:indirect competitors?|alternatives? include|workarounds? include|substitutes?)\s*:?\s*([^\n]+)',
            r'(?:people use|teams use|alternative solutions?)\s+([^\n]+(?:such as|including|like)[^\n]+)',
        ]
        
        # Company/product name extraction
        company_pattern = r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)(?:\s*\(|,|\s+-|\s+–)'
        
        text_lower = research_text.lower()
        
        # Extract direct competitors
        for pattern in direct_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                # Try to extract company names
                company_matches = re.findall(company_pattern, match)
                for company in company_matches[:3]:  # Limit to 3
                    if len(company) > 2:  # Avoid short matches
                        competitors.append({
                            'name': company.strip(),
                            'type': 'direct',
                            'description': None,
                            'url': None
                        })
        
        # Extract indirect competitors
        for pattern in indirect_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                company_matches = re.findall(company_pattern, match)
                for company in company_matches[:2]:  # Limit to 2
                    if len(company) > 2:
                        competitors.append({
                            'name': company.strip(),
                            'type': 'indirect',
                            'description': None,
                            'url': None
                        })
        
        # Remove duplicates based on name
        seen = set()
        unique_competitors = []
        for comp in competitors:
            name_lower = comp['name'].lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique_competitors.append(comp)
        
        return unique_competitors
    
    def extract_unit_economics(self, research_text: str) -> Dict:
        """
        Extract pricing/revenue data from research text.
        
        Args:
            research_text: Research text to analyze
            
        Returns:
            Dict with unit economics data
        """
        economics = {
            'estimated_cac': None,
            'target_monthly_price': None,
            'projected_ltv': None,
            'ltv_cac_ratio': None,
            'cac_payback_months': None
        }
        
        # CAC patterns
        cac_patterns = [
            r'CAC[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'customer acquisition cost[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'cost to acquire[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
        ]
        
        # Pricing patterns
        pricing_patterns = [
            r'(?:price|pricing|cost|subscription)[^\d]*[$]?\s*(\d+(?:\.\d+)?)\s*(?:/|\s)?\s*(month|mo|year|yr)?',
            r'\$(\d+(?:\.\d+)?)\s*(?:/|\s)?\s*(month|mo|year|yr)?',
            r'(\d+(?:\.\d+)?)\s*\$?\s*(?:per|\/)\s*(?:month|mo|user|seat)',
        ]
        
        # LTV patterns
        ltv_patterns = [
            r'LTV[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'lifetime value[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'customer lifetime value[^\d]*[$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
        ]
        
        # LTV:CAC ratio patterns
        ratio_patterns = [
            r'LTV[\s:]?CAC[^\d]*(\d+(?:\.\d+)?)[:\s]*(?:to|to 1|:1)?',
            r'ratio[^\d]*(\d+(?:\.\d+)?)[:\s]*(?:to|to 1|:1)?',
        ]
        
        # Payback period patterns
        payback_patterns = [
            r'(?:payback|payback period)[^\d]*(\d+)\s*(?:months?|mo)?',
            r'CAC[^\d]*(\d+)\s*(?:months?|mo)[^\d]*recover',
        ]
        
        text_lower = research_text.lower()
        
        # Extract CAC
        for pattern in cac_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                economics['estimated_cac'] = float(match.group(1).replace(',', ''))
                break
        
        # Extract pricing (monthly)
        for pattern in pricing_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                price = float(match.group(1))
                period = ''
                if len(match.groups()) > 1 and match.group(2):
                    period = match.group(2).lower()
                if 'year' in period or 'yr' in period:
                    price = price / 12  # Convert to monthly
                economics['target_monthly_price'] = price
                break
        
        # Extract LTV
        for pattern in ltv_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                economics['projected_ltv'] = float(match.group(1).replace(',', ''))
                break
        
        # Extract LTV:CAC ratio
        for pattern in ratio_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                economics['ltv_cac_ratio'] = float(match.group(1))
                break
        
        # Extract payback period
        for pattern in payback_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                economics['cac_payback_months'] = int(match.group(1))
                break
        
        return economics
    
    def extract_technical_requirements(self, research_text: str) -> Dict:
        """
        Extract technical complexity indicators from research text.
        
        Args:
            research_text: Research text to analyze
            
        Returns:
            Dict with technical requirement data
        """
        requirements = {
            'complexity': None,
            'infrastructure_requirements': None,
            'third_party_dependencies': None,
            'scalability_concerns': None,
            'security_compliance_requirements': None
        }
        
        # Complexity indicators
        complexity_indicators = {
            'simple': 1,
            'easy': 1,
            'straightforward': 2,
            'moderate': 3,
            'complex': 4,
            'difficult': 4,
            'challenging': 4,
            'very complex': 5,
            'extremely complex': 5,
            'highly complex': 5,
            'sophisticated': 5
        }
        
        text_lower = research_text.lower()
        
        # Detect complexity level
        max_complexity = 0
        for indicator, level in complexity_indicators.items():
            if indicator in text_lower:
                max_complexity = max(max_complexity, level)
        
        if max_complexity > 0:
            requirements['complexity'] = max_complexity
        
        # Infrastructure patterns
        infra_patterns = [
            r'(?:infrastructure|hosting|deployment|servers?)[^.:]*[:.]?\s*([^\n]+(?:\n[^\n]+){0,2})',
            r'(?:requires|needs)[^\n]*(?:infrastructure|cloud|server)[^.:]*[:.]?\s*([^\n]+)',
        ]
        
        for pattern in infra_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                requirements['infrastructure_requirements'] = match.group(1).strip()[:200]
                break
        
        # Dependencies patterns
        dep_patterns = [
            r'(?:dependencies|integrates? with|third.party|APIs?)[^.:]*[:.]?\s*([^\n]+(?:\n[^\n]+){0,2})',
            r'(?:requires|uses)[^\n]*(?:integration|API|service)[^.:]*[:.]?\s*([^\n]+)',
        ]
        
        for pattern in dep_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                requirements['third_party_dependencies'] = match.group(1).strip()[:200]
                break
        
        # Scalability patterns
        scale_patterns = [
            r'(?:scalability|scale|performance|bottleneck)[^.:]*[:.]?\s*([^\n]+(?:\n[^\n]+){0,2})',
            r'(?:challenges?|concerns?)[^\n]*(?:scale|growth|load)[^.:]*[:.]?\s*([^\n]+)',
        ]
        
        for pattern in scale_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                requirements['scalability_concerns'] = match.group(1).strip()[:200]
                break
        
        # Security/Compliance patterns
        security_patterns = [
            r'(?:security|compliance|GDPR|HIPAA|SOC2)[^.:]*[:.]?\s*([^\n]+(?:\n[^\n]+){0,2})',
            r'(?:requires|needs)[^\n]*(?:compliance|certification|security)[^.:]*[:.]?\s*([^\n]+)',
        ]
        
        for pattern in security_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                requirements['security_compliance_requirements'] = match.group(1).strip()[:200]
                break
        
        return requirements
    
    def generate_jtbd_statement(self, situation: str, motivation: str, outcome: str) -> str:
        """
        Generate a Jobs-to-be-Done statement.
        
        Format: "When [situation], I want to [motivation], so I can [desired outcome]."
        
        Args:
            situation: The situation/context
            motivation: What the user wants to do
            outcome: The desired outcome
            
        Returns:
            str: Formatted JTBD statement
        """
        # Clean up inputs
        situation = situation.strip().rstrip(',').rstrip('.')
        motivation = motivation.strip().rstrip(',').rstrip('.')
        outcome = outcome.strip().rstrip(',').rstrip('.')
        
        # Ensure proper capitalization
        situation = situation[0].lower() + situation[1:] if situation else ''
        motivation = motivation[0].lower() + motivation[1:] if motivation else ''
        outcome = outcome[0].lower() + outcome[1:] if outcome else ''
        
        return f"When {situation}, I want to {motivation}, so I can {outcome}."
    
    def calculate_pain_severity(
        self,
        frequency: str,
        intensity: str,
        current_spend: float,
        workaround: bool
    ) -> Dict:
        """
        Calculate Pain Point Severity Score (0-100).
        
        Scoring breakdown:
        - Frequency (0-30 pts): Daily=30, Weekly=20, Monthly=10, Occasional=5
        - Intensity (0-30 pts): Blocks work=30, Significant frustration=20, Mild annoyance=10
        - Current Spend (0-20 pts): >$100/mo=20, $20-100=15, <$20=10, Time only=5
        - Workaround Evidence (0-20 pts): Complex workflow=20, Manual process=15, Occasional=10
        
        Args:
            frequency: 'daily', 'weekly', 'monthly', or 'occasional'
            intensity: 'blocks work', 'significant frustration', or 'mild annoyance'
            current_spend: Current monthly spend on workarounds
            workaround: Whether there's evidence of workarounds
            
        Returns:
            Dict with score breakdown and total
        """
        frequency_lower = frequency.lower()
        intensity_lower = intensity.lower()
        
        # Frequency score (0-30)
        freq_score = self.FREQUENCY_SCORES.get(frequency_lower, 5)
        
        # Intensity score (0-30)
        int_score = self.INTENSITY_SCORES.get(intensity_lower, 10)
        
        # Current spend score (0-20)
        if current_spend > 100:
            spend_score = self.SPEND_SCORES['high']
        elif current_spend >= 20:
            spend_score = self.SPEND_SCORES['medium']
        elif current_spend > 0:
            spend_score = self.SPEND_SCORES['low']
        else:
            spend_score = self.SPEND_SCORES['time_only']
        
        # Workaround score (0-20)
        if workaround:
            work_score = self.WORKAROUND_SCORES['complex']  # Default to complex if workaround exists
        else:
            work_score = self.WORKAROUND_SCORES['none']
        
        total = freq_score + int_score + spend_score + work_score
        
        return {
            'frequency_score': freq_score,
            'intensity_score': int_score,
            'current_spend_score': spend_score,
            'workaround_score': work_score,
            'total_score': total
        }
    
    def interpret_pain_score(self, score: int) -> str:
        """
        Interpret pain severity score.
        
        Score ranges:
        - 80-100: Critical pain - build immediately
        - 60-79: Significant pain - strong opportunity
        - 40-59: Moderate pain - validate further
        - <40: Minor inconvenience - likely not viable
        
        Args:
            score: Pain severity score (0-100)
            
        Returns:
            str: Interpretation of the pain score
        """
        if score >= 80:
            return "Critical pain - build immediately"
        elif score >= 60:
            return "Significant pain - strong opportunity"
        elif score >= 40:
            return "Moderate pain - validate further"
        else:
            return "Minor inconvenience - likely not viable"
    
    def validate_idea_completeness(self, idea_data: Dict) -> Dict:
        """
        Validate all required fields are present in idea data.
        
        Args:
            idea_data: Dictionary containing idea information
            
        Returns:
            Dict with validation results including:
            - is_complete: Boolean indicating if all required fields are present
            - missing_required: List of missing required field names
            - missing_recommended: List of missing recommended field names
            - completion_percentage: Percentage of fields present (0-100)
            - warnings: List of warning messages
        """
        result = {
            'is_complete': True,
            'missing_required': [],
            'missing_recommended': [],
            'completion_percentage': 0,
            'warnings': []
        }
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in idea_data or idea_data[field] is None or idea_data[field] == '':
                result['missing_required'].append(field)
                result['is_complete'] = False
        
        # Check recommended fields
        for field in self.RECOMMENDED_FIELDS:
            if field not in idea_data or idea_data[field] is None or idea_data[field] == '':
                result['missing_recommended'].append(field)
        
        # Calculate completion percentage
        all_fields = self.REQUIRED_FIELDS + self.RECOMMENDED_FIELDS
        present_count = len(all_fields) - len(result['missing_required']) - len(result['missing_recommended'])
        result['completion_percentage'] = (present_count / len(all_fields)) * 100
        
        # Generate warnings
        if result['missing_required']:
            result['warnings'].append(f"Missing required fields: {', '.join(result['missing_required'])}")
        
        # Check for specific red flags
        market_metrics = idea_data.get('market_metrics', {})
        if isinstance(market_metrics, dict):
            tam = market_metrics.get('tam')
            if tam is not None:
                if tam < 1_000_000:
                    result['warnings'].append(f"TAM (${tam:,.0f}) may be too small to sustain a business")
                elif tam > 1_000_000_000_000:
                    result['warnings'].append(f"TAM (${tam:,.0f}) is very large - may attract big competitors")
        
        unit_econ = idea_data.get('unit_economics', {})
        if isinstance(unit_econ, dict):
            ltv_cac = unit_econ.get('ltv_cac_ratio')
            if ltv_cac is not None and ltv_cac < 2:
                result['warnings'].append(f"LTV:CAC ratio ({ltv_cac}:1) is below 2:1 - unsustainable unit economics")
            
            payback = unit_econ.get('cac_payback_months')
            if payback is not None and payback > 18:
                result['warnings'].append(f"CAC payback period ({payback} months) exceeds 18 months - cash flow risk")
        
        tech_risk = idea_data.get('technical_risk', {})
        if isinstance(tech_risk, dict):
            complexity = tech_risk.get('complexity')
            if complexity == 5:
                result['warnings'].append("Technical complexity is 5/5 - may be too complex for 1-2 person team")
        
        return result
    
    # Helper methods
    
    def _format_competitor_list(self, competitors: List[Dict]) -> str:
        """Format competitor list as markdown."""
        lines = []
        for comp in competitors:
            name = comp.get('name', 'Unknown')
            desc = comp.get('description', '')
            url = comp.get('url', '')
            line = f"- **{name}**"
            if desc:
                line += f" - {desc}"
            if url:
                line += f" ([link]({url}))"
            lines.append(line)
        return '\n'.join(lines) if lines else "- *None identified*"
    
    def _assess_unit_economics_health(self, ltv_cac: float, payback_months: int) -> str:
        """Assess unit economics health."""
        if ltv_cac is None or payback_months is None:
            return "Insufficient data to assess unit economics health."
        
        issues = []
        
        if ltv_cac < 2:
            issues.append(f"❌ LTV:CAC ratio ({ltv_cac}:1) is below 2:1 - unsustainable")
        elif ltv_cac < 3:
            issues.append(f"⚠️ LTV:CAC ratio ({ltv_cac}:1) is acceptable but could be stronger")
        else:
            issues.append(f"✅ LTV:CAC ratio ({ltv_cac}:1) is healthy")
        
        if payback_months > 18:
            issues.append(f"❌ CAC payback ({payback_months} months) exceeds 18 months - cash flow risk")
        elif payback_months > 12:
            issues.append(f"⚠️ CAC payback ({payback_months} months) is acceptable but watch cash flow")
        else:
            issues.append(f"✅ CAC payback ({payback_months} months) is healthy")
        
        return '\n\n'.join(issues)
    
    def _interpret_founder_fit(
        self,
        domain_exp: int,
        personal_pain: str,
        network: str,
        skills_match: str,
        passion: int
    ) -> str:
        """Interpret founder-market fit."""
        score = 0
        
        if domain_exp >= 4:
            score += 2
        elif domain_exp >= 3:
            score += 1
        
        if personal_pain.lower() == 'yes':
            score += 2
        
        if network.lower() == 'yes':
            score += 1
        
        if skills_match.lower() == 'yes':
            score += 1
        
        if passion >= 4:
            score += 1
        
        if score >= 6:
            return "Excellent founder-market fit - strong advantage in execution"
        elif score >= 4:
            return "Good founder-market fit - competitive advantage present"
        elif score >= 2:
            return "Moderate founder-market fit - consider partnerships or team expansion"
        else:
            return "Weak founder-market fit - high risk of slow product-market fit"
    
    def _calculate_viability_score(self, idea_data: Dict, pain_score: int) -> int:
        """Calculate overall viability score (0-100)."""
        scores = {
            'problem_quality': min(pain_score / 5, 20),  # 20% weight
            'market_opportunity': 0,  # 15% weight
            'competitive_position': 0,  # 10% weight
            'unit_economics': 0,  # 15% weight
            'technical_feasibility': 0,  # 10% weight
            'founder_fit': 0,  # 15% weight
            'timing': 10,  # 10% weight - default
            'execution_clarity': 5   # 5% weight - default
        }
        
        # Market opportunity (0-15)
        market = idea_data.get('market_metrics', {})
        if isinstance(market, dict):
            tam = market.get('tam', 0)
            if tam > 1_000_000_000:
                scores['market_opportunity'] = 15
            elif tam > 100_000_000:
                scores['market_opportunity'] = 12
            elif tam > 10_000_000:
                scores['market_opportunity'] = 9
            elif tam > 1_000_000:
                scores['market_opportunity'] = 6
            else:
                scores['market_opportunity'] = 3
        
        # Competitive position (0-10)
        saturation = idea_data.get('market_saturation_score', 5)
        scores['competitive_position'] = max(0, 10 - saturation)
        
        # Unit economics (0-15)
        unit_econ = idea_data.get('unit_economics', {})
        if isinstance(unit_econ, dict):
            ltv_cac = unit_econ.get('ltv_cac_ratio', 0)
            if ltv_cac >= 5:
                scores['unit_economics'] = 15
            elif ltv_cac >= 3:
                scores['unit_economics'] = 12
            elif ltv_cac >= 2:
                scores['unit_economics'] = 8
            else:
                scores['unit_economics'] = 4
        
        # Technical feasibility (0-10)
        tech_risk = idea_data.get('technical_risk', {})
        if isinstance(tech_risk, dict):
            complexity = tech_risk.get('complexity', 3)
            scores['technical_feasibility'] = max(0, 10 - complexity * 2)
        
        # Founder fit (0-15)
        founder = idea_data.get('founder_fit', {})
        if isinstance(founder, dict):
            domain = founder.get('domain_expertise_level', 3)
            passion = founder.get('passion_score', 3)
            personal_pain = founder.get('personal_pain_point', False)
            
            fit_score = (domain * 2) + (passion * 2)
            if personal_pain:
                fit_score += 5
            scores['founder_fit'] = min(15, fit_score)
        
        return int(sum(scores.values()))
    
    def _get_recommendation(self, viability_score: int) -> str:
        """Get recommendation based on viability score."""
        if viability_score >= 85:
            return "🟢 Exceptional - Prioritize immediately"
        elif viability_score >= 70:
            return "🟡 Strong - Proceed with validation"
        elif viability_score >= 55:
            return "🟠 Moderate - Proceed cautiously"
        elif viability_score >= 40:
            return "🔴 Weak - Address weaknesses first"
        else:
            return "❌ Poor - Avoid, fundamental flaws"
    
    def _interpret_saturation(self, score: int) -> str:
        """Interpret market saturation score."""
        if score <= 3:
            return "Green field - High opportunity, <10 players"
        elif score <= 6:
            return "Yellow - Moderate opportunity, 10-30 players"
        elif score <= 8:
            return "Orange - Niche opportunity only, 30-50 players"
        else:
            return "Red - Avoid unless major differentiation, 50+ players"
    
    def _identify_red_flags(self, idea_data: Dict, tam: float, sam: float, som: float, 
                            ltv_cac: float, payback: int, complexity: int) -> str:
        """Identify and format red flags."""
        flags = []
        
        if tam < 1_000_000:
            flags.append(f"🚩 TAM (${tam:,.0f}) is too small to sustain a business")
        elif tam > 1_000_000_000_000:
            flags.append(f"🚩 TAM (${tam:,.0f}) is very large - may attract big competitors")
        
        if ltv_cac is not None and ltv_cac < 2:
            flags.append(f"🚩 LTV:CAC ratio ({ltv_cac}:1) below 2:1 - unsustainable unit economics")
        
        if payback is not None and payback > 18:
            flags.append(f"🚩 CAC payback period ({payback} months) - cash flow risk")
        
        if complexity == 5:
            flags.append("🚩 Technical complexity 5/5 - execution risk for small team")
        
        # Check for competitors
        competitors = idea_data.get('competitors', [])
        direct_count = sum(1 for c in competitors if isinstance(c, dict) and c.get('type') == 'direct')
        if direct_count >= 3:
            flags.append(f"🚩 {direct_count}+ direct competitors - hard to differentiate")
        
        if not flags:
            return "No major red flags identified."
        
        return '\n'.join([f"{i+1}. {flag}" for i, flag in enumerate(flags)])
    
    def _identify_success_boosters(self, idea_data: Dict, pain_score: int) -> str:
        """Identify and format success probability boosters."""
        boosters = []
        
        founder = idea_data.get('founder_fit', {})
        if isinstance(founder, dict) and founder.get('personal_pain_point'):
            boosters.append("✅ Founder has personal pain point")
        
        pain_data = idea_data.get('pain_point_score', {})
        if isinstance(pain_data, dict):
            spend_score = pain_data.get('current_spend_score', 0)
            if spend_score >= 15:
                boosters.append("✅ Customers spending $20+/month on workarounds")
        
        if pain_score >= 60:
            boosters.append("✅ Clear 10x improvement potential over status quo")
        
        market = idea_data.get('market_metrics', {})
        if isinstance(market, dict):
            tam = market.get('tam', 0)
            if tam > 0:
                boosters.append("✅ Growing market opportunity")
        
        competitors = idea_data.get('competitors', [])
        direct_count = sum(1 for c in competitors if isinstance(c, dict) and c.get('type') == 'direct')
        if direct_count == 0:
            boosters.append("✅ Weak or no direct competition")
        
        tech_risk = idea_data.get('technical_risk', {})
        if isinstance(tech_risk, dict):
            complexity = tech_risk.get('complexity', 3)
            if complexity <= 2:
                boosters.append("✅ Can build MVP in 4-8 weeks")
        
        pain_data = idea_data.get('pain_point_score', {})
        if isinstance(pain_data, dict):
            freq_score = pain_data.get('frequency_score', 0)
            if freq_score >= 20:
                boosters.append("✅ High engagement use case (daily/weekly)")
        
        if not boosters:
            return "No specific success boosters identified."
        
        return '\n'.join(boosters)


# Convenience functions for direct usage

def create_template() -> str:
    """Create a new empty template."""
    return IdeaTemplate().generate_template()


def format_idea(idea_data: Dict) -> str:
    """Format idea data into enhanced template."""
    return IdeaTemplate().format_idea(idea_data)


def extract_all_metrics(research_text: str) -> Dict:
    """Extract all metrics from research text."""
    template = IdeaTemplate()
    return {
        'market_metrics': template.extract_market_metrics(research_text),
        'competitors': template.extract_competitors(research_text),
        'unit_economics': template.extract_unit_economics(research_text),
        'technical_requirements': template.extract_technical_requirements(research_text)
    }


# Example usage
if __name__ == "__main__":
    # Example idea data
    example_idea = {
        'title': 'SyncBridge - Local-first Database Sync',
        'lens': 'Developer Tools Monday',
        'problem_statement': 'Web developers struggle with CRDT implementation complexity.',
        'target_audience': [
            'Full-stack JavaScript developers',
            'Teams building PWAs',
            'SaaS startups needing offline functionality'
        ],
        'solution_approach': 'Drop-in JavaScript library with managed backend service.',
        'mvp_features': [
            'Client-side IndexedDB wrapper',
            'Conflict resolution engine',
            'WebSocket real-time sync',
            'React/Vue/Svelte hooks'
        ],
        'market_metrics': {
            'tam': 5_000_000_000,
            'sam': 500_000_000,
            'som': 5_000_000,
            'target_customer_count': 100000,
            'acv': 500
        },
        'pain_point_score': {
            'total_score': 72
        },
        'jtbd_statement': 'When building collaborative web apps, I want to add offline capabilities easily, so I can focus on features instead of sync logic.',
        'technical_risk': {
            'complexity': 3
        }
    }
    
    # Generate formatted output
    template = IdeaTemplate()
    output = template.format_idea(example_idea)
    print(output[:2000])  # Print first 2000 chars