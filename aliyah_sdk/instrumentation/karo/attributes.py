"""
Attribute extraction utilities for Karo framework instrumentation.

This module provides functions to extract relevant data from Karo objects
and map them to AgentOps semantic conventions and karo-specific attributes.
"""

from typing import Any, Dict, Optional, Tuple, List, Union
import logging

from aliyah_sdk.logging import logger
from aliyah_sdk.helpers.serialization import safe_serialize, model_to_dict
from aliyah_sdk.instrumentation.common.attributes import AttributeMap, _extract_attributes_from_mapping, get_common_attributes
from aliyah_sdk.instrumentation.karo import LIBRARY_NAME, LIBRARY_VERSION # Use instrumentation's version info
from aliyah_sdk.semconv import (
    InstrumentationAttributes,
    SpanAttributes,
    AaliyahSpanKindValues,
    ToolAttributes,
    WorkflowAttributes,
    MessageAttributes,
    CoreAttributes # For error details
)

# Import Karo specific types for type hinting and isinstance checks
try:
    from karo.core.base_agent import BaseAgent, BaseAgentConfig
    from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
    from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema
    from karo.memory.memory_manager import MemoryManagerConfig, MemoryManager # For MemoryManager config
    from karo.memory.memory_models import MemoryQueryResult, MemoryRecord
    from karo.providers.base_provider import BaseProvider # For provider config/details
    from karo.providers.openai_provider import OpenAIProviderConfig # Example provider config
    from karo.providers.anthropic_provider import AnthropicProviderConfig # Example provider config
    # Import other specific provider configs if needed for detailed config attributes
    # from karo.providers.gemini_provider import GeminiProviderConfig
    # from karo.providers.ollama_provider import OllamaProviderConfig

    # Define Unions for provider configs and tool inputs if needed for extraction helpers
    ProviderConfigUnion = Union[OpenAIProviderConfig, AnthropicProviderConfig] # Add others if needed
    ToolInputUnion = Union[BaseToolInputSchema] # Add other specific ToolInputSchema if needed
    ToolOutputUnion = Union[BaseToolOutputSchema] # Add other specific ToolOutputSchema if needed

    KARO_TYPES_AVAILABLE = True
except ImportError:
    logger.warning("Karo framework types not found. Attribute extraction may be limited.")
    KARO_TYPES_AVAILABLE = False


# --- Common Attributes ---

def get_common_instrumentation_attributes() -> AttributeMap:
    """Get common instrumentation attributes for the Karo instrumentation."""
    attributes = get_common_attributes()
    attributes.update(
        {
            InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
            InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
            SpanAttributes.LLM_SYSTEM: "karo" # Use 'karo' as the system name
        }
    )
    return attributes

# --- Agent Run Attributes (BaseAgent.run) ---

# Mapping for attributes to extract from BaseAgentConfig
AGENT_CONFIG_ATTRIBUTES: AttributeMap = {
    "karo.agent.config.max_history_messages": "max_history_messages", # Removed from config, now external
    "karo.agent.config.memory_query_results": "memory_query_results",
    # Input/Output schemas are types, handle separately
    # Provider/Memory config are objects, handle separately
}

# Mapping for attributes to extract from BaseAgent instance
AGENT_INSTANCE_ATTRIBUTES: AttributeMap = {
    # BaseAgent doesn't have role/name directly, might need custom logic or rely on config
    # "karo.agent.name": "name", # Assuming agent might have a name attribute
    # "karo.agent.role": "role", # Assuming agent might have a role attribute
}


