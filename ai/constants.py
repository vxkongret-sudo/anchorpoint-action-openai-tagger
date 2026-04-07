# Claude Haiku 4.5 pricing
INPUT_TOKEN_PRICE = 0.000001      # $1.00 per 1M tokens
OUTPUT_TOKEN_PRICE = 0.000005     # $5.00 per 1M tokens

# Image tokens are counted as input tokens by Anthropic
# A small image (~128px) is roughly 1600 tokens
IMAGE_TOKENS_ESTIMATE = 1600

MAX_RETRIES = 5
CLAUDE_REQUEST_TIME = 3.0
ATTRIBUTE_UPDATE_TIME = 0.3

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
