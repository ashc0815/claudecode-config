"""Agent runner — calls Claude API with tools in a loop until done.

This replaces ALL of CrewAI's Agent/Task/Crew/Flow machinery with ~80 lines.

Usage:
    result = run_agent(
        system_prompt="You are a news scout...",
        user_message="Find today's top AI finance news",
        tools={"brave_search": (schema, handler), ...},
    )
"""

from __future__ import annotations

import json
from datetime import datetime

import anthropic

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 25  # Safety limit — most agents finish in 3-8 turns


def run_agent(
    system_prompt: str,
    user_message: str,
    tools: dict[str, tuple[dict, callable]],
    model: str = MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.3,
    verbose: bool = True,
) -> str:
    """Run a Claude agent with tools until it produces a final text response.

    Args:
        system_prompt: Agent's role/goal/instructions (replaces CrewAI backstory).
        user_message: The task to perform (replaces CrewAI Task description).
        tools: Dict of {name: (schema_dict, handler_fn)}.
        model: Claude model ID.
        max_tokens: Max tokens per response.
        temperature: Sampling temperature.
        verbose: Print tool calls to console.

    Returns:
        The agent's final text output.
    """
    client = anthropic.Anthropic()

    # Inject current date into system prompt
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    system = f"Current date/time: {date_str}\n\n{system_prompt}"

    # Build tool list for Claude API
    tool_schemas = [schema for schema, _handler in tools.values()]

    messages = [{"role": "user", "content": user_message}]

    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tool_schemas,
            messages=messages,
        )

        # Collect text and tool_use blocks
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        # If no tool calls, we're done — return the final text
        if not tool_calls:
            final = "\n".join(text_parts)
            if verbose:
                print(f"  [agent] Done after {turn + 1} turn(s)")
            return final

        # Execute tool calls and build tool_result messages
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            handler_pair = tools.get(tc.name)
            if not handler_pair:
                result_str = f"Error: unknown tool '{tc.name}'"
            else:
                _schema, handler = handler_pair
                try:
                    if verbose:
                        print(f"  [tool] {tc.name}({json.dumps(tc.input, ensure_ascii=False)[:120]})")
                    result_str = handler(**tc.input)
                except Exception as e:
                    result_str = f"Error: {type(e).__name__}: {e}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": str(result_str),
            })

        messages.append({"role": "user", "content": tool_results})

    return "[agent] Hit max turns limit — returning partial result"
