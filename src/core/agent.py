import anthropic
from typing import Optional

SYSTEM_PROMPT = """You are a creative visual prompt expander for an AI art installation called 멀티턴 대화형 에이전트.
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

Visitor says: "장미, 밤에"
Your response:
"밤의 장미, 신비롭네요! 어떤 스타일로 표현할까요? 사실적인 그림, 인상주의, 아니면 특정 화가 스타일이 있나요?

[PROMPT]a red rose blooming at night, moonlight casting soft shadows, detailed petals glistening with dew[/PROMPT]"

Always include [PROMPT]...[/PROMPT] in every single response, no exceptions."""


def extract_prompt(response_text: str) -> str:
    """Extract the prompt from [PROMPT]...[/PROMPT] tags."""
    start = response_text.find("[PROMPT]")
    end = response_text.find("[/PROMPT]")
    if start != -1 and end != -1:
        return response_text[start + 8:end].strip()
    # Fallback: return last line if no tags found
    lines = [l.strip() for l in response_text.strip().split("\n") if l.strip()]
    return lines[-1] if lines else response_text.strip()


def get_display_text(response_text: str) -> str:
    """Remove the [PROMPT] block from display text."""
    start = response_text.find("[PROMPT]")
    if start != -1:
        return response_text[:start].strip()
    return response_text.strip()


class VisuariumAgent:
    def __init__(self, api_key: str, model: str = "claude-opus-4-6"):
        self.api_key = api_key
        self.model = model
        self.messages = []
        self.current_prompt = ""
        self._client = None

    def _get_client(self):
        if self._client is None or self._client.api_key != self.api_key:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def reset(self):
        self.messages = []
        self.current_prompt = ""

    def chat(self, user_text: str) -> tuple[str, str]:
        """
        Send user input, get AI response.
        Returns (display_text, prompt_text)
        """
        self.messages.append({"role": "user", "content": user_text})

        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=self.messages,
        )

        assistant_text = response.content[0].text
        self.messages.append({"role": "assistant", "content": assistant_text})

        prompt = extract_prompt(assistant_text)
        display = get_display_text(assistant_text)

        if prompt:
            self.current_prompt = prompt

        return display, self.current_prompt

    def update_api_key(self, new_key: str):
        self.api_key = new_key
        self._client = None
