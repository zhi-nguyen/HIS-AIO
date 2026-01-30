"""
Prompt Caching with LRU Cache

Caches static prompts and templates to avoid repeated string operations
and template loading during agent execution.
"""

from functools import lru_cache
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def get_system_prompt(agent_name: str) -> str:
    """
    Get cached system prompt for an agent.
    
    Caches system prompts to avoid repeated imports and string operations.
    
    Args:
        agent_name: Name of the agent (supervisor, clinical, pharmacist, etc.)
        
    Returns:
        Formatted system prompt string
    """
    try:
        # Import agent-specific prompts lazily
        if agent_name == "supervisor":
            from apps.ai_engine.graph.prompts import SUPERVISOR_PROMPT
            return SUPERVISOR_PROMPT
        elif agent_name == "clinical":
            from apps.ai_engine.agents.clinical_agent.prompts import CLINICAL_PROMPT
            return CLINICAL_PROMPT
        elif agent_name == "triage":
            from apps.ai_engine.agents.triage_agent.prompts import TRIAGE_PROMPT
            return TRIAGE_PROMPT
        elif agent_name == "consultant":
            from apps.ai_engine.agents.consultant_agent.prompts import CONSULTANT_PROMPT
            return CONSULTANT_PROMPT
        elif agent_name == "pharmacist":
            from apps.ai_engine.agents.pharmacist_agent.prompts import PHARMACIST_PROMPT
            return PHARMACIST_PROMPT
        elif agent_name == "paraclinical":
            from apps.ai_engine.agents.paraclinical_agent.prompts import PARACLINICAL_PROMPT
            return PARACLINICAL_PROMPT
        elif agent_name == "summarize":
            from apps.ai_engine.agents.summarize_agent.prompts import SUMMARIZE_PROMPT
            return SUMMARIZE_PROMPT
        elif agent_name == "marketing":
            from apps.ai_engine.agents.marketing_agent.prompts import MARKETING_PROMPT
            return MARKETING_PROMPT
        else:
            logger.warning(f"Unknown agent: {agent_name}")
            return ""
    except ImportError as e:
        logger.error(f"Failed to import prompt for {agent_name}: {e}")
        return ""


@lru_cache(maxsize=64)
def get_tool_description(tool_name: str) -> str:
    """
    Get cached tool description.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool description string
    """
    tool_descriptions = {
        "search_medical_knowledge": "Tìm kiếm thông tin y khoa trong cơ sở dữ liệu kiến thức",
        "check_drug_interaction": "Kiểm tra tương tác giữa các loại thuốc",
        "analyze_lab_results": "Phân tích kết quả xét nghiệm",
        "search_icd10": "Tra cứu mã bệnh ICD-10",
        "create_lab_order": "Tạo phiếu yêu cầu xét nghiệm",
        "track_sample_status": "Theo dõi trạng thái mẫu xét nghiệm",
        "escalate_to_human": "Chuyển tiếp cho nhân viên y tế",
    }
    return tool_descriptions.get(tool_name, f"Tool: {tool_name}")


@lru_cache(maxsize=16)
def get_routing_prompt() -> str:
    """
    Get cached supervisor routing prompt.
    
    Returns:
        Routing decision prompt template
    """
    return """Based on the user's message, determine which agent should handle it:
- clinical: Medical symptoms, diagnoses, treatment questions
- triage: Emergency assessment, urgency classification
- pharmacist: Drug interactions, medication questions
- paraclinical: Lab tests, imaging orders, results
- consultant: General inquiries, appointments, hospital info
- summarize: Request for summary of conversation
- marketing: Service promotions, pricing questions
- end: Greeting, goodbye, or conversation complete

Respond with the agent name only."""


def clear_prompt_cache() -> None:
    """
    Clear all cached prompts.
    
    Useful when prompts are updated dynamically or for testing.
    """
    get_system_prompt.cache_clear()
    get_tool_description.cache_clear()
    get_routing_prompt.cache_clear()
    logger.info("Prompt cache cleared")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for monitoring.
    
    Returns:
        Dict with cache hit/miss stats for each cached function
    """
    return {
        "system_prompt": {
            "hits": get_system_prompt.cache_info().hits,
            "misses": get_system_prompt.cache_info().misses,
            "size": get_system_prompt.cache_info().currsize,
            "maxsize": get_system_prompt.cache_info().maxsize,
        },
        "tool_description": {
            "hits": get_tool_description.cache_info().hits,
            "misses": get_tool_description.cache_info().misses,
            "size": get_tool_description.cache_info().currsize,
            "maxsize": get_tool_description.cache_info().maxsize,
        },
        "routing_prompt": {
            "hits": get_routing_prompt.cache_info().hits,
            "misses": get_routing_prompt.cache_info().misses,
            "size": get_routing_prompt.cache_info().currsize,
            "maxsize": get_routing_prompt.cache_info().maxsize,
        },
    }
