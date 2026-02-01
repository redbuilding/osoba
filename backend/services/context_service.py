from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from db.crud import get_conversation_by_id, get_all_conversations
import db.profiles_crud as profiles_crud
from core.config import get_logger

logger = get_logger("context_service")

# Context size limits to prevent token overflow
MAX_PROFILE_CHARS = 200
# Allow up to 5 chats at 500 chars each
MAX_CONVERSATION_CONTEXT_CHARS = 2500
MAX_TOTAL_CONTEXT_CHARS = 2700
MAX_PINNED_CONVERSATIONS = 5
PROFILE_BUDGET = 200
PINNED_TOTAL_BUDGET = 2500

# Domain lexicons (expandable)
DOMAIN_LEXICONS = {
    "marketing": {
        "campaign", "creative", "copy", "cpc", "cpa", "roas", "pixel", "tag manager",
        "utm", "audience", "retarget", "performance max", "landing page", "cta", "funnel",
        "search terms", "keywords", "ad group", "impressions", "click-through", "conversion"
    },
    "sales": {
        "qualify", "demo", "present", "objection", "close", "pipeline", "icp", "mql",
        "sql", "discovery", "proposal", "renewal", "trial", "follow-up", "quota", "ltv"
    },
    "business": {
        "kpi", "budget", "pricing", "margin", "revenue", "cost", "forecast", "roadmap",
        "stakeholder", "risk", "milestone", "launch", "go-to-market", "objective", "okr"
    },
    "programming": {
        "python", "javascript", "html", "css", "api", "endpoint", "request", "response",
        "pandas", "numpy", "matplotlib", "seaborn", "fastapi", "react", "node", "sql",
        "postgres", "mysql", "docker", "kubernetes", "git", "build", "deploy", "test",
        "authentication", "authorization", "hashing", "bcrypt"
    },
}

ACTION_KEYWORDS = {
    "decide", "decided", "choose", "chose", "select", "selected", "implement", "implemented",
    "resolve", "resolved", "will", "should", "next", "plan", "todo", "set up", "configure",
    "deploy", "analyze", "design", "outline", "sketch", "optimize"
}

async def get_user_context(user_id: str = "default") -> Dict[str, Any]:
    """Get comprehensive user context including profile and pinned conversations."""
    try:
        context = {
            "profile_context": "",
            "conversation_context": "",
            "total_chars": 0
        }
        
        # Get profile context
        profile_context = await get_profile_context(user_id)
        if profile_context:
            context["profile_context"] = profile_context[:MAX_PROFILE_CHARS]
        
        # Get conversation context
        conversation_context = await get_conversation_context(user_id)
        if conversation_context:
            context["conversation_context"] = conversation_context[:MAX_CONVERSATION_CONTEXT_CHARS]
        
        # Calculate total context size
        context["total_chars"] = len(context["profile_context"]) + len(context["conversation_context"])
        
        return context
    except Exception as e:
        logger.error(f"Error getting user context for {user_id}: {e}")
        return {"profile_context": "", "conversation_context": "", "total_chars": 0}

async def get_profile_context(user_id: str = "default") -> str:
    """Generate profile context string for system prompt injection."""
    try:
        profile = profiles_crud.get_active_profile(user_id)
        if not profile:
            return ""
        
        context_parts = []
        
        # Add role information
        if profile.get("role"):
            context_parts.append(f"User role: {profile['role']}")
        
        # Add expertise areas
        expertise = profile.get("expertise_areas", [])
        if expertise:
            context_parts.append(f"Expertise: {', '.join(expertise)}")
        
        # Add current projects
        if profile.get("current_projects"):
            context_parts.append(f"Current projects: {profile['current_projects']}")
        
        # Add communication style
        if profile.get("communication_style"):
            context_parts.append(f"Preferred communication: {profile['communication_style']}")
        
        return " | ".join(context_parts)
    except Exception as e:
        logger.error(f"Error getting profile context for {user_id}: {e}")
        return ""

