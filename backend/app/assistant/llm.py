"""LLM integration with OpenAI-compatible API endpoints."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Default values from settings (for backward-compatible global singleton)
_DEFAULT_API_URL = settings.poolside_api_url
_DEFAULT_API_KEY = settings.get_poolside_key()
_DEFAULT_MODEL = settings.assistant_model


def get_llm_client(model: str | None = None) -> "LLMClient":
    """Factory that constructs an LLMClient with resolved settings.

    Precedence rules:
    1. llm_base_url if non-empty, else poolside_api_url.
    2. API key: llm_api_key if set, else poolside_api_key.
    3. Model: the passed `model` arg if provided; otherwise llm_model if non-empty, else assistant_model.
    """
    base_url = settings.llm_base_url or settings.poolside_api_url
    api_key = settings.get_llm_key()
    resolved_model = model or settings.llm_model or settings.assistant_model
    return LLMClient(base_url=base_url, api_key=api_key, model=resolved_model)


class LLMClient:
    """Client for OpenAI-compatible LLM chat completions and agentic tool-calling loops.

    Provides non-streaming and streaming chat completion methods, plus an
    iterative tool-calling loop that lets the model invoke registered
    tools until no more tool calls are requested.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
        """Initialize the LLM client with API endpoint, key, and default model.

        Behavior:
        1. Read the API URL, API key, and default model from parameters or application settings.
        2. Store them as instance attributes for subsequent requests.

        Raises: None
        Side Effects: None (read-only, no state mutation beyond self).
        Dependencies: app.config.settings.
        Consumers: LLMClient singleton instantiation.
        """
        self.api_url = base_url or _DEFAULT_API_URL
        self.api_key = api_key or _DEFAULT_API_KEY
        self.model = model or _DEFAULT_MODEL

    def _get_headers(self) -> dict[str, str]:
        """Build the HTTP authorization headers for Poolside API requests.

        Behavior:
        1. Build a dict with Bearer token Authorization and Content-Type headers.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None
        Consumers: LLMClient.chat_completion, LLMClient.chat_completion_stream.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send a non-streaming chat completion request to the Poolside LLM.

        Behavior:
        1. Build the request payload with model, messages, temperature, max_tokens, and stream flag.
        2. If tools are provided, add them and set tool_choice to auto.
        3. POST to the Poolside chat completions endpoint.
        4. Raise for non-2xx status codes.
        5. Return the parsed JSON response.

        Raises: httpx.HTTPStatusError if the API returns a non-2xx status.
        Side Effects: Makes an outbound HTTP POST.
        Dependencies: httpx.AsyncClient.
        Consumers: LLMClient.execute_tool_loop.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.api_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 800,
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion response from the Poolside LLM in SSE format.

        Behavior:
        1. Build the streaming request payload.
        2. Open an async stream to the chat completions endpoint.
        3. If the status is >=400, yield a JSON error and return.
        4. Otherwise parse SSE lines, extract content deltas, and yield them.
        5. On exception, yield a JSON error with the traceback.

        Raises: None (errors are yielded as JSON strings).
        Side Effects: Makes an outbound HTTP streaming POST; prints debug logs.
        Dependencies: httpx.AsyncClient.
        Consumers: LLMClient.execute_tool_loop, assistant streaming endpoints.
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        # Debug logging
        print(f"[DEBUG LLM] API URL: {self.api_url}")
        print(f"[DEBUG LLM] Model: {self.model}")
        print(f"[DEBUG LLM] Messages count: {len(messages)}")
        print(f"[DEBUG LLM] Tools count: {len(tools) if tools else 0}")
        print(f"[DEBUG LLM] Payload preview: {json.dumps(payload, indent=2)[:500]}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.api_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        error_body = await response.aread()
                        error_text = error_body.decode()
                        print(f"[ERROR] Poolside API {response.status_code}: {error_text[:1000]}")
                        yield json.dumps({"error": f"LLM API error {response.status_code}: {error_text[:200]}"})
                        return
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                import traceback

                error_detail = f"{type(e).__name__}: {str(e)}"
                print(f"[ERROR] chat_completion_stream: {error_detail}")
                print(f"[ERROR] Traceback: {traceback.format_exc()[:500]}")
                yield json.dumps({"error": error_detail})

    async def execute_tool_loop(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        user_message: str,
        tools: list[dict],
        tool_executor: callable,
        max_iterations: int = 5,
    ) -> AsyncGenerator[str, None]:
        """Execute an agentic LLM conversation with an iterative tool-calling loop.

        Behavior:
        1. Assemble the message list from system prompt, history, and user message.
        2. Stream the assistant's reply via chat_completion_stream.
        3. Detect JSON tool-call payloads in the stream.
        4. If tool calls are found, execute them via tool_executor.
        5. Append tool results to the conversation and loop up to max_iterations.

        Raises: None
        Side Effects: Invokes tool_executor; mutates local messages list.
        Dependencies: LLMClient.chat_completion_stream.
        Consumers: Assistant chat endpoint.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            # Stream the response
            full_content = ""
            tool_calls = []

            async for chunk in self.chat_completion_stream(
                messages=messages,
                tools=tools,
            ):
                # Check if chunk is a tool call
                if chunk.startswith('{"tool":'):
                    try:
                        tool_data = json.loads(chunk)
                        tool_calls.append(tool_data)
                    except json.JSONDecodeError:
                        full_content += chunk
                        yield chunk
                else:
                    full_content += chunk
                    yield chunk

            # If no tool calls, we're done
            if not tool_calls:
                break

            # Execute tool calls and add results
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                parameters = tool_call.get("parameters", {})

                # Execute the tool
                try:
                    result = await tool_executor(tool_name, parameters)
                    tool_result = json.dumps({"success": True, "result": result})
                except Exception as e:
                    tool_result = json.dumps({"success": False, "error": str(e)})

                # Add assistant message with tool call
                messages.append(
                    {
                        "role": "assistant",
                        "content": full_content or None,
                        "tool_calls": [
                            {
                                "id": f"call_{iteration}",
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(parameters),
                                },
                            }
                        ],
                    }
                )

                # Add tool result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": f"call_{iteration}",
                        "content": tool_result,
                    }
                )

            # Continue loop with updated messages


# Global instance
llm_client = LLMClient()
