# Aliyah SDK

Aaliyah SDK provides comprehensive AI agent management, compliance monitoring, and observability. Track LLM calls, manage agent sessions, and ensure compliance with automatic instrumentation and manual event tracking.

## Installation

```bash
pip install aliyah-sdk
```

## Quick Start

### 1. Environment Configuration

Create a `.env` file in your project root:

```bash
# Required - Get from Mensterra dashboard
ALIYAH_API_KEY=your_aliyah_api_key

# Agent Configuration
AGENT_ID=1                    # Your agent's unique ID from app.mensterra.com
AGENT_NAME=my_support_agent   # Descriptive name for your agent
```

### 1. Basic Setup

```python
import aliyah_sdk


# Initialize the SDK
aliyah_sdk.init(
    auto_start_session=False,
    instrument_llm_calls=True,  # Enable automatic LLM instrumentation
    agent_id=12345,  # Your agent ID from the Aliyah dashboard
    agent_name="my_ai_agent"
)
```

### 3. Basic Agent with Automatic LLM Tracking

```python
import os
from dotenv import load_dotenv
import aliyah_sdk
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize Aaliyah SDK - this enables automatic LLM call tracking
aliyah_sdk.init(
    auto_start_session=True,     # Automatically manage sessions
    instrument_llm_calls=True,   # Track all OpenAI/LLM calls automatically
    agent_id=int(os.getenv("AGENT_ID", 1)),
    agent_name=os.getenv("AGENT_NAME", "my_agent")
)

def simple_agent():
    """Basic agent with automatic tracking"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # This LLM call is automatically tracked by Aaliyah
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "What's the weather like?"}]
    )
    
    return response.choices[0].message.content

if __name__ == "__main__":
    result = simple_agent()
    print(f"Agent response: {result}")
```

### 4. Manual Session Management

Sessions help you group related AI interactions and trace them as a single workflow:

```python
# Start a session
session = aliyah_sdk.start_session(
    tags=["chatbot", "customer_support", "production"]
)

# Your AI application logic here...

# End the session
aliyah_sdk.end_session(
    session, 
    end_state="Completed", 
    end_state_reason="User query resolved successfully"
)
```

## Advanced Usage

### Manual Session Management

For production agents that need precise control over session lifecycle:

```python
import os
from dotenv import load_dotenv
import aliyah_sdk
from openai import OpenAI
import time

load_dotenv()

# Initialize without auto-session for manual control
aaliyah_sdk.init(
    auto_start_session=False,    # We'll manage sessions manually
    instrument_llm_calls=True,   # Still auto-track LLM calls
    agent_id=int(os.getenv("AGENT_ID", 1)),
    agent_name=os.getenv("AGENT_NAME", "advanced_agent")
)

def advanced_agent_with_session():
    """Agent with manual session management and custom events"""
    
    # Start a session with custom tags and metadata
    session = aaliyah_sdk.start_session(
        tags=["customer_support", "production"],
        metadata={
            "customer_id": "12345",
            "priority": "high",
            "channel": "chat"
        }
    )
    
    try:
        client = OpenAI()
        
        # Record custom business event
        aaliyah_sdk.record(aaliyah_sdk.BusinessEvent(
            event_type="customer_inquiry_started",
            details="Customer asking about order status",
            metadata={"order_id": "ORD-789"}
        ))
        
        # LLM call - automatically tracked
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful customer support agent."},
                {"role": "user", "content": "Where is my order #ORD-789?"}
            ]
        )
        
        answer = response.choices[0].message.content
        
        # Record successful resolution
        aaliyah_sdk.record(aaliyah_sdk.BusinessEvent(
            event_type="inquiry_resolved",
            details="Successfully provided order status",
            metadata={"resolution_time_ms": 1500}
        ))
        
        return answer
        
    except Exception as e:
        # Record error for debugging and compliance
        aaliyah_sdk.record(aaliyah_sdk.ErrorEvent(
            error_type=type(e).__name__,
            details=str(e),
            logs="Failed to process customer inquiry"
        ))
        raise
        
    finally:
        # Always end the session with proper state
        aaliyah_sdk.end_session(
            session, 
            end_state="completed",
            end_state_reason="Customer inquiry processed successfully"
        )

if __name__ == "__main__":
    result = advanced_agent_with_session()
    print(f"Agent response: {result}")
```



## Integration Examples

### With OpenAI

```python
import aliyah_sdk
import openai

# Initialize Aliyah
aliyah_sdk.init(
    instrument_llm_calls=True,
    agent_id=12345,
    agent_name="openai_chatbot"
)

# Start session
session = aliyah_sdk.start_session(tags=["chatbot"])

try:
    # This call is automatically traced
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)
    
finally:
    aliyah_sdk.end_session(session, end_state="Completed")
```

### With Custom AI Frameworks

The SDK automatically instruments most popular LLM providers. For custom frameworks, manual instrumentation may be needed.

## Event Types Reference

### Automatic Events
- **LLM Calls**: Automatically tracked when `instrument_llm_calls=True`
- **Session Start/End**: Automatically managed when `auto_start_session=True`

### Manual Events


#### Tool Events
```python
aaliyah_sdk.record(aaliyah_sdk.ToolEvent(
    tool_name="database",
    action="query",
    input_data={"table": "customers", "filter": "active=true"},
    output_data={"row_count": 150}
))
```

#### Error Events
```python
aaliyah_sdk.record(aaliyah_sdk.ErrorEvent(
    error_type="ValidationError",
    details="Invalid customer email format",
    severity="medium",
    logs="Email validation failed: invalid@domain"
))
```

## Best Practices

### 1. Session Management
- Use `auto_start_session=True` for simple agents
- Use manual sessions for complex workflows that need precise control
- Always include relevant tags and metadata in sessions

### 2. Error Handling
- Wrap agent logic in try/catch blocks
- Record errors with appropriate severity levels
- Include debugging information in error metadata

### 3. Performance
- Sessions automatically batch and send events efficiently
- Use `end_session()` to ensure all data is flushed
- Consider using manual sessions for long-running agents

## Troubleshooting

### Common Issues

**SDK Not Initializing**
```python
# Check if client is properly initialized
client = aliyah_sdk.get_client()
if client and client.initialized:
    print("✓ SDK initialized successfully")
else:
    print("✗ SDK initialization failed")
```

**Traces Not Appearing**
- Verify your agent ID exists in the dashboard
- Check network connectivity
- Ensure API key is set correctly
- Try force flushing traces

**Session Management Issues**
- Always call `end_session()` in a finally block
- Check session object is valid before ending
- Use appropriate end states and reasons

### Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your Aliyah SDK code here
```

## Configuration Options

### SDK Initialization
```python
aliyah_sdk.init(
    auto_start_session=True,      # Auto-manage sessions (default: True)
    instrument_llm_calls=True,    # Auto-track LLM calls (default: True)
    agent_id=1,                   # Your agent's unique ID
    agent_name="my_agent",        # Descriptive agent name
    api_key="your_key",          # Aliyah API key (or use env var)
)
```

## Monitoring and Dashboards

After instrumenting your agent:

1. **View in Mensterra Dashboard**: Monitor agent performance, compliance, and errors
2. **Session Traces**: See detailed traces of each agent session
3. **Compliance Reports**: Generate compliance reports for audits
4. **Performance Metrics**: Track LLM usage, response times, and error rates
5. **Alerts**: Set up alerts for compliance violations or errors

## Need Help?

- 📖 **Documentation**: [Full API docs](https://docs.mensterra.com)
- 💬 **Support**: [Contact support](mailto:support@mensterra.com)


## License

Apache 2.0

Happy tracing! 🚀