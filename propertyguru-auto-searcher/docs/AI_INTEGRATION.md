# 🤖 AI Integration Guide

## Overview

The PropertyGuru Auto Searcher now uses **OpenAI GPT** for natural language understanding and intent parsing. This replaces the previous regex-based approach with a more powerful and flexible AI-driven solution.

## Architecture

### Before: Regex-Based Parsing ❌

```
User Query → Regex Patterns → Structured Filters
              (brittle, limited)
```

**Problems:**
- Hard to maintain complex regex patterns
- Cannot understand context or semantics
- Requires manual pattern updates for new cases
- Limited to predefined patterns

### After: AI-Powered Parsing ✅

```
User Query → OpenAI GPT → Validated Structured Response → Filters
              (intelligent, flexible)
```

**Benefits:**
- Natural language understanding
- Context-aware parsing
- Handles variations automatically
- Strict response validation

## Implementation Details

### 1. Structured Response Schema

We use a **strict Go struct** (similar to Python's Pydantic) to validate AI responses:

```go
type AIIntentResponse struct {
    PriceMin       *float64 `json:"price_min,omitempty" validate:"omitempty,gte=0"`
    PriceMax       *float64 `json:"price_max,omitempty" validate:"omitempty,gte=0"`
    Bedrooms       *int     `json:"bedrooms,omitempty" validate:"omitempty,gte=0,lte=10"`
    Bathrooms      *int     `json:"bathrooms,omitempty" validate:"omitempty,gte=0,lte=10"`
    UnitType       *string  `json:"unit_type,omitempty" validate:"omitempty,oneof=HDB Condo Landed Executive"`
    Location       *string  `json:"location,omitempty" validate:"omitempty,min=2,max=100"`
    MRTDistanceMax *int     `json:"mrt_distance_max,omitempty" validate:"omitempty,gte=0,lte=5000"`
    BuildYearMin   *int     `json:"build_year_min,omitempty" validate:"omitempty,gte=1900,lte=2100"`
    Keywords       []string `json:"keywords,omitempty" validate:"omitempty,dive,min=1,max=50"`
}
```

### 2. Validation Rules

**Business Logic Validation:**
- Price range: `price_min <= price_max`
- Unit type: Must be one of `HDB | Condo | Landed | Executive`
- Numeric ranges: Bedrooms/bathrooms (0-10), MRT distance (0-5000m), Build year (1900-2100)

**Type Safety:**
- All fields are properly typed
- Optional fields use pointers (`*float64`, `*int`, `*string`)
- JSON unmarshaling with error handling

### 3. OpenAI Integration

**Configuration:**
```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_CHAT_MODEL=gpt-3.5-turbo              # Model for chat/intent parsing
OPENAI_EMBEDDING_MODEL=text-embedding-3-small # Model for embeddings
OPENAI_EMBEDDING_DIMENSIONS=1536
OPENAI_BATCH_SIZE=100
OPENAI_TIMEOUT=30
```

**Supported Models:**
- **Chat Models**: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo-preview`, or any OpenAI-compatible chat model
- **Embedding Models**: `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`

**Features:**
- Chat completion for intent parsing
- Embedding generation for vector search
- Batch processing support
- Error handling and fallback

### 4. System Prompt Engineering

The AI is given a comprehensive system prompt that:
- Defines all extractable fields
- Specifies data types and formats
- Provides Singapore-specific context
- Includes examples for few-shot learning
- Enforces JSON-only output

Example prompt excerpt:
```
You are a real estate search assistant in Singapore.
Extract: price_min, price_max, bedrooms, bathrooms, unit_type, location, ...
Rules:
- All property data is in English
- Respond ONLY with valid JSON
- Unit types: "HDB" | "Condo" | "Landed" | "Executive"
- Prices in SGD: "1.5M" = 1500000
```

## Code Structure

### New Files

1. **`internal/service/openai.go`**
   - OpenAI client wrapper
   - Chat completion API
   - Embedding API
   - Response validation

2. **`internal/config/config.go` (updated)**
   - Added `OpenAIConfig` struct
   - Environment variable loading

3. **`cmd/server/main.go` (updated)**
   - Initialize OpenAI client
   - Conditional initialization based on API key

### Modified Files

1. **`internal/service/intent.go`**
   - Removed all regex patterns
   - Simplified to AI-only parsing
   - Fallback behavior if AI is disabled

## Usage Examples

### Example 1: Simple Query

**Input:**
```
3 bedroom condo in Punggol under 1.5M
```

**AI Response:**
```json
{
  "bedrooms": 3,
  "unit_type": "Condo",
  "location": "Punggol",
  "price_max": 1500000,
  "keywords": ["condo", "punggol"]
}
```

### Example 2: Complex Query

**Input:**
```
HDB near MRT with good view and spacious layout
```

**AI Response:**
```json
{
  "unit_type": "HDB",
  "mrt_distance_max": 1000,
  "keywords": ["view", "spacious", "near mrt", "hdb"]
}
```

### Example 3: Multi-criteria

**Input:**
```
Landed property in Bukit Timah, 4 bed 3 bath, modern
```

**AI Response:**
```json
{
  "unit_type": "Landed",
  "location": "Bukit Timah",
  "bedrooms": 4,
  "bathrooms": 3,
  "keywords": ["modern", "landed", "bukit timah"]
}
```

## Error Handling

### AI Unavailable

If `OPENAI_API_KEY` is not set:
```
⚠️ OpenAI is disabled - AI-powered search intent parsing will not work
   Set OPENAI_API_KEY environment variable to enable AI features
```

The system will:
1. Return empty intent slots
2. Include original query as keyword
3. Log warning message
4. Continue with basic search

### Validation Failure

If AI returns invalid data:
```
AI response validation failed: price_min (2000000) cannot be greater than price_max (1000000)
```

The system will:
1. Reject the response
2. Log detailed error
3. Return empty result with query keyword

### API Errors

Network or API errors are caught and logged:
```
AI parsing failed: API request failed with status 429: Rate limit exceeded
```

## Performance Considerations

### Latency
- Typical AI parsing: 200-500ms
- Embedding generation: 100-300ms per batch
- Total query time: <1 second (including DB query)

### Cost Optimization
- Use `gpt-3.5-turbo` for intent parsing (cheap, fast)
- Batch embedding requests (up to 100 items)
- Cache common queries (future enhancement)

### Rate Limits
- Default timeout: 30 seconds
- Batch size: 100 embeddings
- Automatic retry with exponential backoff (future enhancement)

## API Compatibility

The OpenAI client supports:
- **OpenAI Official API**
- **Azure OpenAI**
- **Compatible APIs** (Anthropic, local LLMs with OpenAI format)

Change `OPENAI_API_BASE` to use alternative providers:
```env
# Azure OpenAI
OPENAI_API_BASE=https://your-resource.openai.azure.com/

# Local LLM (e.g., Ollama, LocalAI)
OPENAI_API_BASE=http://localhost:8080/v1
```

## Testing

### Manual Testing

```bash
# Start server with OpenAI enabled
OPENAI_API_KEY=sk-xxx go run cmd/server/main.go

# Test query
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "3 bedroom condo in Punggol under 1.5M",
    "options": {"top_k": 10}
  }'