def get_agent_run_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None, instance: Optional[BaseAgent] = None
) -> AttributeMap:
    """Extract attributes for BaseAgent.run method calls."""
    args = args or ()      # Ensure args is not None
    kwargs = kwargs or {}  # Ensure kwargs is not None
    attributes = get_common_instrumentation_attributes()
    attributes[SpanAttributes.AALIYAH_SPAN_KIND] = AaliyahSpanKindValues.AGENT.value # Explicitly mark as agent span
    attributes["karo.operation.type"] = "agent_run" # Specific operation type

    # Agent instance attributes
    if instance:
        attributes.update(_extract_attributes_from_mapping(instance, AGENT_INSTANCE_ATTRIBUTES))
        # Access config attributes from instance.config
        if hasattr(instance, 'config') and isinstance(instance.config, BaseAgentConfig):
            attributes.update(_extract_attributes_from_mapping(instance.config, AGENT_CONFIG_ATTRIBUTES))

            # Handle Provider Config details (example for OpenAI/Anthropic)
            if hasattr(instance.config, 'provider_config') and isinstance(instance.config.provider_config, ProviderConfigUnion): # Check against Union
                provider_cfg = instance.config.provider_config
                attributes["karo.agent.provider.type"] = provider_cfg.type # Discriminator
                attributes["karo.agent.provider.model"] = getattr(provider_cfg, 'model', 'unknown') # Access model safely
                # Add other common provider config attributes if needed
                if hasattr(provider_cfg, 'temperature'):
                     attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = provider_cfg.temperature
                # Add more provider-specific config details (e.g., base_url, organization)

            # Handle Memory Manager Config details
            if hasattr(instance.config, 'memory_manager_config') and isinstance(instance.config.memory_manager_config, MemoryManagerConfig):
                 mem_cfg = instance.config.memory_manager_config
                 attributes["karo.agent.memory_manager.db_type"] = mem_cfg.db_type
                 # Add specific DB config details if needed (e.g., path, collection name)

            # Handle Input/Output Schema names
            if hasattr(instance.config, 'input_schema'):
                 attributes["karo.agent.input_schema"] = getattr(instance.config.input_schema, '__name__', str(instance.config.input_schema))
            if hasattr(instance.config, 'output_schema'):
                 attributes["karo.agent.output_schema"] = getattr(instance.config.output_schema, '__name__', str(instance.config.output_schema))

            # Handle available tools (list of names/descriptions)
            if hasattr(instance, 'tool_map') and isinstance(instance.tool_map, dict):
                 tool_list = []
                 for tool_name, tool_instance in instance.tool_map.items():
                     if isinstance(tool_instance, BaseTool):
                         tool_list.append({"name": tool_instance.get_name(), "description": tool_instance.get_description()})
                     else:
                         tool_list.append({"name": tool_name, "description": "Unknown"})

                 if tool_list:
                      attributes["karo.agent.available_tools"] = safe_serialize(tool_list) # Serialize the list

    # Input arguments (BaseInputSchema, history, state)
    if args and len(args) > 0 and isinstance(args[0], BaseInputSchema):
         input_data = args[0]
         if hasattr(input_data, 'chat_message'):
             attributes[WorkflowAttributes.WORKFLOW_INPUT] = input_data.chat_message # Use chat_message as primary input
         # Add other input schema fields if they exist
         attributes["karo.agent.input"] = safe_serialize(model_to_dict(input_data)) # Serialize full input data

    # History (passed as argument)
    history = kwargs.get('history') or (args[1] if len(args) > 1 else None) # Check kwargs first, then args
    if isinstance(history, list):
         attributes["karo.agent.history_count"] = len(history)
         attributes["karo.agent.history"] = safe_serialize(history) # Serialize full history

    # State (passed as argument)
    state = kwargs.get('state') or (args[2] if len(args) > 2 else None) # Check kwargs first, then args
    if isinstance(state, dict):
         attributes["karo.agent.state"] = safe_serialize(state) # Serialize state

    # Return value (BaseOutputSchema or AgentErrorSchema)
    if return_value is not None:
        if isinstance(return_value, BaseOutputSchema):
            attributes[WorkflowAttributes.FINAL_OUTPUT] = getattr(return_value, 'response_message', safe_serialize(model_to_dict(return_value))) # Prioritize response_message
            attributes["karo.agent.output_success"] = True
            attributes["karo.agent.output"] = safe_serialize(model_to_dict(return_value)) # Serialize full output model
        elif isinstance(return_value, AgentErrorSchema):
            attributes[WorkflowAttributes.FINAL_OUTPUT] = return_value.error_message
            attributes[CoreAttributes.ERROR_TYPE] = return_value.error_type
            attributes[CoreAttributes.ERROR_MESSAGE] = return_value.error_message
            attributes["karo.agent.output_success"] = False
            attributes["karo.agent.output_error_details"] = return_value.details

    return attributes

# --- Tool Run Attributes (BaseTool.run) ---

# Mapping for attributes to extract from BaseTool instance
TOOL_INSTANCE_ATTRIBUTES: AttributeMap = {
    ToolAttributes.TOOL_NAME: "name",
    ToolAttributes.TOOL_DESCRIPTION: "description",
}

