---
title: "Nano-Banana Pro Prompting Guide: Strategies"
research_date: "2026-02-23"
source_url: "https://dev.to/googleai/nano-banana-pro-prompting-guide-strategies-1h9n"
version_at_research: "Nano-Banana Pro (`gemini-3-pro-image-preview` preview)"
license: "Google API Terms of Service (output owned by user; usage billed via Gemini API quota)"
last_verified: "2026-02-23"
version_at_verification: "`gemini-3-pro-image-preview` (preview)"
next_review: "2026-05-23"
---

## Overview

Nano-Banana Pro (model ID `gemini-3-pro-image-preview`) is Google's latest image generation model, a significant upgrade from previous generations. Published by the Google AI Developer Relations team on dev.to, this prompting guide documents the model's core capabilities and the most effective strategies for eliciting professional-grade output across ten categories: text rendering, character consistency, real-time data grounding, image editing, dimensional translation (2D↔3D), high-resolution output, visual reasoning, storyboarding, and structural layout control. Unlike earlier image models, Nano-Banana Pro is a "Thinking" model — it reasons about intent, physics, and composition before generating output, enabling conversational editing workflows rather than prompt-from-scratch iteration.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Image models treat prompts as keyword bags, producing generic results | Nano-Banana Pro understands full natural-language sentences and intent, enabling Creative Director-style prompting |
| Re-rolling entire images when only one element needs fixing wastes time and credits | Conversational edits let users say "change the lighting to sunset" without regenerating from scratch |
| Adding legible, stylized text to images is notoriously unreliable | Native SOTA text rendering with explicit quote syntax produces infographics, diagrams, and pull-quote layouts reliably |
| Maintaining consistent character identity across multiple images is brittle | Up to 14 reference images (6 with high fidelity) enable explicit "Identity Locking" across a series |
| Real-time data visualization requires separate search-to-image pipelines | Google Search grounding is built in; the model thinks over search results before generating the image |
| Manually masking areas for in-painting is slow and requires specialized tools | Semantic in-painting via natural-language instruction ("remove the tourists and fill with cobblestones") requires no masks |
| Converting floor plans or sketches into 3D renders requires dedicated 3D tools | Dimensional Translation interprets 2D schematics as structured 3D composition inputs |
| Generating tile-based sprites or LED display assets requires pixel-perfect layout alignment | Structural control via grid or wireframe reference images forces exact composition adherence |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Model ID | `gemini-3-pro-image-preview` | 2026-02-23 |
| Max reference images | 14 (6 with high fidelity) | 2026-02-23 |
| Native output resolution | 1K – 4K | 2026-02-23 |
| Thinking mode | Default on (generates interim thought images, not billed) | 2026-02-23 |
| Access | Google AI Studio (free playground) + Gemini API | 2026-02-23 |

---

## Key Features

### The Golden Rules of Prompting

These four foundational rules apply across all capability areas:

1. **Edit, Don't Re-roll** — the model understands conversational edits; if an output is 80% correct, describe only the specific change needed rather than regenerating from scratch
2. **Use Natural Language & Full Sentences** — treat the model as a human artist being briefed; grammar and descriptive adjectives produce significantly better results than comma-separated tag lists ("tag soup")
3. **Be Specific and Descriptive** — define subject, setting, lighting, and mood; specify materiality ("matte finish", "brushed steel", "soft velvet") instead of generic adjectives
4. **Provide Context** — because the model "thinks," giving the "why" or "for whom" allows it to make correct artistic inferences (e.g., "for a Brazilian high-end gourmet cookbook" implies professional plating and perfect lighting)

### Text Rendering, Infographics & Visual Synthesis

- Compress dense text or PDFs into visual aids by asking the model to "compress" the content
- Specify style explicitly: "polished editorial," "technical diagram," or "hand-drawn whiteboard"
- Enclose exact text to render in quotes within the prompt
- Capable of ingesting PDFs (e.g., earnings reports) and generating structured infographics

### Character Consistency & Viral Thumbnails

- Supports up to 14 reference images (6 with high fidelity) for "Identity Locking"
- State explicitly: "Keep the person's facial features exactly the same as Image 1"
- Describe only the change (expression, pose, setting) while holding identity constant
- Combined identity + bold graphics + text in a single generation pass

### Grounding with Google Search

- Instructs the model to search for current data before generating images
- Suited for real-time data visualization (stock values, trends, event schedules)
- Model "thinks" (reasons) over search results before rendering; double-check outputs as synthesis can mix information

### Advanced Editing, Restoration & Colorization

- **In-painting**: Remove objects and fill with semantically coherent background content via plain language
- **Restoration**: Fix old or damaged photos
- **Colorization**: Apply style palettes to B&W manga or archival photos
- **Style swapping and localization**: Translate text within images and adapt cultural context in one pass
- **Physics-aware editing**: Complex changes like "fill this glass with liquid" respect physical constraints

### Dimensional Translation (2D ↔ 3D)

- Convert 2D floor plans into photorealistic 3D interior design boards
- Generate orthographic blueprints from 3D rendered subjects
- Translate meme compositions into photorealistic 3D renders with material specification

### High-Resolution & Textures

- Explicitly request "2K" or "4K" for high-fidelity asset generation
- Describe fine details (imperfections, surface textures) to activate full resolution capability
- Thinking Mode handles complex layered compositions (e.g., deconstructed food infographics with labeled layers)

### Thinking & Reasoning

