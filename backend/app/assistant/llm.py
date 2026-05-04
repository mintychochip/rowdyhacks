"""LLM integration with Poolside AI (m.1 model)."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Poolside API configuration
POOLSIDE_API_URL = settings.poolside_api_url
POOLSIDE_API_KEY = settings.get_poolside_key()
DEFAULT_MODEL = settings.assistant_model


class LLMClient:
    """Client for Poolside AI LLM."""

    def __init__(self):
        self.api_url = POOLSIDE_API_URL
        self.api_key = POOLSIDE_API_KEY
        self.model = DEFAULT_MODEL

    def _get_headers(self) -> dict[str, str]:
        """Get authorization headers."""
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
        """Send a chat completion request."""
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
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion response (SSE format)."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        # Debug logging
        print(f"[DEBUG LLM] Poolside API URL: {self.api_url}")
        print(f"[DEBUG LLM] Poolside model: {self.model}")
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
                        yield f'{{"error": "Poolside API error {response.status_code}: {error_text[:200]}"}}'
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
        """
        Execute LLM with tool calling loop.
        Yields content chunks. Tool calls are executed and results added.
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
