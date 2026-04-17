import re
from typing import Optional

SYSTEM_PROMPT = """You are a creative visual prompt expander for an AI art installation called Agent.
Your role is to guide visitors through a short conversation to build a rich, detailed image generation prompt.

# YOUR GOAL
Transform simple, short inputs (like "flower", "robot", "forest") into vivid, detailed image generation prompts by asking one question at a time about these 4 categories:
1. **Subject** – What exactly appears? Characters, objects, creatures?
2. **Environment** – Space, background, setting, time of day?
3. **Style** – Artistic style, specific artists (Van Gogh, Picasso, Monet), medium (oil painting, sketch, digital art)?
4. **Mood & Color** – Emotion/atmosphere + color palette, lighting?

# CONVERSATION RULES
- Always respond in the SAME LANGUAGE the visitor uses (Korean → Korean, English → English).
- Keep responses SHORT and friendly (1-2 sentences max before the question).
- Ask only ONE question per turn, targeting the most missing category.
- After 3-4 turns, you have enough to build a complete prompt.
- EVERY turn, end your response with a [PROMPT] block.

# [PROMPT] FORMAT
At the end of EVERY response, append a refined prompt enclosed in [PROMPT]...[/PROMPT].
- Write the prompt in English only (for image generation compatibility).
- Start minimal (just the subject), grow richer each turn as you gather more details.
- Target 20-60 words by the final turn.
- Use vivid, painterly descriptive language.

# EXAMPLE
Visitor says: "꽃"
Your response:
"아름다운 꽃이군요! 어떤 꽃인가요? 장미, 벚꽃, 해바라기 같은 특정 꽃이 있나요?

[PROMPT]a beautiful flower, detailed botanical illustration[/PROMPT]"

Always include [PROMPT]...[/PROMPT] in every single response, no exceptions."""


def extract_prompt(response_text: str) -> str:
    start = response_text.find("[PROMPT]")
    end = response_text.find("[/PROMPT]")
    if start != -1 and end != -1:
        return response_text[start + 8:end].strip()
    lines = [l.strip() for l in response_text.strip().split("\n") if l.strip()]
    return lines[-1] if lines else response_text.strip()


def get_display_text(response_text: str) -> str:
    start = response_text.find("[PROMPT]")
    if start != -1:
        return response_text[:start].strip()
    return response_text.strip()


def _has_non_ascii(text: str) -> bool:
    return bool(re.search(r'[^\x00-\x7F]', text))


# ── Provider-specific helpers ───────────────────────────────────────────────

def _chat_claude(client, model: str, messages: list) -> str:
    import anthropic as _anthropic
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


def _translate_claude(client, text: str) -> str:
    import anthropic as _anthropic
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system="You are a translator. Translate the given image generation prompt to English only. Output ONLY the translated prompt, no explanations.",
        messages=[{"role": "user", "content": text}],
    )
    return response.content[0].text.strip()


def _chat_openai(client, model: str, messages: list) -> str:
    response = client.chat.completions.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
    )
    return response.choices[0].message.content


def _translate_openai(client, text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=256,
        messages=[
            {"role": "system", "content": "You are a translator. Translate the given image generation prompt to English only. Output ONLY the translated prompt, no explanations."},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content.strip()


# ── Main agent class ────────────────────────────────────────────────────────

class VisuariumAgent:
    PROVIDERS = ["Claude", "OpenAI"]

    # Default models per provider
    DEFAULT_MODELS = {
        "Claude": "claude-opus-4-6",
        "OpenAI": "gpt-4o",
    }

    def __init__(self, api_key: str, model: str = "claude-opus-4-6",
                 provider: str = "Claude"):
        self.api_key = api_key
        self.model = model
        self.provider = provider  # "Claude" or "OpenAI"
        self.messages = []
        self.current_prompt = ""
        self._client = None

    def _get_client(self):
        if self._client is None or getattr(self._client, '_api_key_ref', None) != self.api_key:
            if self.provider == "Claude":
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            else:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            self._client._api_key_ref = self.api_key
        return self._client

    def reset(self):
        self.messages = []
        self.current_prompt = ""

    def chat(self, user_text: str) -> tuple[str, str]:
        self.messages.append({"role": "user", "content": user_text})

        client = self._get_client()

        if self.provider == "Claude":
            assistant_text = _chat_claude(client, self.model, self.messages)
        else:
            assistant_text = _chat_openai(client, self.model, self.messages)

        self.messages.append({"role": "assistant", "content": assistant_text})

        prompt = extract_prompt(assistant_text)
        display = get_display_text(assistant_text)

        if prompt and _has_non_ascii(prompt):
            if self.provider == "Claude":
                prompt = _translate_claude(client, prompt)
            else:
                prompt = _translate_openai(client, prompt)

        if prompt:
            self.current_prompt = prompt

        return display, self.current_prompt

    def update_api_key(self, new_key: str):
        self.api_key = new_key
        self._client = None

    def update_provider(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self._client = None
