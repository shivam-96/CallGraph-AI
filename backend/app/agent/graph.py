"""
LangGraph Agent — ReAct agent with identity/context injection.
Loads YAML configs and builds a system prompt dynamically.
"""

import logging
import yaml
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from app.tools.web_search import web_search
from app.tools.calculator import calculator
from app.tools.datetime_tool import get_datetime

logger = logging.getLogger(__name__)

# ─── Config Loading ───────────────────────────────────────────────

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def load_yaml(filename: str) -> dict:
    """Load a YAML config file from the config directory."""
    path = CONFIG_DIR / filename
    if not path.exists():
        logger.warning(f"Config file not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_system_prompt(identity: dict, context: dict) -> str:
    """Build the system prompt from identity + context YAML data."""
    parts = []

    # Identity section
    parts.append(f"You are {identity.get('name', 'an AI assistant')}.")
    parts.append(f"Your role: {identity.get('role', 'Assistant')}.")
    parts.append(f"Your tone: {identity.get('tone', 'professional')}.")

    traits = identity.get("personality_traits", [])
    if traits:
        parts.append(f"Personality: {', '.join(traits)}.")

    style = identity.get("speaking_style", "")
    if style:
        parts.append(f"Speaking style: {style}.")

    rules = identity.get("behavior_rules", [])
    if rules:
        parts.append("Behavior rules:")
        for rule in rules:
            parts.append(f"  - {rule}")

    # Context section
    dk = context.get("domain_knowledge", {})
    if isinstance(dk, dict):
        for key, value in dk.items():
            parts.append(f"{key.replace('_', ' ').title()}: {value}")
    elif isinstance(dk, str):
        parts.append(f"Domain knowledge: {dk}")

    strategies = context.get("conversation_strategies", [])
    if strategies:
        parts.append("Conversation strategies:")
        for s in strategies:
            parts.append(f"  - {s}")

    tips = context.get("tips", [])
    if tips:
        parts.append("Tips:")
        for t in tips:
            parts.append(f"  - {t}")

    constraints = context.get("constraints", [])
    if constraints:
        parts.append("Constraints:")
        for c in constraints:
            parts.append(f"  - {c}")

    # Voice-specific instruction
    parts.append(
        "\nIMPORTANT: This is a VOICE conversation. Keep your responses SHORT "
        "and natural — 1-3 sentences max. Speak as if talking to someone on a "
        "phone call. Do NOT use markdown, bullet points, or formatting."
    )

    return "\n".join(parts)


# ─── Agent Creation ───────────────────────────────────────────────

# All available tools
TOOLS = [web_search, calculator, get_datetime]


def create_agent(openai_api_key: str):
    """Create the LangGraph ReAct agent with loaded config."""
    # Load config
    identity = load_yaml("identity.yaml")
    context = load_yaml("context.yaml")
    system_prompt = build_system_prompt(identity, context)
    logger.info(f"System prompt built ({len(system_prompt)} chars)")

    # LLM — gpt-4o-mini for speed + cost efficiency
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=openai_api_key,
        temperature=0.3,   # Lower = faster token sampling
        max_tokens=150,    # Shorter = fewer tokens = faster TTS
    )

    # Create ReAct agent
    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        prompt=system_prompt,
    )

    logger.info("LangGraph agent created")
    return agent, system_prompt


async def run_agent(agent, conversation_history: list[dict], user_text: str) -> str:
    """
    Run the agent with conversation history and new user input.
    Returns the agent's text response.
    """
    # Build messages list
    messages = []
    for msg in conversation_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # Add current user message
    messages.append(HumanMessage(content=user_text))

    logger.info(f"Running agent with {len(messages)} messages")

    try:
        result = await agent.ainvoke({"messages": messages})
        # Get the last AI message
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        if ai_messages:
            response = ai_messages[-1].content
            logger.info(f"Agent response: {response[:100]}...")
            return response
        return "I'm sorry, I couldn't generate a response."
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"I encountered an error: {str(e)}"
