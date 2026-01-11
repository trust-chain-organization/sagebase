# Migration Guide: Using the Shared LLM Service Layer

This guide explains how to migrate existing code to use the new shared LLM service layer.

## Overview

The new service layer provides:
- **LLMService**: Centralized LLM management with retry logic
- **PromptManager**: Centralized prompt management
- **ChainFactory**: Factory for creating different types of chains

## Benefits

1. **Reduced Code Duplication**: Common LLM operations are centralized
2. **Consistent Error Handling**: Built-in retry logic with exponential backoff
3. **Better Configuration Management**: Centralized model selection and parameters
4. **Easier Testing**: Mock services instead of individual LLMs
5. **Performance Optimization**: Reusable chains and connection pooling

## Migration Steps

### 1. Update Imports

**Before:**
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub
from langchain_core.runnables import RunnablePassthrough
```

**After:**
```python
from ..services import LLMService, ChainFactory, PromptManager
```

### 2. Initialize Services

**Before:**
```python
class MinutesDivider:
    def __init__(self, llm: ChatGoogleGenerativeAI, k: int = 5):
        self.section_info_list_formatted_llm = llm.with_structured_output(SectionInfoList)
        self.speaker_and_speech_content_formatted_llm = llm.with_structured_output(SpeakerAndSpeechContentList)
```

**After:**
```python
class MinutesDivider:
    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None, k: int = 5):
        # Initialize services
        if llm:
            # Backward compatibility
            self.llm_service = LLMService(
                model_name=llm.model_name,
                temperature=llm.temperature
            )
        else:
            self.llm_service = LLMService.create_fast_instance()

        self.chain_factory = ChainFactory(self.llm_service)

        # Pre-create chains for performance
        self._section_divide_chain = self.chain_factory.create_minutes_divider_chain(SectionInfoList)
        self._speech_divide_chain = self.chain_factory.create_speech_divider_chain(SpeakerAndSpeechContentList)
```

### 3. Use Chain Factory

**Before:**
```python
def section_divide_run(self, minutes: str) -> SectionInfoList:
    prompt_template = hub.pull("divide_chapter_prompt")
    runnable_prompt = prompt_template | self.section_info_list_formatted_llm
    chain = {"minutes": RunnablePassthrough()} | runnable_prompt
    result = chain.invoke({"minutes": minutes})
    return result
```

**After:**
```python
def section_divide_run(self, minutes: str) -> SectionInfoList:
    try:
        # Use chain factory with retry logic
        result = self.chain_factory.invoke_with_retry(
            self._section_divide_chain,
            {"minutes": minutes}
        )
        return result
    except Exception as e:
        logger.error(f"Error in section_divide_run: {e}")
        raise
```

### 4. Error Handling

The new service layer includes built-in retry logic:

```python
# Automatic retry with exponential backoff
result = self.chain_factory.invoke_with_retry(
    chain,
    input_data,
    max_retries=3  # Optional, defaults to 3
)
```

### 5. Model Selection

Use predefined model configurations:

```python
# Fast model for simple tasks
llm_service = LLMService.create_fast_instance()

# Advanced model for complex tasks
llm_service = LLMService.create_advanced_instance()

# Custom configuration
llm_service = LLMService(
    model_name="gemini-2.0-flash-exp",
    temperature=0.2,
    max_tokens=2000
)
```

## Available Chain Types

The ChainFactory provides pre-configured chains:

1. **Minutes Divider Chain**: `create_minutes_divider_chain(output_schema)`
2. **Speech Divider Chain**: `create_speech_divider_chain(output_schema)`
3. **Politician Extractor Chain**: `create_politician_extractor_chain(output_schema)`
4. **Speaker Matching Chain**: `create_speaker_matching_chain(output_schema)`
5. **Generic Chain**: `create_generic_chain(prompt_template, output_schema)`

## Testing

Update tests to mock the service layer:

```python
# Mock LLM service
mock_llm_service = MagicMock(spec=LLMService)
mock_llm_service.invoke_with_retry.return_value = expected_result

# Inject mock into class
divider = MinutesDivider()
divider.llm_service = mock_llm_service
```

## Backward Compatibility

All refactored classes maintain backward compatibility by accepting an optional `llm` parameter:

```python
# Old way (still works)
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
divider = MinutesDivider(llm)

# New way (recommended)
divider = MinutesDivider()  # Uses default configuration
```

## Best Practices

1. **Use Pre-configured Instances**: Prefer `create_fast_instance()` or `create_advanced_instance()`
2. **Centralize Prompts**: Add new prompts to PromptManager instead of hardcoding
3. **Handle Errors Gracefully**: The service layer logs errors, but still handle them in your code
4. **Reuse Chains**: Create chains once and reuse them for better performance
5. **Monitor Usage**: Use logging to track API calls and costs

## Example: Complete Migration

See the refactored files for complete examples:
- `minutes_divider_refactored.py`
- `politician_extractor_refactored.py`
- `extractor_refactored.py`
- `speaker_matching_service_refactored.py`
- `update_speaker_links_llm_refactored.py`