def get_tool_run_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None, instance: Optional[BaseTool] = None
) -> AttributeMap:
    """Extract attributes for BaseTool.run method calls."""
    attributes = get_common_instrumentation_attributes()
    attributes[SpanAttributes.AALIYAH_SPAN_KIND] = AaliyahSpanKindValues.TOOL.value # Explicitly mark as tool span
    attributes["karo.operation.type"] = "tool_run" # Specific operation type

    # Tool instance attributes
    if instance:
        attributes.update(_extract_attributes_from_mapping(instance, TOOL_INSTANCE_ATTRIBUTES))
        # Override trace_name if tool name is available
        if instance.name:
             # Access the current span and update its name if possible (requires OTel API usage)
             # Or set an attribute to indicate the specific tool name for filtering
             attributes["karo.tool.specific_name"] = instance.name

    # Input arguments (BaseToolInputSchema)
    if args and len(args) > 0 and isinstance(args[0], BaseToolInputSchema): # Check against base tool input schema
         input_data = args[0]
         attributes[ToolAttributes.TOOL_PARAMETERS] = safe_serialize(model_to_dict(input_data)) # Serialize full input model
         # Add specific common input fields if known, e.g., file_path, query_text

    # Return value (BaseToolOutputSchema)
    if return_value is not None and isinstance(return_value, BaseToolOutputSchema): # Check against base tool output schema
        attributes["karo.tool.success"] = return_value.success
        if return_value.success:
            attributes[ToolAttributes.TOOL_STATUS] = "succeeded"
            # Try to extract a primary result field if available (e.g., 'result', 'row_data', 'content')
            if hasattr(return_value, 'result'):
                 attributes[ToolAttributes.TOOL_RESULT] = safe_serialize(return_value.result)
            elif hasattr(return_value, 'row_data'):
                 attributes[ToolAttributes.TOOL_RESULT] = safe_serialize(return_value.row_data)
            elif hasattr(return_value, 'content'):
                 attributes[ToolAttributes.TOOL_RESULT] = safe_serialize(return_value.content)
            elif hasattr(return_value, 'results'): # For query tools
                 attributes[ToolAttributes.TOOL_RESULT] = safe_serialize(return_value.results)
            else:
                 attributes[ToolAttributes.TOOL_RESULT] = safe_serialize(model_to_dict(return_value)) # Serialize full output model
        else:
            attributes[ToolAttributes.TOOL_STATUS] = "failed"
            attributes[CoreAttributes.ERROR_MESSAGE] = return_value.error_message
            # Add other error fields if they exist in BaseToolOutputSchema
            attributes["karo.tool.error_message"] = return_value.error_message


    return attributes

# --- Memory Manager Attributes ---

# Mapping for attributes to extract from MemoryManagerConfig
MEMORY_MANAGER_CONFIG_ATTRIBUTES: AttributeMap = {
    "karo.memory.manager.db_type": "db_type",
    # Add specific DB config details if needed (e.g., path, collection name)
}

def get_memory_manager_attributes(instance: Optional[MemoryManager] = None) -> AttributeMap:
    """Extract common attributes from MemoryManager instance."""
    attributes = {}
    if instance and hasattr(instance, 'config') and isinstance(instance.config, MemoryManagerConfig):
        attributes.update(_extract_attributes_from_mapping(instance.config, MEMORY_MANAGER_CONFIG_ATTRIBUTES))
        # Add specific DB config details if needed
        if hasattr(instance.config, 'chromadb_config'):
            attributes["karo.memory.manager.chromadb.path"] = getattr(instance.config.chromadb_config, 'path', 'unknown')
            attributes["karo.memory.manager.chromadb.collection"] = getattr(instance.config.chromadb_config, 'collection_name', 'unknown')
            attributes["karo.memory.manager.chromadb.embedding_model"] = getattr(instance.config.chromadb_config, 'embedding_model_name', 'unknown')

    return attributes