- Default thinking mode generates internal "thought images" (not billed) to refine composition
- Solves visual logic problems: equation whiteboards, architectural reasoning ("show what this room looked like before drywall")
- Interim thought images guide the final composition without adding to token cost

### One-Shot Storyboarding & Concept Art

- Generates sequential image narratives in a single conversational session
- Specify identity/attire consistency explicitly per frame while allowing varied angles and expressions
- Use numbered parts ("9-part story, generate one at a time") to maintain coherent narrative flow
- Applicable for fake film concept art, brand story commercials, and comic-style sequences

### Structural Control & Layout Guidance

- Upload a hand-drawn sketch, wireframe, or grid to precisely control element placement in the final output
- Grid images constrain pixel art generation cell-by-cell, enabling LED matrix display asset creation
- Sprite sheet animation frames can be generated from a reference grid and extracted as GIF cells programmatically
- UI mockup generation from wireframes adheres to button placement and grid structure

---

## Technical Architecture

Nano-Banana Pro is accessed via the Gemini API as `gemini-3-pro-image-preview`. The model uses a "Thinking" pipeline that generates internal reasoning steps (interim thought images) before the final billable output. This multi-step inference enables physics reasoning and compositional planning that single-pass image models cannot perform.

<eg>
User Prompt + Reference Images (up to 14)
    │
    ▼
Thinking Stage (interim thought images — not billed)
    │
    ▼
Final Image Generation (1K–4K, billed)
    │
    ▼
Conversational Edit Loop (incremental deltas, not full regenerations)
</eg>

Google Search grounding inserts a web retrieval step before the Thinking Stage when real-time data is needed:

<eg>
User Prompt → Google Search → Retrieved Data → Thinking Stage → Final Image
</eg>

---

## Installation & Usage

Access via [Google AI Studio](https://aistudio.google.com/) (no install) or the Gemini API:

```bash
pip install google-genai
# or with uv:
uv add google-genai
```

**Generate an image**:

```python
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents="A cinematic wide shot of a futuristic sports car speeding through a rainy Tokyo street at night.",
    config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
)

for part in response.candidates[0].content.parts:
    if part.inline_data:
        with open("output.png", "wb") as f:
            f.write(part.inline_data.data)
```

See the [Gemini Cookbook Colab](https://colab.sandbox.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Get_Started_Nano_Banana.ipynb) for complete examples with reference image uploads.

---

## Relevance to Claude Code Development

### Applications

- **Prompt design patterns**: The four Golden Rules (Edit Don't Re-roll, Natural Language, Be Specific, Provide Context) are model-agnostic principles applicable to any SKILL.md prompt design, including Claude Code skills
- **Reference for multimodal skill prompting**: Skills that generate or manipulate images via tool calls (e.g., a future `image-generation` plugin) can adopt the structured prompt patterns from this guide
- **Structural control metaphor**: The sketch/wireframe-as-layout-constraint pattern maps to how structured output schemas constrain LLM text generation — a pattern worth documenting in prompt-engineering skills

### Patterns Worth Adopting

- **Edit-don't-regenerate loop**: In agentic workflows, prefer targeted follow-up tool calls that modify a prior result over full regeneration; reduces token cost and preserves context
- **Context-as-constraint**: Providing "for whom" context (audience, brand, format) as part of a task description guides model decisions implicitly — applicable to system prompt design in Claude Code agents
- **Explicit identity anchoring**: In multi-turn agentic tasks requiring consistency (e.g., maintaining a persona or output style across steps), explicit "keep X exactly the same" instructions outperform relying on implicit memory
- **Thinking-first pipeline**: Pre-generation reasoning before committing to output — analogous to how Claude Code agent orchestration benefits from a planning step before execution

### Integration Opportunities

- A future `image-generation` Claude Code plugin could use `gemini-3-pro-image-preview` via the Gemini API for tasks where image output is needed alongside text responses
- The Google Search grounding pattern (retrieve → think → generate) mirrors the research-curator skill's workflow and could inform its agent design
- Structural control via reference images could be applied to diagram generation skills: provide a layout skeleton image and generate a populated architecture diagram

### Competitive Analysis

| Capability | Nano-Banana Pro (Gemini 3 Pro Image) | DALL-E 3 (OpenAI) | Imagen 4 (Google) |
|------------|--------------------------------------|-------------------|-------------------|
| Native text rendering | SOTA | Good | Good |
| Character consistency via reference images | Up to 14 refs | Limited | Limited |
| Google Search grounding | Built-in | No | No |
| Thinking/reasoning mode | Default | No | No |
| Semantic in-painting (no mask) | Yes | Partial | Partial |
| Native resolution | 1K–4K | Up to 1792×1024 | Up to 2K |
| Conversational editing | Yes (full context) | Limited | Limited |
| Structural layout via wireframe input | Yes | No | No |

---

## References

- [Nano-Banana Pro Prompting Guide: Strategies](https://dev.to/googleai/nano-banana-pro-prompting-guide-strategies-1h9n) (accessed 2026-02-23)
- [Introducing Nano-Banana Pro: Complete Developer Tutorial](https://dev.to/googleai/introducing-nano-banana-pro-complete-developer-tutorial-5fc8) (accessed 2026-02-23)
- [Gemini API Cookbook — Get Started with Nano-Banana Pro (Colab)](https://colab.sandbox.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Get_Started_Nano_Banana.ipynb) (accessed 2026-02-23)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs) (accessed 2026-02-23)
- [Google AI Studio](https://aistudio.google.com/) (accessed 2026-02-23)

---
