"""Model prefix formatting for message responses."""


def format_prefix(model_full: str, thinking_level: str = "off") -> str:
    """
    Generate message prefix with thinking level.

    Args:
        model_full: Full model identifier (e.g., "anthropic/claude-opus-4-5").
        thinking_level: Current thinking level (low, medium, high, off).

    Returns:
        Formatted prefix string.
    """
    return f"thinking level: {thinking_level}\n\n"


def get_model_short(model_full: str) -> str:
    """
    Extract short model name from full identifier.

    Args:
        model_full: Full model identifier (e.g., "anthropic/claude-opus-4-5").

    Returns:
        Short model name (e.g., "claude-opus-4-5").
    """
    return model_full.split("/")[-1]


def get_provider_name(model_full: str) -> str:
    """
    Get provider name from model identifier.

    Args:
        model_full: Full model identifier (e.g., "anthropic/claude-opus-4-5").

    Returns:
        Provider name (e.g., "anthropic").
    """
    if "/" in model_full:
        return model_full.split("/")[0]
    return "unknown"
