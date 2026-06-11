#!/usr/bin/env python3
"""
Stage 3: Synthesize SaaS Ideas

Generates actionable Micro-SaaS ideas from research reports using AI.
Includes viability scoring and enhanced idea templating.
"""

import sys
import os
import time
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# Robust path resolution for imports (works from any working directory)
SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_ROOT = SCRIPT_DIR.parent
SHARED_DIR = Path(__file__).resolve().parents[3] / 'shared'

# Add paths for imports
sys.path.insert(0, str(SCRIPT_DIR))  # For helpers
sys.path.insert(0, str(SKILL_ROOT))  # For skill modules
sys.path.insert(0, str(SHARED_DIR))  # For shared utilities

from credentials import load_credential, CredentialNotFound
from helpers.lens_manager import LensManager
from helpers.state_manager import StateManager

# Import new viability scoring and template modules
try:
    from helpers.viability_scorer import ViabilityScorer
    VIABILITY_AVAILABLE = True
except ImportError:
    VIABILITY_AVAILABLE = False

try:
    from helpers.idea_template import IdeaTemplate
    TEMPLATE_AVAILABLE = True
except ImportError:
    TEMPLATE_AVAILABLE = False

# Import OpenAI for idea generation
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def load_openrouter_key() -> str:
    """Load OPENROUTER_API_KEY using shared credential loader."""
    try:
        return load_credential(
            "OPENROUTER_API_KEY",
            required=True
        )
    except CredentialNotFound as e:
        raise ValueError(f"OPENROUTER_API_KEY not found: {e}")