```

### Check AI Initialization

Look for startup logs:
```
✅ Connected to PostgreSQL database
✅ OpenAI client initialized (model: text-embedding-3-small)
✅ Services initialized
```

## Future Enhancements

1. **Response Caching**: Cache common queries to reduce API calls
2. **Retry Logic**: Exponential backoff for transient failures
3. **Multi-language**: Support Chinese/Malay/Tamil queries
4. **Confidence Scoring**: Adjust based on AI certainty
5. **Semantic Search**: Use embeddings for property description matching
6. **Query Suggestions**: AI-powered autocomplete

## Migration Guide

### For Developers

No breaking changes! The API remains the same:
- Same endpoints
- Same request/response format
- Intent parsing is internal

### For Deployments

1. Add `OPENAI_API_KEY` to environment variables
2. Restart service
3. Verify AI initialization in logs

That's it! No code changes needed.

## Troubleshooting

### Issue: "OpenAI is disabled"
**Solution:** Set `OPENAI_API_KEY` environment variable

### Issue: "AI parsing failed"
**Possible causes:**
- Network connectivity
- Invalid API key
- Rate limit exceeded
- API endpoint unreachable

**Solution:** Check logs for specific error, verify API key and network

### Issue: "AI response validation failed"
**Possible causes:**
- AI returned invalid format
- Values out of range
- Type mismatch

**Solution:** This is expected behavior - the system will use empty result

## Summary

The AI integration provides:
- ✅ **Better UX**: Natural language understanding
- ✅ **Less Code**: Removed ~200 lines of regex code
- ✅ **Flexibility**: Handles variations automatically
- ✅ **Reliability**: Strict validation ensures correct data
- ✅ **Extensibility**: Easy to add new fields or logic

**Key Principle:** Use AI for understanding, validate rigorously for reliability.