def get_memory_add_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None, instance: Optional[MemoryManager] = None
) -> AttributeMap:
    """Extract attributes for MemoryManager.add_memory method calls."""
    attributes = get_common_instrumentation_attributes()
    attributes.update(get_memory_manager_attributes(instance))
    attributes[SpanAttributes.AALIYAH_SPAN_KIND] = "memory" # Custom kind or map to CLIENT
    attributes["karo.operation.type"] = "memory_add"

    # Input arguments (text, metadata, memory_id, importance_score)
    # Check kwargs first as they are often used
    text = kwargs.get('text') or (args[0] if args and len(args) > 0 else None)
    memory_id = kwargs.get('memory_id') or (args[2] if args and len(args) > 2 else None) # memory_id is 3rd positional arg
    metadata = kwargs.get('metadata') or (args[1] if args and len(args) > 1 else None) # metadata is 2nd positional arg
    importance_score = kwargs.get('importance_score') or (args[3] if args and len(args) > 3 else None) # importance_score is 4th positional arg

    if text is not None:
        attributes["karo.memory.add.text"] = str(text)[:1000] # Truncate long text
    if memory_id is not None:
        attributes["karo.memory.add.id"] = str(memory_id)
    if metadata is not None:
        attributes["karo.memory.add.metadata"] = safe_serialize(metadata)
    if importance_score is not None:
        attributes["karo.memory.add.importance_score"] = importance_score

    # Return value (ID of the stored memory or None)
    if return_value is not None:
         attributes["karo.memory.add.result_id"] = str(return_value)
         attributes["karo.memory.add.success"] = True
         attributes[ToolAttributes.TOOL_STATUS] = "succeeded" # Map to tool status for simplicity
    elif return_value is None and args and len(args) > 0: # Assume failure if None is returned but args exist
         attributes["karo.memory.add.success"] = False
         attributes[ToolAttributes.TOOL_STATUS] = "failed"

    return attributes

def get_memory_query_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None, instance: Optional[MemoryManager] = None
) -> AttributeMap:
    """Extract attributes for MemoryManager.retrieve_relevant_memories method calls."""
    attributes = get_common_instrumentation_attributes()
    attributes.update(get_memory_manager_attributes(instance))
    attributes[SpanAttributes.AALIYAH_SPAN_KIND] = "memory" # Custom kind or map to CLIENT
    attributes["karo.operation.type"] = "memory_query"

    # Input arguments (query_text, n_results, where_filter)
    # Check kwargs first
    query_text = kwargs.get('query_text') or (args[0] if args and len(args) > 0 else None)
    n_results = kwargs.get('n_results') or (args[1] if args and len(args) > 1 else None)
    where_filter = kwargs.get('where_filter') or (args[2] if args and len(args) > 2 else None)

    if query_text is not None:
        attributes["karo.memory.query.text"] = str(query_text)
    if n_results is not None:
        attributes["karo.memory.query.n_results_requested"] = n_results
    if where_filter is not None:
         attributes["karo.memory.query.where_filter"] = safe_serialize(where_filter)

    # Return value (List[MemoryQueryResult])
    if return_value is not None and isinstance(return_value, list): # Expect a list of results
         attributes["karo.memory.query.success"] = True
         attributes[ToolAttributes.TOOL_STATUS] = "succeeded" # Map to tool status for simplicity
         attributes["karo.memory.query.n_results_returned"] = len(return_value)
         # Include details of the top N results?
         if return_value:
              top_n_details = []
              for i, res in enumerate(return_value[:min(len(return_value), 5)]): # Limit details to top 5
                  if isinstance(res, MemoryQueryResult):
                       top_n_details.append({
                            "id": res.record.id,
                            "text": res.record.text[:100] + "..." if len(res.record.text) > 100 else res.record.text, # Truncate text
                            "distance": res.distance,
                            # Add other relevant record/result fields
                       })
              attributes["karo.memory.query.top_results_preview"] = safe_serialize(top_n_details)
    elif return_value is not None and not isinstance(return_value, list):
         # Unexpected return type
         attributes["karo.memory.query.success"] = False
         attributes[ToolAttributes.TOOL_STATUS] = "failed"
         attributes[CoreAttributes.ERROR_MESSAGE] = f"Memory query returned unexpected type: {type(return_value).__name__}"
    elif return_value is None and query_text is not None: # Assume failure if None is returned but query text was provided
         attributes["karo.memory.query.success"] = False
         attributes[ToolAttributes.TOOL_STATUS] = "failed"
         # No specific error message available from method signature, might need try/except in wrapper


    return attributes

# --- Provider Generate Response Attributes (BaseProvider.generate_response) ---

