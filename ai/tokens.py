def count_tokens(text):
    """Estimate token count. Approximation: ~4 characters per token."""
    return len(text) // 4
