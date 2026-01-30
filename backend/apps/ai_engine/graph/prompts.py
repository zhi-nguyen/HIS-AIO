# apps/ai_engine/graph/prompts.py
"""
Prompt Templates for Medical AI Agents

This file now acts as a registry, importing prompts from specific agent modules.
"""

from typing import Optional, Dict, Any

# Import prompts from new locations
from apps.ai_engine.agents.utils import GLOBAL_LANGUAGE_RULE
from apps.ai_engine.agents.clinical_agent.prompts import CLINICAL_PROMPT
from apps.ai_engine.agents.triage_agent.prompts import TRIAGE_PROMPT, TriageCode
from apps.ai_engine.agents.consultant_agent.prompts import CONSULTANT_PROMPT
from apps.ai_engine.agents.pharmacist_agent.prompts import PHARMACIST_PROMPT, InteractionSeverity
from apps.ai_engine.agents.paraclinical_agent.prompts import PARACLINICAL_PROMPT, CriticalValueCode, SampleStatus
from apps.ai_engine.agents.marketing_agent.prompts import MARKETING_AGENT_PROMPT
from apps.ai_engine.agents.summarize_agent.prompts import SUMMARIZE_AGENT_PROMPT
from apps.ai_engine.agents.core_agent.prompts import SUPERVISOR_SYSTEM_PROMPT

# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# Aliases cho các tên cũ (để không break code cũ nếu có)
CLINICAL_AGENT_PROMPT = CLINICAL_PROMPT
TRIAGE_AGENT_PROMPT = TRIAGE_PROMPT
CONSULTANT_AGENT_PROMPT = CONSULTANT_PROMPT
PHARMACIST_AGENT_PROMPT = PHARMACIST_PROMPT
PARACLINICAL_AGENT_PROMPT = PARACLINICAL_PROMPT
SUPERVISOR_AGENT_PROMPT = SUPERVISOR_SYSTEM_PROMPT

# =============================================================================
# PROMPT FACTORY (Giữ nguyên cho backward compatibility)
# =============================================================================

class PromptFactory:
    """
    Factory class for generating agent-specific system prompts.
    
    Centralizes prompt management and ensures consistent language rules
    across all agents.
    """
    
    PROMPT_MAP = {
        "clinical": CLINICAL_PROMPT,
        "triage": TRIAGE_PROMPT,
        "consultant": CONSULTANT_PROMPT,
        "pharmacist": PHARMACIST_PROMPT,
        "paraclinical": PARACLINICAL_PROMPT,
        "supervisor": SUPERVISOR_SYSTEM_PROMPT,
        "summarize": SUMMARIZE_AGENT_PROMPT,
        "marketing": MARKETING_AGENT_PROMPT,
    }
    
    @classmethod
    def get_prompt(cls, agent_type: str, additional_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate the complete system prompt for an agent.
        
        Args:
            agent_type: Type of agent ('clinical', 'triage', etc.)
            additional_context: Optional additional context to inject
        
        Returns:
            Complete system prompt string
        """
        base_prompt = cls.PROMPT_MAP.get(agent_type.lower())
        
        if not base_prompt:
            raise ValueError(f"Unknown agent type: {agent_type}. "
                           f"Available: {list(cls.PROMPT_MAP.keys())}")
        
        # Add additional context if provided
        if additional_context:
            context_str = "\n\n## Ngữ Cảnh Bổ Sung\n"
            for key, value in additional_context.items():
                context_str += f"- {key}: {value}\n"
            base_prompt += context_str
        
        return base_prompt
    
    @classmethod
    def get_all_prompts(cls) -> Dict[str, str]:
        """Get all prompts."""
        return dict(cls.PROMPT_MAP)
    
    @classmethod
    def list_agents(cls) -> list:
        """List all available agent types."""
        return list(cls.PROMPT_MAP.keys())


def get_system_prompt(agent_type: str, **kwargs) -> str:
    """
    Convenience function to get agent system prompt.
    
    Args:
        agent_type: Type of agent
        **kwargs: Additional context to inject
    
    Returns:
        Complete system prompt
    """
    return PromptFactory.get_prompt(agent_type, kwargs if kwargs else None)