async def get_conversation_context(user_id: str = "default") -> str:
    """Get context from pinned conversations."""
    try:
        # Get pinned conversations for user
        pinned_conversations = get_pinned_conversations(user_id)
        if not pinned_conversations:
            return ""
        
        # Allocate budget fairly across up to 5 pins
        selected = pinned_conversations[:MAX_PINNED_CONVERSATIONS]
        n = len(selected)
        if n == 0:
            return ""
        per_chat_budget = max(100, PINNED_TOTAL_BUDGET // n)

        # Compose sentence-aware snippets
        snippets: list[str] = []
        leftovers = 0

        for conv in selected:
            title = conv.get("title", "Untitled")
            conv_id = str(conv.get("_id", ""))
            summary = conv.get("summary", "")
            base = f"{title}: {summary}" if summary else title
            trimmed = _trim_to_sentence_budget(base, per_chat_budget)
            used = len(trimmed)
            if used < per_chat_budget:
                leftovers += per_chat_budget - used
            snippets.append(trimmed)

        # Distribute leftovers to more recent pins (already in updated order)
        if leftovers > 0 and snippets:
            augmented: list[str] = []
            for idx, conv in enumerate(selected):
                if leftovers <= 0:
                    augmented.append(snippets[idx])
                    continue
                title = conv.get("title", "Untitled")
                summary = conv.get("summary", "")
                base = f"{title}: {summary}" if summary else title
                target = len(snippets[idx]) + min(leftovers, 120)
                extended = _trim_to_sentence_budget(base, target)
                leftovers -= max(0, len(extended) - len(snippets[idx]))
                augmented.append(extended)
            snippets = augmented

        result = " | ".join(snippets)
        # Keep legacy overall cap too (defensive)
        return result[:MAX_CONVERSATION_CONTEXT_CHARS]
    except Exception as e:
        logger.error(f"Error getting conversation context for {user_id}: {e}")
        return ""

def get_pinned_conversations(user_id: str = "default") -> List[Dict[str, Any]]:
    """Get conversations pinned for context by user."""
    try:
        from db.crud import get_pinned_conversations as get_pinned_from_db
        return get_pinned_from_db(user_id, MAX_PINNED_CONVERSATIONS)
    except Exception as e:
        logger.error(f"Error getting pinned conversations for {user_id}: {e}")
        return []

def generate_conversation_summary(conversation_data: Dict[str, Any]) -> str:
    """Generate an informative, sentence-aware summary (~250–350 chars).

    Pulls key lines from the last 5 messages: topic/intent, decisions/outcomes,
    next steps, and notable tools/data.
    """
    try:
        messages = conversation_data.get("messages", [])
        if not messages:
            return ""

        # Expand the window for more signal
        window = messages[-30:]

        # Separate user and assistant contents (cleaned)
        user_lines_raw = [m.get("content", "") for m in window if m.get("role") == "user" and m.get("content")]
        asst_lines_raw = [m.get("content", "") for m in window if m.get("role") == "assistant" and m.get("content")]
        user_lines = [_clean_text(x) for x in user_lines_raw if x]
        asst_lines = [_clean_text(x) for x in asst_lines_raw if x]

        # Sentence helpers
        def first_sentence(text: str) -> str:
            s = text.strip().split(". ")[0].strip()
            return s if s else text.strip()

        def cap_sentence(s: str) -> str:
            s = s.strip()
            if not s:
                return s
            if s[-1] not in ".!?":
                s += "."
            return s

        # 1) Topic/intent (from most recent user message)
        topic = ""
        if user_lines:
            topic = first_sentence(user_lines[-1])

        # 2) Decisions/outcomes (from assistant)
        decision = ""
        decision_keywords = [
            "decided", "resolved", "we will", "we'll", "use ", "chose ", "selected ", "implemented", "fixed"
        ]
        for line in reversed(asst_lines):
            lower = line.lower()
            if any(k in lower for k in decision_keywords):
                decision = first_sentence(line)
                break
        if not decision and asst_lines:
            decision = first_sentence(asst_lines[-1])

        # 3) Next steps (scan user + assistant)
        next_steps = ""
        next_keywords = ["next", "plan", "todo", "will", "should", "follow up", "then"]
        for line in reversed(user_lines + asst_lines):
            lower = line.lower()
            if any(k in lower for k in next_keywords):
                next_steps = first_sentence(line)
                break

        # 4) Steps/bullets/numbered items
        bullets = _extract_bullets(user_lines + asst_lines, max_items=5)

        # 5) Tools/data mentions
        tool_list = [
            "pandas", "numpy", "matplotlib", "seaborn", "scikit-learn", "requests", "fastapi",
            "react", "javascript", "python", "sql", "postgres", "mysql", "csv", "api"
        ]
        mentioned = []
        joined = " ".join(window_line for window_line in (user_lines + asst_lines))
        low_all = joined.lower()
        for t in tool_list:
            if t in low_all and t not in mentioned:
                mentioned.append(t)
        tools = ", ".join(mentioned[:3])

        # Build base parts from quick signals
        parts = []
        if topic:
            parts.append(cap_sentence(topic))
        if decision and decision.lower() != (topic or "").lower():
            parts.append(cap_sentence(decision))
        if bullets:
            # Include a condensed steps line
            steps_line = "; ".join(bullets)
            parts.append(cap_sentence(f"Key steps: {steps_line}"))
        if next_steps and next_steps.lower() not in (topic + " " + decision).lower():
            parts.append(cap_sentence(next_steps))
        if tools:
            parts.append(f"Tools/data: {tools}.")

        # Candidate sentences pool for scoring (user + assistant)
        sentences_pool = []
        for line in user_lines + asst_lines:
            for s in _split_sentences(line):
                s = s.strip()
                if len(s.split()) < 5:
                    continue
                sentences_pool.append(s)

        # Score and select diverse sentences to enrich summary
        scored = [(s, _score_sentence(s)) for s in sentences_pool]
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = _select_diverse_sentences(scored, max_items=3, diversity=0.6)
        if selected:
            parts.append(" ".join(cap_sentence(s) for s in selected))

        summary = " ".join([p for p in parts if p])
        if not summary:
            # Fallback to simple hybrid of last 5
            basic = []
            for msg in window:
                content = msg.get("content", "")
                if not content:
                    continue
                if msg.get("role") == "user":
                    basic.append(first_sentence(content))
                else:
                    basic.append(first_sentence(content))
            summary = ". ".join(basic)

        # Ensure minimum substance by appending more bullets if short
        if len(summary) < 220 and bullets:
            extra = "; ".join(bullets[:3])
            summary = (summary + " " + cap_sentence(f"Additional steps: {extra}")) if summary else cap_sentence(f"Additional steps: {extra}")

        # Target up to 500 chars; trim by sentence/word boundaries
        return _trim_to_sentence_budget(summary, 500)
    except Exception as e:
        logger.error(f"Error generating conversation summary: {e}")
        return ""

def _extract_assistant_key_points(content: str) -> str:
    """Extract key points from assistant responses for summary."""
    try:
        # Look for common solution patterns
        content_lower = content.lower()
        
        # Extract code-related solutions
        if "```" in content:
            return "provided code example"
        
        # Extract tool/library recommendations
        tools = ["pandas", "numpy", "matplotlib", "seaborn", "requests", "fastapi", "react", "python", "javascript", "sql"]
        mentioned_tools = [tool for tool in tools if tool in content_lower]
        if mentioned_tools:
            return f"use {', '.join(mentioned_tools[:2])}"
        
        # Extract action words that indicate solutions
        action_patterns = [
            ("install", "installation steps"),
            ("configure", "configuration help"),
            ("create", "creation guide"),
            ("fix", "troubleshooting"),
            ("debug", "debugging help"),
            ("optimize", "optimization tips"),
            ("deploy", "deployment guide")
        ]
        
        for pattern, description in action_patterns:
            if pattern in content_lower:
                return description
        
        # Extract first sentence as fallback (truncated)
        first_sentence = content.split('.')[0].strip()
        if len(first_sentence) > 50:
            first_sentence = first_sentence[:47] + "..."
        
        return first_sentence if first_sentence else ""
        
    except Exception as e:
        logger.error(f"Error extracting assistant key points: {e}")
        return ""

def format_context_for_system_prompt(context: Dict[str, Any]) -> str:
    """Format user context for injection into system prompt."""
    try:
        prompt_parts = []
        
        if context.get("profile_context"):
            prompt_parts.append(f"User Context: {context['profile_context']}")
        
        if context.get("conversation_context"):
            prompt_parts.append(f"Previous Conversations: {context['conversation_context']}")
        
        if prompt_parts:
            return "Context Information: " + " | ".join(prompt_parts)
        
        return ""
    except Exception as e:
        logger.error(f"Error formatting context for system prompt: {e}")
        return ""

def _trim_to_sentence_budget(text: str, budget: int) -> str:
    """Trim text to <= budget, preferring to end at a sentence boundary."""
    if len(text) <= budget:
        return text
    candidate = text[:budget]
    # Find last sentence end within candidate
    for punct in ['. ', '! ', '? ']:
        idx = candidate.rfind(punct)
        if idx != -1 and idx >= budget * 2 // 3:  # avoid trimming too early
            return candidate[:idx+1].strip()
    # Fallback to word boundary
    ws = candidate.rfind(' ')
    if ws != -1 and ws >= budget * 2 // 3:
        return candidate[:ws].strip()
    return candidate.strip()

def _clean_text(text: str) -> str:
    """Remove markdown/html and collapse whitespace."""
    import re
    # Strip custom indicators/HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove markdown bullets/headers artifacts for sentence extraction
    text = re.sub(r"^[#>*\-\d\.\)\s]+", "", text.strip())
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _extract_bullets(lines: list[str], max_items: int = 5) -> list[str]:
    import re
    bullets = []
    for line in lines:
        # grab inline lists or obvious bullet-like fragments
        for part in re.split(r"[\n•\-•]", line):
            p = part.strip()
            if not p:
                continue
            # Numbered or imperative phrases that look like steps
            if re.match(r"^(\d+\.|\d+\)|step\s*\d+|build|configure|implement|deploy|analyze|design|outline|sketch|qualify|present|handle|close)\b", p, re.I):
                bullets.append(_clean_text(p))
            elif len(p.split()) >= 4 and any(k in p.lower() for k in ["step", "phase", "ensure", "then", "after"]):
                bullets.append(_clean_text(p))
            if len(bullets) >= max_items:
                break
        if len(bullets) >= max_items:
            break
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for b in bullets:
        if b.lower() in seen:
            continue
        seen.add(b.lower())
        uniq.append(b)
    return uniq[:max_items]

def _split_sentences(text: str) -> list[str]:
    import re
    # Split on sentence terminators but keep reasonable chunks
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Avoid carrying markdown headings/bullets into sentences
        out.append(_clean_text(p))
    return out

def _tokenize(text: str) -> set[str]:
    import re
    tokens = re.findall(r"[a-zA-Z0-9_\-]+", text.lower())
    return set(tokens)

def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0

def _score_sentence(s: str) -> float:
    """Score a sentence using action keywords, domain lexicons, structure, and length."""
    s_low = s.lower()
    score = 0.0
    # Action/decision cues
    score += sum(1.0 for k in ACTION_KEYWORDS if k in s_low)
    # Domain lexicons weighting
    for cat, words in DOMAIN_LEXICONS.items():
        hits = sum(1 for w in words if w in s_low)
        if hits:
            score += min(2.0, 0.5 * hits)
    # Numeric/step cues
    if any(ch.isdigit() for ch in s):
        score += 0.5
    # Link presence (often valuable)
    if "http://" in s_low or "https://" in s_low or "www." in s_low:
        score += 1.0
    # Prefer assistant-like structure (lists, bold keywords, etc.)
    if ":" in s or "—" in s or " - " in s:
        score += 0.3
    # Length sweet spot (80–180 chars)
    L = len(s)
    if 80 <= L <= 180:
        score += 0.8
    elif L < 50:
        score -= 0.5
    return score

def _select_diverse_sentences(scored: list[tuple[str, float]], max_items: int = 3, diversity: float = 0.6) -> list[str]:
    """Greedy MMR-like selection using Jaccard overlap as redundancy penalty."""
    selected: list[str] = []
    for s, base_score in scored:
        if len(selected) >= max_items:
            break
        penalty = max((_jaccard(s, t) for t in selected), default=0.0)
        mmr = base_score - diversity * penalty
        # Simple threshold to avoid junk
        if mmr > 0.2:
            selected.append(s)
    return selected

async def _generate_and_store_summary(conv_id: str) -> str:
    """Generate summary for a conversation and store it in the database."""
    try:
        # Get full conversation with messages
        conversation = get_conversation_by_id(conv_id)
        if not conversation:
            return ""
        
        # Generate summary using existing function
        summary = generate_conversation_summary(conversation)
        if not summary:
            return ""
        
        # Store summary in database
        from db.crud import update_conversation_summary
        success = update_conversation_summary(conv_id, summary)
        if success:
            logger.info(f"Generated and stored summary for conversation {conv_id}")
            return summary
        else:
            logger.error(f"Failed to store summary for conversation {conv_id}")
            return ""
            
    except Exception as e:
        logger.error(f"Error generating and storing summary for {conv_id}: {e}")
        return ""
