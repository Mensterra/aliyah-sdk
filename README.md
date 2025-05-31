# Aliyah SDK

Aaliyah SDK for AI Agent Management and Compliance. Monitor, manage, and ensure compliance for your AI agents.

## Installation

```bash
pip install aliyah-sdk
```

## Quick Start

### Agent Instrumentation and Tracing

```python
import os
from dotenv import load_dotenv
import aliyah_sdk

# Load environment variables
load_dotenv()

# Initialize Aliyah SDK for agent tracing
try:
    aliyah_sdk.init(
        auto_start_session=False,  # Manage sessions manually for better control
        instrument_llm_calls=True,  # Automatically instrument LLM calls
        agent_id=int(os.getenv("AGENT_ID", 1)),  # Set your agent ID
        agent_name=os.getenv("AGENT_NAME", "my_agent")  # Set your agent name
    )
    
    # Enable OpenAI instrumentation
    try:
        from opentelemetry.instrumentation.openai import OpenAIInstrumentor
        openai_instrumentor = OpenAIInstrumentor()
        openai_instrumentor.instrument()
        print("✅ Aliyah SDK initialized with OpenAI instrumentation")
    except Exception as e:
        print(f"Warning: Could not enable OpenAI instrumentation: {e}")
        
except Exception as e:
    print(f"Error initializing Aliyah SDK: {e}")

# Your agent code here - all LLM calls will be automatically traced
```

### Simple Agent Example

```python
import os
from dotenv import load_dotenv
import aliyah_sdk
import time

# Load environment variables
load_dotenv()

# Initialize Aliyah SDK
aliyah_sdk_initialized = False
try:
    aliyah_sdk.init(
        auto_start_session=False,
        instrument_llm_calls=True,
        agent_id=int(os.getenv("AGENT_ID", 1)),
        agent_name=os.getenv("AGENT_NAME", "simple_agent")
    )
    
    # Enable OpenAI instrumentation
    from opentelemetry.instrumentation.openai import OpenAIInstrumentor
    OpenAIInstrumentor().instrument()
    print("✅ Aliyah SDK initialized")
    aliyah_sdk_initialized = True
except Exception as e:
    print(f"Error initializing Aliyah SDK: {e}")
    aliyah_sdk_initialized = False

def run_agent():
    """Simple agent function with Aliyah tracking"""
    
    # Start session manually for better control
    session = None
    if aliyah_sdk_initialized:
        try:
            session = aliyah_sdk.start_session(tags=["simple_agent", "example"])
            if session and hasattr(session, 'span'):
                print(f"🎯 Started Aliyah session: {session.span.context.trace_id:x}")
        except Exception as e:
            print(f"Warning: Could not start session: {e}")
    
    try:
        # Your agent logic here
        # Example: OpenAI call (automatically traced)
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello, how are you?"}]
        )
        
        print(f"Agent response: {response.choices[0].message.content}")
        
        # Force flush traces after LLM call
        if aliyah_sdk_initialized:
            try:
                from aliyah_sdk.sdk.core import TracingCore
                tracing_core = TracingCore.get_instance()
                if tracing_core.initialized:
                    tracing_core._provider._active_span_processor.force_flush(5000)
                    print("✅ Traces flushed")
            except Exception:
                pass
        
        time.sleep(1)  # Brief delay for trace processing
        
    except Exception as e:
        print(f"Error in agent: {e}")
        
        # Record error event
        if aliyah_sdk_initialized:
            try:
                error_event = aliyah_sdk.ErrorEvent(
                    error_type=type(e).__name__,
                    details=str(e),
                    logs=f"Agent error: {e}"
                )
                aliyah_sdk.record(error_event)
            except Exception:
                pass
    
    finally:
        # End session and flush traces
        if session and aliyah_sdk_initialized:
            try:
                aliyah_sdk.end_session(session, end_state="Completed", end_state_reason="Agent finished")
                print("✓ Aliyah session ended")
                
                # Final flush
                from aliyah_sdk.sdk.core import TracingCore
                tracing_core = TracingCore.get_instance()
                if tracing_core.initialized:
                    tracing_core._provider._active_span_processor.force_flush(5000)
                    time.sleep(2)
                    print("✅ Final traces flushed")
            except Exception as e:
                print(f"Warning: Could not properly end session: {e}")

if __name__ == "__main__":
    run_agent()
```

### Environment Variables

Set these in your `.env` file:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key
ALIYAH_API_KEY=your_aliyah_api_key

# Optional - defaults provided
AGENT_ID=1
AGENT_NAME=my_agent
```

## License

Apache 2.0