def get_provider_generate_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None, instance: Optional[BaseProvider] = None
) -> AttributeMap:
    """Extract attributes for BaseProvider.generate_response method calls."""
    attributes = get_common_instrumentation_attributes()
    attributes[SpanAttributes.AALIYAH_SPAN_KIND] = "llm" # Map to LLM span
    attributes["karo.operation.type"] = "provider_generate_response"

    # Provider instance details
    if instance:
        attributes["karo.provider.type"] = instance.__class__.__name__
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = instance.get_model_name() # Use get_model_name()
        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = instance.get_model_name() # Assume response model is the same

    # Input arguments (prompt, output_schema, tools, tool_choice, kwargs for provider)
    prompt = kwargs.get('prompt') or (args[0] if args and len(args) > 0 else None)
    output_schema_type = kwargs.get('output_schema') or (args[1] if args and len(args) > 1 else None)
    tools = kwargs.get('tools') or (args[2] if args and len(args) > 2 else None) # tools is 3rd positional
    tool_choice = kwargs.get('tool_choice') or (args[3] if args and len(args) > 3 else None) # tool_choice is 4th positional

    if isinstance(prompt, list):
         attributes[SpanAttributes.LLM_PROMPTS] = safe_serialize(prompt) # Serialize full prompt list
         attributes["karo.provider.prompt_count"] = len(prompt)
    elif prompt is not None:
         attributes[SpanAttributes.LLM_PROMPTS] = str(prompt) # Fallback for non-list prompts

    if output_schema_type is not None:
         attributes["karo.provider.output_schema_name"] = getattr(output_schema_type, '__name__', str(output_schema_type))

    if isinstance(tools, list):
         attributes["karo.provider.tools_passed_count"] = len(tools)
         # Include list of tool names passed
         tool_names = [t.get('function', {}).get('name', 'unknown') for t in tools if isinstance(t, dict) and 'function' in t]
         attributes["karo.provider.tools_passed_names"] = safe_serialize(tool_names)
    elif tools is not None:
         attributes["karo.provider.tools_passed_count"] = 1 # Assume single tool/definition
         attributes["karo.provider.tools_passed_details"] = safe_serialize(tools)

    if tool_choice is not None:
         attributes["karo.provider.tool_choice"] = str(tool_choice)

    # Extract other provider-specific kwargs if they exist in the input dict
    # This is tricky as kwargs can contain anything. Might need specific handling per provider or rely on LLM library instrumentors.
    # Example: temperature, max_tokens are often in kwargs.
    temperature = kwargs.get('temperature')
    max_tokens = kwargs.get('max_tokens')
    if temperature is not None:
         attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = temperature
    if max_tokens is not None:
         attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = max_tokens


    # Return value (BaseOutputSchema or raw response with tool calls)
    if return_value is not None:
        if isinstance(return_value, BaseOutputSchema):
             attributes["karo.provider.response_success"] = True
             attributes["karo.provider.response_type"] = "validated_schema"
             attributes[SpanAttributes.LLM_COMPLETIONS] = getattr(return_value, 'response_message', safe_serialize(model_to_dict(return_value))) # Prioritize response_message
        # Check for common raw response structures indicating tool calls (OpenAI, Anthropic)
        # This requires checking specific provider return types or common patterns
        # Example: Check if it has 'choices' and 'tool_calls' (OpenAI) or 'content' with tool_use (Anthropic)
        elif hasattr(return_value, 'choices') and isinstance(return_value.choices, list) and len(return_value.choices) > 0:
            choice = return_value.choices[0]
            if hasattr(choice, 'message') and (hasattr(choice.message, 'tool_calls') or hasattr(choice.message, 'function_call')):
                 attributes["karo.provider.response_success"] = True
                 attributes["karo.provider.response_type"] = "raw_tool_call"
                 # Add attributes for tool calls if needed, but LLM library instrumentors should handle this detail
            else:
                 attributes["karo.provider.response_success"] = True # Response received
                 attributes["karo.provider.response_type"] = "raw_other"
                 attributes[SpanAttributes.LLM_COMPLETIONS] = safe_serialize(model_to_dict(return_value)) # Serialize raw response
        elif hasattr(return_value, 'content') and isinstance(return_value.content, list) and len(return_value.content) > 0:
             # Check for Anthropic content block structure indicating tool_use
             if any(hasattr(block, 'type') and block.type == 'tool_use' for block in return_value.content):
                  attributes["karo.provider.response_success"] = True
                  attributes["karo.provider.response_type"] = "raw_tool_use"
                  # Add attributes for tool use blocks if needed
             else:
                  attributes["karo.provider.response_success"] = True # Response received
                  attributes["karo.provider.response_type"] = "raw_content_block"
                  attributes[SpanAttributes.LLM_COMPLETIONS] = safe_serialize(model_to_dict(return_value)) # Serialize raw response
        else:
             attributes["karo.provider.response_success"] = True # Response received, but type unknown
             attributes["karo.provider.response_type"] = "unknown"
             attributes[SpanAttributes.LLM_COMPLETIONS] = safe_serialize(model_to_dict(return_value)) # Serialize raw response

    return attributes