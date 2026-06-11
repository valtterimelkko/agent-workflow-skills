---
name: saas-idea-finder
description: "Uses rotating lenses (7 different daily perspectives) to discover trending topics from HackerNews, HN Algolia, DEV.to, GitHub, arXiv, Stack Exchange, GDELT, SerpAPI, YouTube, Reddit, Twitter/X, and Instagram. Generates actionable Micro-SaaS ideas using deep research with viability scoring (0-100), enhanced templates, and JTBD framework. Daily automated discovery with deduplication. Use when: (1) User asks for SaaS/startup ideas, (2) User wants to discover trending topics in tech/business, (3) Daily automated idea generation is needed."
---

# SaaS Idea Finder

Automatically discover trending topics from multiple sources and generate actionable Micro-SaaS ideas based on real research and market signals.

## Overview

This skill implements a 3-stage pipeline that:
1. **Discovers trends** from HackerNews, HN Algolia Search, DEV.to, GitHub, arXiv, Stack Exchange, GDELT, SerpAPI, YouTube, **Reddit (self-hosted)**, and social media (Twitter/X, Instagram via Xpoz MCP)
2. **Researches topics** using GPT Researcher with comprehensive web analysis
3. **Generates SaaS ideas** using AI based on researched pain points and opportunities, with viability scoring (0-100)

Uses a rotating lens system (7 daily perspectives) to ensure fresh, diverse ideas with automatic deduplication.

## Pipeline Timing Expectations

**Total Pipeline Duration: ~3-6 minutes per topic**

| Stage | Component | Expected Time | Notes |
|-------|-----------|---------------|-------|
| **Stage 1: Discovery** | | **~30-60s** | |
| | HackerNews | 2-3s | Fast, reliable |
| | GitHub | 3-5s | Depends on API response |
| | DEV.to | 2-3s | Usually fast |
| | HN Algolia | 2-3s | Fast |
| | NewsAPI | 2-3s | Fast |
| | Product Hunt | 2-3s | Fast |
| | arXiv | 2-3s | Fast |
| | Stack Exchange | 2-3s | Fast |
| | GDELT | 2-3s | May timeout occasionally |
| | SerpAPI | 2-3s | Optional, may be skipped |
| | YouTube | 2-3s | Fast |
| | **Reddit** | **~18-25s** | Sequential fetches with rate limiting (4 subreddits × ~5s) |
| | **Twitter/X** | **~15-25s** | 8 parallel queries with 15s timeout each |
| **Stage 2: Research** | GPT Researcher | **~2-4 min** | Web scraping + LLM analysis |
| **Stage 3: Synthesis** | Idea Generation | **~30-60s** | LLM idea generation + viability scoring |

**Factors that increase time:**
- Slower API responses (TwitterAPI.io, Reddit)
- Rate limiting (Reddit: ~6s delay between requests)
- Network latency
- Complex research topics requiring more web scraping

**Factors that decrease time:**
- Cached/credential failures (skips source quickly)
- GDELT timeout (fails fast, ~2s)
- SerpAPI not configured (skipped)

**Maximum acceptable time:** 10 minutes (with 600s timeout buffer)

If pipeline exceeds 10 minutes, it likely indicates:
- Network connectivity issues
- API service degradation
- Hanging connection (should be rare with timeout fixes)

## Prerequisites

### Required API Keys

This skill uses the shared credential loading system with the following hierarchy:
1. Environment variables (highest priority)
2. HashiCorp Vault (for service users like openclaw)
3. a shell startup file such as `~/.bashrc`

**Example shell startup file setup**:
```bash
export GITHUB_TOKEN="ghp_your_token"
export OPENROUTER_API_KEY="sk-or-v1-your_key"
export STACK_KEY="your_stack_key"
export SERPAPI_KEY="your_serpapi_key"
export YOUTUBE_API_KEY="your_youtube_key"
export TWITTERAPI_KEY="your_twitterapi_key"
```