def extract_metrics_from_research(research_content: str) -> Dict[str, Any]:
    """
    Extract key metrics from research content for better idea generation.
    
    Args:
        research_content: Research markdown content
        
    Returns:
        Dictionary of extracted metrics
    """
    metrics = {
        'market_size': None,
        'growth_rate': None,
        'pricing_mentions': [],
        'pain_points': [],
        'competitors': []
    }
    
    # Extract market size
    market_patterns = [
        r'(?:market size|market is|valued at)[^\d]*\$?\s*(\d+(?:\.\d+)?)\s*(billion|million|trillion)',
        r'(?:TAM|total addressable market)[^\d]*\$?\s*(\d+(?:\.\d+)?)\s*(billion|million|trillion)',
    ]
    
    for pattern in market_patterns:
        match = re.search(pattern, research_content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            multiplier = 1_000_000_000 if 'billion' in unit else 1_000_000 if 'million' in unit else 1_000_000_000_000
            metrics['market_size'] = value * multiplier
            break
    
    # Extract growth rate
    growth_match = re.search(r'CAGR[^\d]*(\d+(?:\.\d+)?)%', research_content, re.IGNORECASE)
    if growth_match:
        metrics['growth_rate'] = float(growth_match.group(1))
    
    # Extract pain points (sentences mentioning pain, challenge, problem, struggle)
    pain_patterns = [
        r'(?:pain point|challenge|problem|struggle|difficulty)[^.:]*[:.]?([^\n]+)',
        r'(?:developers?|users?|teams?)[^\n]*(?:struggle|difficulty|challenge|pain)[^\n]*',
    ]
    
    for pattern in pain_patterns:
        matches = re.findall(pattern, research_content, re.IGNORECASE)
        metrics['pain_points'].extend([m.strip() for m in matches[:3]])
    
    # Extract competitor mentions
    comp_patterns = [
        r'(?:competitors? include|competing with|alternatives? such as)[^:]*:?([^\n]+)',
    ]
    
    for pattern in comp_patterns:
        matches = re.findall(pattern, research_content, re.IGNORECASE)
        for match in matches:
            # Split by common separators and clean
            comps = re.split(r',|\band\b', match)
            metrics['competitors'].extend([c.strip() for c in comps if len(c.strip()) > 2])
    
    return metrics


def generate_saas_ideas(
    research_content: str, 
    topic: str, 
    lens_name: str, 
    num_ideas: int = 3,
    include_viability_details: bool = False
) -> str:
    """
    Generate SaaS ideas from research content using AI.

    Args:
        research_content: Markdown research report
        topic: Topic name
        lens_name: Lens context
        num_ideas: Number of ideas to generate
        include_viability_details: Whether to request detailed viability metrics

    Returns:
        Markdown with generated SaaS ideas
    """
    if not OPENAI_AVAILABLE:
        raise ImportError("openai library not installed")

    # Get lens context
    lens_manager = LensManager()
    saas_focus = lens_manager.get_saas_focus(lens_name)
    
    # Extract metrics from research to guide AI
    research_metrics = extract_metrics_from_research(research_content)

    # Initialize OpenAI client with OpenRouter
    api_key = load_openrouter_key()
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    # Build enhanced prompt with viability fields
    viability_instruction = """
**Market Analysis (REQUIRED - use research data or reasonable estimates):**
- TAM (Total Addressable Market): $X (be specific, e.g., "$500M" or "$2.5B")
- SAM (Serviceable Addressable Market): $X (e.g., "$50M" or "$200M")
- SOM (Serviceable Obtainable Market - Year 1): $X (e.g., "$100K" or "$500K")

**Competitor Analysis (REQUIRED):**
- Direct competitors: [List 2-3 with brief analysis]
- Indirect competitors: [List 2-3 alternatives]
- Competitive advantage: [Why this solution wins]

**Unit Economics Projections (REQUIRED - realistic estimates):**
- Estimated CAC (Customer Acquisition Cost): $X (e.g., "$200", "$500")
- Estimated LTV (Lifetime Value): $X (e.g., "$2,400", "$6,000")
- LTV:CAC ratio: X:1 (e.g., "3:1", "5:1")
- Payback period: X months (e.g., "6 months", "12 months")
- Target pricing: $X/month (e.g., "$49/month", "$199/month")

**Technical Complexity Assessment:**
- Backend complexity: [Low/Medium/High]
- Frontend complexity: [Low/Medium/High]
- Integration requirements: [List key integrations needed]
- Infrastructure needs: [Hosting, scaling considerations]

**Founder-Market Fit Assessment:**
- Domain expertise required: [Specific knowledge areas]
- Network effects: [Do founders need existing connections?]
- Regulatory considerations: [Compliance requirements]
""" if include_viability_details else ""

    # Truncate research but preserve important parts
    # Try to keep the executive summary and pain points sections
    max_chars = 10000 if include_viability_details else 8000
    research_truncated = research_content[:max_chars]
    
    # If truncated, try to find a good breaking point
    if len(research_content) > max_chars:
        # Try to break at a section boundary
        last_section = research_truncated.rfind('\n## ')
        if last_section > max_chars * 0.7:  # Only if we keep at least 70%
            research_truncated = research_truncated[:last_section]

    prompt = f"""You are an expert Micro-SaaS strategist. Based on the research report about "{topic}", generate {num_ideas} actionable, specific Micro-SaaS ideas.

Lens Context: {lens_name}
Target Focus: {saas_focus}

Research Insights:
- Market Size: {research_metrics.get('market_size', 'Not specified in research')}
- Growth Rate: {research_metrics.get('growth_rate', 'Not specified')}%
- Key Pain Points: {', '.join(research_metrics.get('pain_points', [])[:3]) or 'See research'}
- Competitors Mentioned: {', '.join(research_metrics.get('competitors', [])[:3]) or 'See research'}

Research Report:
{research_truncated}

For each idea, provide COMPLETE information for ALL fields:

## Idea N: [Name] - [Tagline]

**Problem Statement:**
[Specific problem from research, with evidence - 2-3 sentences]

**Target Audience:**
[Hyper-specific customer segment - who exactly has this problem?]

**Solution Approach:**
[How it solves the problem technically - be specific]

**MVP Features:**
1. [Core feature 1 - specific functionality]
2. [Core feature 2 - specific functionality]
3. [Core feature 3 - specific functionality]

**Tech Stack:**
- Frontend: [e.g., React, Vue, etc.]
- Backend: [e.g., Node.js, Python, etc.]
- Database: [e.g., PostgreSQL, MongoDB, etc.]
- Infrastructure: [e.g., AWS, Vercel, etc.]

**Market Validation:**
[How to test demand in 48 hours - specific steps]

**Jobs-to-be-Done (JTBD) Statement:**
"When [situation], I want to [motivation], so I can [expected outcome]"

**Pain Point Severity Score:** [1-100, where 100 = critical business-threatening pain]
{viability_instruction}
**Estimated Complexity:** [1-5]/5
**Time to MVP:** [Weeks estimate, e.g., "4-6 weeks"]
**Pricing Model:** [How to monetize, e.g., "SaaS subscription at $49/month"]

---

CRITICAL REQUIREMENTS:
1. Every field must have content - NO empty sections
2. Be SPECIFIC - no generic statements like "various tools" or "cloud infrastructure"
3. Use REALISTIC numbers for market size, pricing, and economics
4. Each idea must be buildable by 1-2 developers in 4-8 weeks
5. Focus on the lens context: {saas_focus}
6. Base ideas on ACTUAL pain points from the research

Generate exactly {num_ideas} complete ideas in markdown format.
"""

    print("🤖 Generating SaaS ideas...")
    if include_viability_details:
        print("📊 Including detailed viability analysis...")

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[
                {"role": "system", "content": "You are an expert Micro-SaaS strategist who generates actionable, specific business ideas. You ALWAYS provide complete information for every field and use specific, realistic numbers. Never leave fields empty or use generic placeholder text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=7000 if include_viability_details else 5000,
            temperature=0.7
        )

        ideas_markdown = response.choices[0].message.content
        return ideas_markdown

    except Exception as e:
        print(f"Error generating ideas: {e}", file=sys.stderr)
        raise


def extract_section_content(section: str, header_pattern: str) -> str:
    """
    Extract content under a markdown header pattern.
    
    Args:
        section: The section text
        header_pattern: Pattern to match the header
        
    Returns:
        Extracted content or empty string
    """
    # Match header and capture content until next ## or ** header or end
    pattern = rf'{header_pattern}\s*\n(.*?)(?=\n##|\n\*\*[A-Z]|\Z)'
    match = re.search(pattern, section, re.IGNORECASE | re.DOTALL)
    if match:
        content = match.group(1).strip()
        # Clean up markdown list formatting
        content = re.sub(r'\n\s*[-*]\s*', '\n- ', content)
        return content
    return ''


def parse_market_analysis(section: str) -> Dict[str, Any]:
    """Extract market analysis metrics from section."""
    market = {}
    
    # TAM
    tam_match = re.search(r'TAM[^\d\n]*\$?\s*([\d,.]+)\s*(million|billion|trillion|M|B|T)?', section, re.IGNORECASE)
    if tam_match:
        value_str = tam_match.group(1).replace(',', '')
        if value_str and value_str.replace('.', '').isdigit():
            value = float(value_str)
            unit = (tam_match.group(2) or '').lower()
            mult = 1_000_000 if 'million' in unit or 'm' in unit else 1_000_000_000 if 'billion' in unit or 'b' in unit else 1
            market['tam'] = value * mult
    
    # SAM
    sam_match = re.search(r'SAM[^\d\n]*\$?\s*([\d,.]+)\s*(million|billion|trillion|M|B|T)?', section, re.IGNORECASE)
    if sam_match:
        value_str = sam_match.group(1).replace(',', '')
        if value_str and value_str.replace('.', '').isdigit():
            value = float(value_str)
            unit = (sam_match.group(2) or '').lower()
            mult = 1_000_000 if 'million' in unit or 'm' in unit else 1_000_000_000 if 'billion' in unit or 'b' in unit else 1
            market['sam'] = value * mult
    
    # SOM
    som_match = re.search(r'SOM[^\d\n]*\$?\s*([\d,.]+)\s*(million|billion|K|k)?', section, re.IGNORECASE)
    if som_match:
        value_str = som_match.group(1).replace(',', '')
        # Validate the matched string is actually a number
        if value_str and value_str.replace('.', '').isdigit():
            value = float(value_str)
            unit = (som_match.group(2) or '').lower()
            mult = 1_000_000 if 'million' in unit else 1_000_000_000 if 'billion' in unit else 1_000 if 'k' in unit else 1
            market['som'] = value * mult
    
    return market


def parse_unit_economics(section: str) -> Dict[str, Any]:
    """Extract unit economics from section."""
    economics = {}
    
    # CAC
    cac_match = re.search(r'CAC[^\d\n]*\$?\s*([\d,]+)', section, re.IGNORECASE)
    if cac_match:
        economics['cac'] = float(cac_match.group(1).replace(',', ''))
    
    # LTV
    ltv_match = re.search(r'LTV[^\d\n]*\$?\s*([\d,]+)(?!:)', section, re.IGNORECASE)
    if ltv_match:
        economics['ltv'] = float(ltv_match.group(1).replace(',', ''))
    
    # LTV:CAC ratio
    ratio_match = re.search(r'LTV:CAC[^\d]*(\d+(?:\.\d+)?)\s*:?\s*1?', section, re.IGNORECASE)
    if ratio_match:
        economics['ltv_cac_ratio'] = float(ratio_match.group(1))
    
    # Payback period
    payback_match = re.search(r'payback[^\d]*(\d+)\s*month', section, re.IGNORECASE)
    if payback_match:
        economics['cac_payback_months'] = int(payback_match.group(1))
    
    # Pricing
    price_match = re.search(r'(?:pricing|price)[^\d\n]*\$?\s*([\d]+)\s*/\s*(month|mo)', section, re.IGNORECASE)
    if price_match:
        economics['target_monthly_price'] = float(price_match.group(1))
    else:
        # Try alternate format: $X/month
        price_match2 = re.search(r'\$([\d]+)\s*/\s*(month|mo)', section, re.IGNORECASE)
        if price_match2:
            economics['target_monthly_price'] = float(price_match2.group(1))
    
    return economics


def parse_mvp_features(section: str) -> List[str]:
    """Extract MVP features as a list."""
    features = []
    
    # Match numbered or bulleted list items
    pattern = r'(?:^|\n)\s*(?:\d+\.|[\-*])\s*([^\n]+)'
    matches = re.findall(pattern, section)
    
    for match in matches[:5]:  # Limit to first 5 features
        feature = match.strip()
        if feature and len(feature) > 5:  # Filter out short/empty items
            features.append(feature)
    
    return features


def parse_ideas_from_markdown(markdown_content: str) -> List[Dict[str, Any]]:
    """
    Parse individual ideas from the generated markdown with enhanced extraction.
    
    Args:
        markdown_content: The raw markdown output from AI
        
    Returns:
        List of parsed idea dictionaries with complete structured data
    """
    ideas = []
    
    # Split by Idea headers (handle variations)
    idea_sections = re.split(r'\n##\s*(?:Idea\s*\d+[:\-\.]?|#{1,3}\s*[^\n]+)\s*[:\-\.]?', markdown_content)
    
    for section in idea_sections[1:]:  # Skip first empty section
        section = section.strip()
        if not section or len(section) < 100:  # Skip very short sections
            continue
            
        idea = {
            'raw_content': section,
            'title': 'Untitled Idea',
            'name': '',
            'tagline': '',
            'problem_statement': '',
            'target_audience': '',
            'solution_approach': '',
            'mvp_features': [],
            'tech_stack': '',
            'market_validation': '',
            'jtbd_statement': '',
            'pain_severity_score': 50,  # Default to neutral
            'complexity': 3,
            'time_to_mvp': '',
            'pricing_model': '',
            'market_metrics': {},
            'competitors': [],
            'unit_economics': {},
            'technical_risk': {},
            'founder_fit': {}
        }
        
        # Extract name and tagline from first line
        lines = section.split('\n')
        if lines:
            first_line = lines[0].strip()
            # Remove markdown formatting
            first_line = re.sub(r'^#+\s*', '', first_line)
            
            if ' - ' in first_line or ' – ' in first_line or ': ' in first_line:
                # Try different separators
                for sep in [' - ', ' – ', ': ']:
                    if sep in first_line:
                        parts = first_line.split(sep, 1)
                        idea['name'] = parts[0].strip()
                        idea['tagline'] = parts[1].strip()
                        idea['title'] = first_line
                        break
            else:
                idea['name'] = first_line
                idea['title'] = first_line
        
        # Extract pain severity score (handle multiple formats)
        pain_patterns = [
            r'Pain Point Severity Score[:\s]*([\d]+)',
            r'Pain Severity[:\s]*([\d]+)',
            r'Severity Score[:\s]*([\d]+)',
        ]
        for pattern in pain_patterns:
            pain_match = re.search(pattern, section, re.IGNORECASE)
            if pain_match:
                idea['pain_severity_score'] = int(pain_match.group(1))
                break
        
        # Extract complexity
        complexity_match = re.search(r'Estimated Complexity[^\d]*(\d+)', section, re.IGNORECASE)
        if complexity_match:
            idea['complexity'] = int(complexity_match.group(1))
        
        # Extract time to MVP
        time_match = re.search(r'Time to MVP[^\d]*(\d+[-\s]*(?:to|-)\s*\d+|\d+)\s*(week|month)', section, re.IGNORECASE)
        if time_match:
            idea['time_to_mvp'] = time_match.group(0).split(':')[-1].strip()
        
        # Extract pricing model
        pricing_section = extract_section_content(section, r'\*\*Pricing Model:\*\*')
        if pricing_section:
            idea['pricing_model'] = pricing_section
        
        # Extract JTBD statement
        jtbd_match = re.search(r'Jobs-to-be-Done.*?Statement[:\s]*["\']?([^"\']+)["\']?', section, re.IGNORECASE | re.DOTALL)
        if jtbd_match:
            idea['jtbd_statement'] = jtbd_match.group(1).strip()
        
        # Extract problem statement
        idea['problem_statement'] = extract_section_content(section, r'\*\*Problem Statement:\*\*')
        
        # Extract target audience
        idea['target_audience'] = extract_section_content(section, r'\*\*Target Audience:\*\*')
        
        # Extract solution approach
        idea['solution_approach'] = extract_section_content(section, r'\*\*Solution Approach:\*\*')
        
        # Extract MVP features
        mvp_section = extract_section_content(section, r'\*\*MVP Features:\*\*')
        if mvp_section:
            idea['mvp_features'] = parse_mvp_features(mvp_section)
        
        # Extract tech stack
        idea['tech_stack'] = extract_section_content(section, r'\*\*Tech Stack:\*\*')
        
        # Extract market validation
        idea['market_validation'] = extract_section_content(section, r'\*\*Market Validation:\*\*')
        
        # Extract market analysis
        idea['market_metrics'] = parse_market_analysis(section)
        
        # Extract unit economics
        idea['unit_economics'] = parse_unit_economics(section)
        
        # Fill in defaults for missing critical fields
        if not idea['problem_statement']:
            idea['problem_statement'] = 'See raw content for details'
        if not idea['target_audience']:
            idea['target_audience'] = 'See raw content for details'
        if not idea['mvp_features']:
            idea['mvp_features'] = ['Core functionality', 'User authentication', 'Dashboard']
        if not idea['time_to_mvp']:
            idea['time_to_mvp'] = f"{idea['complexity'] * 2}-{idea['complexity'] * 3} weeks"
        
        ideas.append(idea)
    
    return ideas


def calculate_viability_scores(
    ideas: List[Dict[str, Any]], 
    include_details: bool = False
) -> List[Dict[str, Any]]:
    """
    Calculate viability scores for all ideas using extracted data.
    
    Args:
        ideas: List of parsed idea dictionaries
        include_details: Whether to include detailed scoring breakdown
        
    Returns:
        List of ideas with viability scores added
    """
    if not VIABILITY_AVAILABLE:
        print("⚠️  ViabilityScorer not available, using basic scoring")
        for idea in ideas:
            # Basic scoring based on available data
            score = 50  # Base score
            
            # Adjust for pain severity
            pain = idea.get('pain_severity_score', 50)
            score += (pain - 50) * 0.2
            
            # Adjust for market data presence
            market = idea.get('market_metrics', {})
            if market.get('tam', 0) > 0:
                score += 10
            if market.get('som', 0) > 0:
                score += 5
            
            # Adjust for unit economics presence
            unit_econ = idea.get('unit_economics', {})
            if unit_econ.get('cac', 0) > 0 and unit_econ.get('ltv', 0) > 0:
                score += 10
            
            # Adjust for completeness
            if idea.get('mvp_features'):
                score += 5
            if idea.get('market_validation'):
                score += 5
            
            idea['viability_score'] = min(max(int(score), 0), 100)
            idea['viability_rating'] = get_basic_rating(idea['viability_score'])
            idea['red_flags'] = []
            idea['success_boosters'] = []
        return ideas
    
    scorer = ViabilityScorer()
    
    for idea in ideas:
        # Extract values from parsed data
        market = idea.get('market_metrics', {})
        unit_econ = idea.get('unit_economics', {})
        
        # Determine urgency from pain severity
        pain_score = idea.get('pain_severity_score', 50)
        if pain_score >= 80:
            urgency = 'critical'
        elif pain_score >= 60:
            urgency = 'high'
        elif pain_score >= 40:
            urgency = 'medium'
        else:
            urgency = 'low'
        
        # Build idea_data dictionary matching ViabilityScorer expectations
        idea_data = {
            'problem_quality': {
                'pain_evidence': [idea.get('problem_statement', '')] if idea.get('problem_statement') else [],
                'urgency': urgency,
                'workaround_evidence': pain_score >= 60  # Assume workaround if pain is high
            },
            'market_opportunity': {
                'tam': market.get('tam', 0),
                'sam': market.get('sam', 0),
                'som': market.get('som', 0),
                'growth_rate': 15  # Default moderate growth
            },
            'competitive_position': {
                'differentiation': 'moderate',
                'competitors': len(idea.get('competitors', [])),
                'moat_potential': 'moderate'
            },
            'unit_economics': {
                'cac': unit_econ.get('cac', 500),
                'price': unit_econ.get('target_monthly_price', 50),
                'ltv': unit_econ.get('ltv', 1500)
            },
            'technical_feasibility': {
                'complexity': idea.get('complexity', 3),
                'team_size': 2,  # Assume 2-person team
                'dependencies': []
            },
            'founder_market_fit': {
                'domain_expertise': 2,  # Default moderate
                'personal_pain': pain_score >= 70,  # Assume personal pain if high severity
                'network': False
            },
            'timing': {
                'market_maturity': 'growth',
                'trend_alignment': True,
                'urgency': urgency
            },
            'execution_clarity': {
                'validation_plan': idea.get('market_validation', '')[:100],
                'mvp_scope': str(idea.get('mvp_features', ''))[:100]
            }
        }
        
        try:
            # Calculate comprehensive viability score
            score_result = scorer.calculate_score(idea_data)
            
            idea['viability_score'] = score_result.total_score
            idea['viability_rating'] = score_result.rating
            
            if include_details:
                idea['viability_breakdown'] = score_result.category_scores
            
            # Add red flags and success boosters
            idea['red_flags'] = score_result.red_flags
            idea['success_boosters'] = score_result.success_boosters
        except Exception as e:
            # Fallback if scoring fails
            print(f"Warning: Viability scoring failed for idea '{idea.get('name', 'Unknown')}': {e}")
            idea['viability_score'] = 50
            idea['viability_rating'] = 'Unknown'
            idea['red_flags'] = []
            idea['success_boosters'] = []
    
    return ideas


def get_basic_rating(score: int) -> str:
    """Get basic rating label for scores when ViabilityScorer is not available."""
    if score >= 80:
        return "Strong"
    elif score >= 60:
        return "Moderate"
    elif score >= 40:
        return "Weak"
    else:
        return "Poor"


def format_idea_with_template(idea: Dict[str, Any], include_viability: bool = False) -> str:
    """
    Format a single idea using the enhanced template.
    
    Args:
        idea: Idea dictionary with all fields
        include_viability: Whether to include viability scoring in output
        
    Returns:
        Formatted markdown string for the idea
    """
    if not TEMPLATE_AVAILABLE:
        # Fallback to basic formatting
        lines = [
            f"## {idea.get('name', 'Unnamed Idea')} - {idea.get('tagline', '')}",
            "",
            f"**Problem Statement:**",
            f"{idea.get('problem_statement', 'N/A')}",
            "",
            f"**Target Audience:**",
            f"{idea.get('target_audience', 'N/A')}",
            "",
        ]
        
        if include_viability:
            lines.extend([
                f"**Viability Score:** {idea.get('viability_score', 'N/A')}/100 ({idea.get('viability_rating', 'Unknown')})",
                f"**Pain Severity:** {idea.get('pain_severity_score', 'N/A')}/100",
                "",
            ])
        
        return '\n'.join(lines)
    
    # Use IdeaTemplate for enhanced formatting
    template = IdeaTemplate()
    return template.format_idea(idea)


def filter_ideas_by_thresholds(
    ideas: List[Dict[str, Any]], 
    pain_threshold: int = 0,
    min_viability: int = 0
) -> List[Dict[str, Any]]:
    """
    Filter ideas based on pain severity and viability thresholds.
    
    Args:
        ideas: List of idea dictionaries
        pain_threshold: Minimum pain severity score (0-100)
        min_viability: Minimum viability score (0-100)
        
    Returns:
        Filtered list of ideas
    """
    filtered = []
    
    for idea in ideas:
        pain_score = idea.get('pain_severity_score', 0)
        viability_score = idea.get('viability_score', 0)
        
        if pain_score >= pain_threshold and viability_score >= min_viability:
            filtered.append(idea)
    
    return filtered


def generate_output_summary(ideas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for the output.
    
    Args:
        ideas: List of processed ideas
        
    Returns:
        Summary dictionary
    """
    if not ideas:
        return {
            'total_ideas': 0,
            'avg_viability': 0,
            'exceptional_count': 0,
            'strong_count': 0,
            'red_flags_found': 0
        }
    
    total_ideas = len(ideas)
    avg_viability = sum(idea.get('viability_score', 0) for idea in ideas) / total_ideas
    
    exceptional_count = sum(1 for idea in ideas if idea.get('viability_score', 0) >= 85)
    strong_count = sum(1 for idea in ideas if 70 <= idea.get('viability_score', 0) < 85)
    red_flags_found = sum(len(idea.get('red_flags', [])) for idea in ideas)
    
    return {
        'total_ideas': total_ideas,
        'avg_viability': round(avg_viability, 1),
        'exceptional_count': exceptional_count,
        'strong_count': strong_count,
        'red_flags_found': red_flags_found
    }


def generate_enhanced_markdown(
    ideas: List[Dict[str, Any]], 
    topic: str,
    lens_name: str,
    research_path: Path,
    include_viability: bool = False
) -> str:
    """
    Generate enhanced markdown output with all ideas.
    
    Args:
        ideas: List of processed idea dictionaries
        topic: Topic name
        lens_name: Lens context
        research_path: Path to source research file
        include_viability: Whether to include viability details
        
    Returns:
        Complete markdown content
    """
    header = f"""# SaaS Ideas: {topic}

*Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}*
*Lens: {lens_name}*
*Source research: {research_path.name}*

---

"""
    
    # Add summary section if viability scoring is enabled
    summary_content = ""
    if include_viability:
        summary = generate_output_summary(ideas)
        summary_content = f"""## 📊 Summary

| Metric | Value |
|--------|-------|
| Total Ideas | {summary['total_ideas']} |
| Average Viability | {summary['avg_viability']}/100 |
| Exceptional (85+) | {summary['exceptional_count']} |
| Strong (70-84) | {summary['strong_count']} |
| Red Flags Found | {summary['red_flags_found']} |

---

"""
    
    # Format each idea
    idea_sections = []
    for i, idea in enumerate(ideas, 1):
        if TEMPLATE_AVAILABLE:
            # Use enhanced template with structured data
            formatted = format_idea_with_template(idea, include_viability=include_viability)
        else:
            # Basic formatting
            formatted = format_idea_basic(idea, include_viability)
        idea_sections.append(formatted)
    
    return header + summary_content + '\n\n'.join(idea_sections)


def format_idea_basic(idea: Dict[str, Any], include_viability: bool) -> str:
    """Basic idea formatting when template is not available."""
    lines = [
        f"## {idea.get('name', 'Unnamed Idea')}",
        "",
        f"**Tagline:** {idea.get('tagline', 'N/A')}",
        "",
        "### Problem Statement",
        idea.get('problem_statement', 'See research for details'),
        "",
        "### Target Audience",
        idea.get('target_audience', 'See research for details'),
        "",
        "### Solution Approach",
        idea.get('solution_approach', 'See research for details'),
        "",
    ]
    
    if idea.get('mvp_features'):
        lines.extend([
            "### MVP Features",
            ""
        ])
        for i, feature in enumerate(idea['mvp_features'], 1):
            lines.append(f"{i}. {feature}")
        lines.append("")
    
    if include_viability:
        lines.extend([
            "### Viability",
            f"**Score:** {idea.get('viability_score', 'N/A')}/100 ({idea.get('viability_rating', 'Unknown')})",
            f"**Pain Severity:** {idea.get('pain_severity_score', 'N/A')}/100",
            f"**Complexity:** {idea.get('complexity', 'N/A')}/5",
            f"**Time to MVP:** {idea.get('time_to_mvp', 'N/A')}",
            ""
        ])
        
        # Market metrics
        market = idea.get('market_metrics', {})
        if any(market.values()):
            lines.extend([
                "### Market Metrics",
                f"- TAM: ${market.get('tam', 0):,.0f}" if market.get('tam') else "- TAM: Not specified",
                f"- SAM: ${market.get('sam', 0):,.0f}" if market.get('sam') else "- SAM: Not specified",
                f"- SOM: ${market.get('som', 0):,.0f}" if market.get('som') else "- SOM: Not specified",
                ""
            ])
        
        # Unit economics
        unit_econ = idea.get('unit_economics', {})
        if any(unit_econ.values()):
            lines.extend([
                "### Unit Economics",
            ])
            if unit_econ.get('cac'):
                lines.append(f"- CAC: ${unit_econ['cac']:,.0f}")
            if unit_econ.get('ltv'):
                lines.append(f"- LTV: ${unit_econ['ltv']:,.0f}")
            if unit_econ.get('ltv_cac_ratio'):
                lines.append(f"- LTV:CAC Ratio: {unit_econ['ltv_cac_ratio']}:1")
            if unit_econ.get('target_monthly_price'):
                lines.append(f"- Target Price: ${unit_econ['target_monthly_price']:,.0f}/month")
            lines.append("")
    
    lines.append("---")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate Micro-SaaS ideas from research')
    parser.add_argument('--research', required=True, help='Research markdown file path')
    parser.add_argument('--topic', help='Topic name (extracted from filename if not provided)')
    parser.add_argument('--lens', help='Lens context')
    parser.add_argument('--num-ideas', type=int, default=3, help='Number of ideas to generate')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--min-complexity', type=int, default=1, help='Min complexity (1-5)')
    parser.add_argument('--max-complexity', type=int, default=3, help='Max complexity (1-5)')
    
    # New command-line arguments for viability scoring
    parser.add_argument('--include-viability', action='store_true', 
                        help='Include detailed viability scoring')
    parser.add_argument('--pain-threshold', type=int, default=0,
                        help='Minimum pain severity score (0-100) to include idea')
    parser.add_argument('--min-viability', type=int, default=0,
                        help='Minimum viability score (0-100) to include idea')
    parser.add_argument('--json-output', action='store_true',
                        help='Also output results as JSON with structured data')

    args = parser.parse_args()

    start_time = time.time()

    try:
        # Read research file
        research_path = Path(args.research).expanduser()
        if not research_path.exists():
            print(f"❌ Error: Research file not found: {research_path}", file=sys.stderr)
            sys.exit(1)

        print(f"📖 Reading research from: {research_path}")
        with open(research_path, 'r') as f:
            research_content = f.read()

        # Extract topic from filename or arg
        if args.topic:
            topic = args.topic
        else:
            # Try to extract from frontmatter or filename
            if '---' in research_content:
                frontmatter = research_content.split('---')[1]
                for line in frontmatter.split('\n'):
                    if 'topic:' in line:
                        topic = line.split('topic:')[1].strip().strip('"\'')
                        break
                else:
                    topic = research_path.stem.replace('-', ' ').title()
            else:
                topic = research_path.stem.replace('-', ' ').title()

        # Get lens
        if args.lens:
            lens_name = args.lens
        else:
            # Try to extract from frontmatter
            lens_name = None
            if '---' in research_content:
                frontmatter = research_content.split('---')[1]
                for line in frontmatter.split('\n'):
                    if 'lens:' in line:
                        lens_name = line.split('lens:')[1].strip().strip('"\'')
                        break

            if not lens_name:
                lens_manager = LensManager()
                lens = lens_manager.get_active_lens()
                lens_name = lens['name']

        print(f"💡 Synthesizing SaaS ideas...")
        print(f"📋 Topic: {topic}")
        print(f"🔭 Lens: {lens_name}")
        print(f"🎯 Generating: {args.num_ideas} ideas")
        
        if args.include_viability:
            print(f"📊 Viability scoring enabled")
        if args.pain_threshold > 0:
            print(f"🔍 Pain threshold: {args.pain_threshold}+")
        if args.min_viability > 0:
            print(f"🔍 Min viability: {args.min_viability}+")

        # Generate ideas with enhanced prompt
        ideas_markdown = generate_saas_ideas(
            research_content, 
            topic, 
            lens_name, 
            args.num_ideas,
            include_viability_details=args.include_viability
        )

        # Parse ideas from markdown
        print("🔍 Parsing generated ideas...")
        parsed_ideas = parse_ideas_from_markdown(ideas_markdown)
        
        # Calculate viability scores if enabled
        if args.include_viability and VIABILITY_AVAILABLE:
            print("📊 Calculating viability scores...")
            parsed_ideas = calculate_viability_scores(
                parsed_ideas, 
                include_details=args.include_viability
            )
        
        # Filter by thresholds
        original_count = len(parsed_ideas)
        if args.pain_threshold > 0 or args.min_viability > 0:
            parsed_ideas = filter_ideas_by_thresholds(
                parsed_ideas, 
                pain_threshold=args.pain_threshold,
                min_viability=args.min_viability
            )
            if len(parsed_ideas) < original_count:
                print(f"🚫 Filtered out {original_count - len(parsed_ideas)} ideas below thresholds")
        
        # Determine output path
        if args.output:
            output_path = Path(args.output).expanduser()
        else:
            state_manager = StateManager()
            output_dir = state_manager.get_output_dir_for_date(stage='ideas')
            safe_topic = topic.lower().replace(' ', '-')[:50]
            output_path = output_dir / f"{safe_topic}_ideas.md"

        # Generate enhanced markdown output
        final_content = generate_enhanced_markdown(
            parsed_ideas,
            topic,
            lens_name,
            research_path,
            include_viability=args.include_viability
        )

        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(final_content)
        
        # Generate JSON output if requested
        json_output_path = None
        if args.json_output:
            json_output_path = output_path.with_suffix('.json')
            output_data = {
                'ideas': parsed_ideas,
                'viability_scores': [idea.get('viability_score', 0) for idea in parsed_ideas],
                'summary': generate_output_summary(parsed_ideas)
            }
            with open(json_output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"📄 JSON output saved: {json_output_path}")

        duration = time.time() - start_time

        print(f"\n✅ Synthesis complete!")
        print(f"   - Ideas generated: {len(parsed_ideas)}")
        if args.include_viability and parsed_ideas:
            avg_score = sum(idea.get('viability_score', 0) for idea in parsed_ideas) / len(parsed_ideas)
            print(f"   - Avg viability: {avg_score:.1f}/100")
        print(f"   - Duration: {duration:.1f}s")
        print(f"   - Output: {output_path}")
        
        # Status message for viability scorer
        if args.include_viability and not VIABILITY_AVAILABLE:
            print(f"   ⚠️  Note: ViabilityScorer not available, install helpers.viability_scorer")
        # Status message for idea template
        if args.include_viability and not TEMPLATE_AVAILABLE:
            print(f"   ⚠️  Note: IdeaTemplate not available, install helpers.idea_template")

        sys.exit(0)

    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Synthesis failed after {duration:.1f}s: {e}", file=sys.stderr)
        import traceback
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()