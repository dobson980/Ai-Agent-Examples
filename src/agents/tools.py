#!/usr/bin/env python3
# ======================================================================================
# Agent: Weather (Function Calling Conversation)
# ======================================================================================
"""Interactive multi-turn weather agent.

What it does:
    * Lets the model call a single function (get_weather_by_city) to resolve city -> temp.
    * Executes the tool, then provides the tool result back for a natural-language summary.
    * Allows repeated city queries in one session with cumulative token accounting.

User Inputs:
    City names like 'San Diego', 'Paris, France', 'Tokyo'.
    Commands: /exit | exit | quit | :q  (leave)  •  /help (help menu)

Environment:
    OPENAI_API_KEY must be set.

Outputs:
    Per-turn usage lines + final aggregate token usage.
"""

import os
import logging
import json
from typing import Any, Dict, List
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

# --------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Quiet noisy underlying client loggers (those HTTP Request: POST ... lines)
for noisy in ("openai", "httpx"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-5-nano"

# Single tool: resolve city name -> fetch current temperature (returns F)
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather_by_city",
            "description": "Get the current temperature (F) for a given city name. Provide city, optionally with state/country for disambiguation (e.g. 'Paris, France').",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, optionally with region/country."}
                },
                "required": ["city"],
                "additionalProperties": False
            }
        }
    }
]

# --------------------------------------------------------------------------------------
# Tool Implementation (returns only what we need)
# --------------------------------------------------------------------------------------
def c_to_f(c: float) -> float:
    return round((c * 9 / 5) + 32, 1)

def geocode_city(city: str) -> Dict[str, Any]:
    """Resolve a city name to coordinates using Open-Meteo geocoding."""
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        first = (data.get("results") or [{}])[0]
        if not first:
            return {"error": "city_not_found", "city": city}
        return {
            "city": city,
            "resolved_name": first.get("name"),
            "country": first.get("country"),
            "latitude": first.get("latitude"),
            "longitude": first.get("longitude")
        }
    except Exception as e:
        return {"error": str(e), "city": city}

def fetch_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": latitude, "longitude": longitude, "current": "temperature_2m"},
            timeout=8,
        )
        resp.raise_for_status()
        payload = resp.json()
        current = payload.get("current", {})
        temp_c = current.get("temperature_2m")
        if temp_c is None:
            return {"error": "temperature_unavailable", "latitude": latitude, "longitude": longitude}
        return {
            "latitude": latitude,
            "longitude": longitude,
            "temperature_c": temp_c,
            "temperature_f": c_to_f(temp_c),
            "timestamp": current.get("time")
        }
    except Exception as e:
        return {"error": str(e), "latitude": latitude, "longitude": longitude}

def get_weather_by_city(city: str) -> Dict[str, Any]:
    geo = geocode_city(city)
    if geo.get("error"):
        return {"city": city, **geo}
    lat = geo.get("latitude")
    lon = geo.get("longitude")
    if lat is None or lon is None:
        return {"city": city, "error": "coordinates_missing", **geo}
    weather = fetch_weather(lat, lon)
    return {"city": city, **geo, **weather}

def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "get_weather_by_city":
        return get_weather_by_city(**args)
    return {"error": f"unknown_tool", "name": name}

# --------------------------------------------------------------------------------------
# OpenAI Helpers
# --------------------------------------------------------------------------------------
def first_call(system_prompt: str, user_prompt: str):
    client = OpenAI(api_key=OPENAI_API_KEY)
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        tools=tools,
        reasoning_effort="minimal"
    )

def second_call(messages: List[Dict[str, Any]]):
    client = OpenAI(api_key=OPENAI_API_KEY)
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        reasoning_effort="minimal"
    )

def extract_usage(completion) -> Dict[str, Any]:
    u = completion.usage
    details = getattr(u, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", 0) if details else 0
    return {
        "prompt": getattr(u, "prompt_tokens", 0),
        "completion": getattr(u, "completion_tokens", 0),
        "reasoning": reasoning,
        "total": getattr(u, "total_tokens", 0)
    }

# --------------------------------------------------------------------------------------
# Conversation Runner
# --------------------------------------------------------------------------------------
def conversation_loop():
    system_prompt = (
        "You are a concise weather assistant. To answer weather questions, call the function "
        "get_weather_by_city with a city name (optionally with region/country). After tool results are provided, "
        "summarize ONLY the current temperature in °F and location name in one short sentence."
    )
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt}
    ]
    client = OpenAI(api_key=OPENAI_API_KEY)

    total_tokens = 0
    total_prompt = 0
    total_completion = 0
    total_reasoning = 0

    print("Enter a city name to get the current temperature. Type '/exit' (or 'exit', 'quit', ':q') or press ENTER on a blank line to quit. Type '/help' for commands.")
    while True:
        try:
            city_query = input("City> ").strip()
        except EOFError:
            break
        if not city_query:
            break
        # Command handling
        lower = city_query.lower()
        if lower in {"/exit", "exit", "quit", ":q"}:
            break
        if lower in {"/help", "help", "?"}:
            print("Commands: /exit | exit | quit | :q to leave, /help for this message. Enter a city like 'Paris, France' or 'San Diego'.")
            continue
        messages.append({"role": "user", "content": city_query})

        # First model call (may produce tool calls)
        first = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            reasoning_effort="minimal"
        )
        u1 = extract_usage(first)
        total_tokens += u1["total"]; total_prompt += u1["prompt"]; total_completion += u1["completion"]; total_reasoning += u1["reasoning"]
        print(f"[usage:first] prompt={u1['prompt']} completion={u1['completion']} total={u1['total']}")
        msg = first.choices[0].message

        if msg.tool_calls:
            # Append assistant tool call shell
            assistant_call_msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": []
            }
            tool_output_messages = []
            for tc in msg.tool_calls:
                fn = tc.function
                args = json.loads(fn.arguments) if fn.arguments else {}
                # If model forgot city argument, try using last user content
                args.setdefault("city", city_query)
                result = execute_tool(fn.name, args)
                assistant_call_msg["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": fn.name, "arguments": json.dumps(args)}
                })
                tool_output_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)
                })

            messages.append(assistant_call_msg)
            messages.extend(tool_output_messages)

            second = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                reasoning_effort="minimal"
            )
            u2 = extract_usage(second)
            total_tokens += u2["total"]; total_prompt += u2["prompt"]; total_completion += u2["completion"]; total_reasoning += u2["reasoning"]
            final_msg = second.choices[0].message
            messages.append({"role": "assistant", "content": final_msg.content})
            print(final_msg.content)
            print(f"[usage:second] prompt={u2['prompt']} completion={u2['completion']} total={u2['total']} (cumulative_total={total_tokens})")
        else:
            # Direct answer (no tool call)
            messages.append({"role": "assistant", "content": msg.content})
            print(msg.content)
            print(f"[usage:single] cumulative_total={total_tokens}")

    logger.info("\n=== Total Token Usage (All Turns) ===")
    logger.info({
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "reasoning_tokens": total_reasoning,
        "total_tokens": total_tokens
    })
    print("\nSession token totals:")
    print(f"prompt={total_prompt} completion={total_completion} reasoning={total_reasoning} total={total_tokens}")

# --------------------------------------------------------------------------------------
# Main Entry
# --------------------------------------------------------------------------------------
def main():
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set")
        return
    conversation_loop()

if __name__ == "__main__":
    main()