**For openclaw service user** (add to vault):
```bash
# GitHub token (optional, only for GitHub trend discovery)
vault kv put secret/skills-apis/github token="ghp_your_token"

# OpenRouter API key (required for research and idea generation)
vault kv put secret/skills-apis/openrouter api_key="sk-or-v1-your_key"

# Stack Exchange API (for Stack Overflow pain point discovery)
vault kv put secret/skills-apis/stackexchange value="your_stack_key"

# SerpAPI (for search validation and keyword trends)
vault kv put secret/skills-apis/serpapi value="your_serpapi_key"

# YouTube Data API (for content gap analysis)
vault kv put secret/skills-apis/youtube value="your_youtube_key"

# TwitterAPI.io (for Twitter/X trend discovery)
vault kv put secret/skills-apis/twitterapi/api_key value="your_twitterapi_key"
```

**Environment variables** (for testing or CI/CD):
```bash
export GITHUB_TOKEN="ghp_your_token"
export OPENROUTER_API_KEY="sk-or-v1-your_key"
export STACK_KEY="your_stack_key"
export SERPAPI_KEY="your_serpapi_key"
export YOUTUBE_API_KEY="your_youtube_key"
```

### Free APIs (No Keys Needed)
- HackerNews API (https://hacker-news.firebaseio.com)
- HN Algolia Search API (https://hn.algolia.com/api)
- DEV.to Forem API (https://developers.forem.com/api)
- arXiv API (https://export.arxiv.org/api) - Unlimited requests
- GDELT API (https://api.gdeltproject.org) - Unlimited requests

### Rate-Limited APIs (Free Tiers)
| API | Free Tier | Key Required |
|-----|-----------|--------------|
| **Stack Exchange** | 10,000 requests/day | STACK_KEY |
| **arXiv** | Unlimited | No key required |
| **GDELT** | Unlimited | No key required |
| **SerpAPI** | 250 searches/month | SERPAPI_KEY |
| **YouTube Data API** | 10,000 units/day | YOUTUBE_API_KEY |
| **TwitterAPI.io** | $0.10-$1.00 free credits | TWITTERAPI_KEY |
| **Xpoz Social** | 5,000 credits (one-time) | Xpoz OAuth (Instagram only) |

**TwitterAPI.io Credit Information:**
- **Free tier**: $0.10-$1.00 free credits upon signup (no credit card)
- **Pricing**: $0.15 per 1,000 tweets
- **Rate limits**: 1,000+ requests per second
- Get your API key at: https://twitterapi.io

**Xpoz Credit Information (Instagram only):**
- **Free tier**: 5,000 ONE-TIME credits (NOT monthly, NOT 100K)
- Credits do NOT refresh - once used, they're gone
- Credit formula: `Credits = (Queries × 5) + (Results × 0.005)`
- **Pro tier**: $20/month for 30,000 credits/month
- **Max tier**: $200/month for 600,000 credits/month

**Note**: Reddit and Twitter/X are now **self-hosted/managed API** and do NOT use Xpoz credits. Only Instagram requires Xpoz.

### Social Media Sources

The skill includes social media trend detection from:

| Platform | Source | Authentication | Rate Limit |
|----------|--------|----------------|------------|
| **Reddit** | Self-hosted JSON API | OAuth2 (recommended) or None | 100/min with OAuth2, 10/min without |
| **Twitter/X** | TwitterAPI.io | TWITTERAPI_KEY | 1,000+ req/sec |
| **Instagram** | Xpoz MCP | Xpoz OAuth (optional) | Via Xpoz credits |

**Reddit**: Uses Reddit's public `.json` endpoints with automatic rate limiting and User-Agent rotation.

- **Without OAuth2**: 10 requests/minute, may be blocked in some environments
- **With OAuth2**: 100 requests/minute, more reliable access

**Twitter/X**: Uses TwitterAPI.io direct REST API. Fast, cost-effective ($0.15/1k tweets).
- Sign up at https://twitterapi.io
- Get your API key from the dashboard
- No Twitter developer account required

**Instagram**: Optional Xpoz MCP integration (requires Xpoz credits).

#### Reddit OAuth2 Setup (Recommended)

For reliable Reddit scraping, set up OAuth2:

1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app..."
3. Select "script" type
4. Name: `SaaSIdeaFinder` (or any name)
5. Redirect URI: `http://localhost:8080` (not used but required)
6. Copy the Client ID (under the app name) and Client Secret
7. Set environment variables:
   ```bash
   export REDDIT_CLIENT_ID="your_client_id"
   export REDDIT_CLIENT_SECRET="your_client_secret"
   ```

Or add to vault:
```bash
vault kv put secret/skills-apis/reddit client_id="your_id" client_secret="your_secret"
```

#### TwitterAPI.io Setup (for Twitter/X)

To enable Twitter/X scraping via TwitterAPI.io:

1. Go to https://twitterapi.io/
2. Sign up for an account (no credit card required)
3. Copy your API key from the dashboard
4. Add to environment:
   ```bash
   export TWITTERAPI_KEY="your_api_key"
   ```

Or add to vault:
```bash
vault kv put secret/skills-apis/twitterapi/api_key value="your_api_key"
```

#### Xpoz Authentication (Optional - for Instagram only)

To enable Instagram scraping via Xpoz:

1. Go to https://www.xpoz.ai/
2. Sign in with Google
3. Copy your API token
4. Save to `~/.xpoz/token.txt` (or vault: `secret/skills-apis/xpoz/bearer_token`)

See `~/.xpoz/SETUP_INSTRUCTIONS.md` for detailed steps.

**Note**: The skill works without Xpoz - Reddit and Twitter/X are always available via self-hosted/managed APIs.

#### Social Media Lens Configuration

Each lens includes social platform configurations:

| Lens | Reddit | Twitter | Instagram |
|------|--------|---------|-----------|
| DevTools & AI | webdev, programming, MachineLearning | #buildinpublic, #AIdev, #devtools | codelife, developer, aitools |
| Business SaaS | Flipping, Etsy, AmazonFBA | #reseller, #ecommerce, #smallbusiness | etsyshop, smallbusinessowner |
| AI/ML | MachineLearning, ChatGPT, LocalLLaMA | #AI, #LLM, #ChatGPT | aitools, artificialintelligence |
| Data & Analytics | dataengineering, datascience | #dataviz, #analytics | datavisualization, analytics |
| Productivity | devops, nocode, selfhosted | #automation, #nocode | automation, productivity |
| Design & Frontend | webdev, reactjs, css | #frontend, #webdesign | webdesign, uidesign |
| Infrastructure | devops, kubernetes, docker | #DevOps, #Kubernetes | devops, cloudcomputing |

## Quick Start

### Run Full Daily Pipeline

```bash
cd ./skills/saas-idea-finder
python3 scripts/run_full_pipeline.py
```

This automatically:
- Uses today's lens (Monday = Developer Tools, Tuesday = Business SaaS, etc.)
- Discovers trending topics from 9+ sources
- **Intelligently filters** for SaaS opportunities (removes open-source lists, tutorials, etc.)
- **Deduplicates** similar topics across sources
- Deep-researches the top topic (~1-2 minutes)
- Generates Micro-SaaS ideas with viability scoring (0-100)
- Saves outputs to `~/.saas-idea-finder/outputs/`

### Advanced Options

```bash
# Generate more ideas per topic
python3 scripts/run_full_pipeline.py --topics 2

# Include detailed viability analysis
python3 scripts/run_full_pipeline.py --include-viability

# Filter by minimum viability score
python3 scripts/run_full_pipeline.py --min-viability 60

# Filter by pain threshold
python3 scripts/run_full_pipeline.py --pain-threshold 50

### Advanced Options

```bash
# Run with viability scoring (enabled by default)
python3 scripts/run_full_pipeline.py --include-viability

# Filter by pain threshold (minimum pain score 0-100)
python3 scripts/run_full_pipeline.py --pain-threshold 60

# Filter by minimum viability score (0-100)
python3 scripts/run_full_pipeline.py --min-viability 70

# Combine filters for high-quality ideas only
python3 scripts/run_full_pipeline.py --pain-threshold 70 --min-viability 75
```

## How It Works

### Smart Topic Discovery

The skill uses an **intelligent topic extraction system** that:

1. **Filters non-SaaS topics**: Automatically removes open-source lists ("awesome-X"), tutorials, courses, free books, and other non-commercial content
2. **Deduplicates**: Merges similar topics (e.g., "local-first software" and "software: local first") 
3. **Cross-source validation**: Prefers topics appearing in multiple sources
4. **Smart scoring**: Weights engagement metrics differently per source

Topics are excluded if they contain keywords like:
- `free`, `open source`, `tutorial`, `course`, `book`, `roadmap`
- `awesome-list`, `cheatsheet`, `guide`, `curated`
- High-star repos without monetization indicators

### Rotating Lens System

7 lenses rotate daily (Monday-Sunday), each focusing on different domains:

| Day | Lens | Focus |
|-----|------|-------|
| Mon | **Developer Tools** | CLI tools, dev productivity |
| Tue | **Business SaaS** | B2B solutions for SMBs |
| Wed | **AI/ML** | AI-powered tools, LLMs |
| Thu | **Data & Analytics** | BI, dashboards |
| Fri | **Productivity & Automation** | Workflow tools, no-code |
| Sat | **Design & Frontend** | UI components, design systems |
| Sun | **Infrastructure & DevOps** | Cloud, Kubernetes, monitoring |

### 3-Stage Pipeline

**Stage 1: Trend Discovery** - Aggregates from:
- **HackerNews**: Top stories, Show HN, Ask HN (55+ posts)
- **HN Algolia**: Keyword-based search for lens-specific topics (15-20 stories)
- **DEV.to**: Trending articles from developer community (20-30 posts)
- **GitHub**: Trending repositories (30 repos, requires token)
- **arXiv**: Research trends and emerging tech papers (recent submissions)
- **Stack Exchange**: Unanswered questions = pain points (high-engagement questions)
- **GDELT**: Global news events and technology trends (breaking tech news)
- **SerpAPI**: Search validation and keyword trends (Google search insights)
- **YouTube**: Content gaps and trending tech videos (tech tutorial analysis)
- **Reddit (Self-Hosted)**: Subreddit-specific pain points via public JSON API
  - No authentication required
  - Automatic rate limiting and User-Agent rotation
  - Real pain point detection from discussions
- **Twitter/X (TwitterAPI.io)**: Hashtag-based trend discovery
  - Direct REST API integration
  - Fast, cost-effective data extraction
  - Pain point detection from tweets
- **Instagram (Xpoz)** (Optional): Engagement-based trend discovery
  - Cross-platform validation for trending topics
  - Requires Xpoz credits

**Stage 2: Deep Investigation** - GPT Researcher analyzes with 40+ sources

**Stage 3: SaaS Synthesis** - AI generates 3-5 structured Micro-SaaS ideas with:
- Viability scoring (0-100)
- Pain point severity scoring (0-100)
- JTBD (Jobs-to-be-Done) framework analysis
- Market sizing (TAM/SAM/SOM estimates)
- Competition analysis
- Unit economics projections

## Viability Scoring (0-100)

Each generated SaaS idea receives a viability score based on 8 weighted categories:

| Category | Weight | Description |
|----------|--------|-------------|
| **Market Size** | 15% | TAM/SAM/SOM analysis and growth potential |
| **Competition** | 15% | Competitive landscape and differentiation |
| **Technical Feasibility** | 15% | Implementation complexity and tech stack requirements |
| **Pain Severity** | 15% | How critical is the problem being solved |
| **Monetization Potential** | 15% | Revenue model viability and pricing power |
| **Time to MVP** | 10% | Speed of initial product launch |
| **Network Effects** | 10% | Potential for viral growth and user lock-in |
| **Regulatory Risk** | 5% | Compliance requirements and legal barriers |

**Score Interpretation:**
- **90-100**: Exceptional opportunity, low risk
- **80-89**: Strong viability, proceed with confidence
- **70-79**: Good potential, address flagged concerns
- **60-69**: Moderate, requires significant refinement
- **50-59**: Weak viability, major issues to resolve
- **<50**: Not recommended without fundamental changes

## Enhanced Idea Template

Each SaaS idea now includes comprehensive business analysis:

```markdown
### Idea: [Name]

**Viability Score:** XX/100

**One-Liner:** [Clear value proposition]

**Target Users:** [Specific user personas]

**Jobs-to-be-Done (JTBD):**
- When [situation], I want to [motivation], so I can [outcome]

**Pain Point Severity:** XX/100
- Frequency: [How often the pain occurs]
- Intensity: [How severe the pain is]
- Willingness to Pay: [User payment intent]

**Proposed Solution:** [Feature overview]

**Market Size:**
- TAM: $X (Total Addressable Market)
- SAM: $X (Serviceable Addressable Market)
- SOM: $X (Serviceable Obtainable Market)

**Competition:**
| Competitor | Strengths | Weaknesses | Our Differentiation |

**Unit Economics:**
- CAC: $X (Customer Acquisition Cost)
- LTV: $X (Lifetime Value)
- LTV:CAC Ratio: X:1
- Payback Period: X months
- Target MRR: $X

**Red Flags:**
- ⚠️ [Potential risk or concern]

**Success Boosters:**
- ✅ [Factor that increases success probability]

**Validation Steps:**
1. [First validation experiment]
2. [Second validation experiment]
```

## Jobs-to-be-Done Framework

Each idea includes JTBD statements following the Clayton Christensen framework:

> "When [situation], I want to [motivation], so I can [outcome]"

**Example JTBD for a Developer Tool:**
- When I'm reviewing PRs with 50+ files, I want to auto-group changes by logic, so I can focus on architectural issues instead of scrolling

**Why JTBD Matters:**
- Focuses on user motivation, not just features
- Identifies the "job" users "hire" a product to do
- Enables better positioning and messaging
- Guides feature prioritization

## Pain Point Severity Scoring

Each identified pain point receives a severity score (0-100) based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Frequency** | 30% | How often users encounter this pain |
| **Intensity** | 40% | How severely it impacts their work/life |
| **Willingness to Pay** | 30% | How much they'd pay to solve it |

**Severity Levels:**
- **90-100**: Critical pain, immediate action required
- **80-89**: High severity, actively seeking solutions
- **70-79**: Moderate-high, frequent complaints
- **60-69**: Moderate, occasional frustration
- **50-59**: Low-moderate, tolerable inconvenience
- **<50**: Minor annoyance, low priority

## Red Flags & Success Boosters

### Auto-Detection Features

The system automatically identifies factors that impact idea viability:

**Red Flags (Risk Indicators):**
- High competition with low differentiation
- Regulatory complexity or compliance barriers
- Long sales cycles for B2B ideas
- Technical complexity requiring specialized expertise
- Low willingness to pay relative to CAC
- Network effects required for basic functionality

**Success Boosters (Positive Indicators):**
- Clear, specific target user segment
- Existing budget for the problem category
- Growing market with tailwinds
- Product-led growth potential
- Integration with existing workflows
- Recurring revenue model fit

## Individual Stage Usage

### Discover Trends

```bash
python3 scripts/discover_trends.py --lens "AI/ML Wednesday" --limit 5
```

### Investigate Topic

```bash
python3 scripts/investigate_topic.py --topic "local-first software" --lens "Developer Tools Monday"
```

### Generate SaaS Ideas

```bash
python3 scripts/synthesize_saas_ideas.py --research path/to/research.md --num-ideas 5
```

## Output Locations

```
~/.saas-idea-finder/outputs/
├── 2026-02-08_discover/trends.json
├── 2026-02-08_research/topic.md
└── 2026-02-08_ideas/topic_ideas.md
```

## Error Handling

- **Missing API Keys**: Add to your environment, shell startup file, or secret store
- **All Sources Failed**: Check internet, try --since 14
- **Already Analyzed**: Use --force to re-analyze
- **Rate Limits Exceeded**: Wait and retry, or check API quotas

All errors return JSON: `{"success": false, "error": "type", "message": "solution"}`

## Usage Examples

### Daily Automated

```bash
# Crontab: Run every day at 9 AM
0 9 * * * cd /path/to/skills/saas-idea-finder && python3 scripts/run_full_pipeline.py
```

### Ad-Hoc Research

```bash
python3 scripts/run_full_pipeline.py --topics 2 --lens "Business SaaS Tuesday"
```

### Filter by Viability

```bash
# Only show ideas with viability score >= 75
python3 scripts/run_full_pipeline.py --min-viability 75 --include-viability
```

### High-Pain-Point Focus

```bash
# Only show ideas addressing pain points >= 70 severity
python3 scripts/run_full_pipeline.py --pain-threshold 70
```

### Comprehensive Analysis

```bash
# Full pipeline with deep research and high-quality filtering
python3 scripts/run_full_pipeline.py \
  --breadth 3 \
  --depth 2 \
  --pain-threshold 65 \
  --min-viability 70 \
  --include-viability
```

### Validate Specific Trend

```bash
# Research a specific topic and generate ideas
python3 scripts/investigate_topic.py \
  --topic "AI code review tools" \
  --lens "Developer Tools Monday" \
  --output ~/.saas-idea-finder/outputs/custom_research.md

python3 scripts/synthesize_saas_ideas.py \
  --research ~/.saas-idea-finder/outputs/custom_research.md \
  --num-ideas 5
```
