---
name: NotebookLM
description: NotebookLM (Google NotebookLM; LM = "Language Model") is a research and note-taking online tool developed by Google Labs that uses Google Gemini to assist users in interacting with their documents....
license: Proprietary (Google)
metadata:
  topic: notebooklm
  category: ai-research-tools
  source_url: https://notebooklm.google
  version: "Android 2026.01.06 / iOS 1.21.0"
  verified: "2026-01-31"
  next_review: "2026-05-01"
---

## Overview

NotebookLM (Google NotebookLM; LM = "Language Model") is a research and note-taking online tool developed by Google Labs that uses Google Gemini to assist users in interacting with their documents. Google describes it as a "virtual research assistant" that generates summaries, explanations, and answers based on user-uploaded content. Its distinctive "Audio Overviews" feature converts documents into podcast-style conversations between two AI hosts.

---

## Problem Addressed

| Problem                                             | Solution                                                                            |
| --------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Long documents are time-consuming to read           | Generates summaries and key insights from uploaded sources                          |
| Complex topics are hard to understand               | Creates explanations in simplified, structured format                               |
| Traditional notes are passive and static            | Q&A interface allows interactive exploration of document content                    |
| Text-heavy content doesn't suit all learning styles | Audio Overviews create podcast discussions; Video Overviews create visual summaries |
| Research requires manual synthesis across sources   | AI analyzes multiple documents to extract and connect key ideas                     |
| Knowledge is siloed in individual documents         | Notebook structure organizes related sources for cross-document reasoning           |

---

## Key Statistics

| Metric           | Value                          | Date Gathered |
| ---------------- | ------------------------------ | ------------- |
| Initial Release  | May 2023 (as Project Tailwind) | 2026-01-31    |
| Stable Release   | October 17, 2024               | 2026-01-31    |
| Android Version  | 2026.01.06 (Build 853388154)   | 2026-01-31    |
| iOS Version      | 1.21.0                         | 2026-01-31    |
| Platform Support | Web, Android 10+, iOS 17+      | 2026-01-31    |
| AI Model         | Google Gemini                  | 2026-01-31    |
| Language Support | 80+ languages (Audio/Video)    | 2026-01-31    |

---

## Key Features

### Document Processing

- **Multi-format support**: PDFs, Google Docs, Google Slides, websites
- **Video transcripts**: Processes videos with subtitles/transcripts (no auto-extraction)
- **Source organization**: Notebooks group related documents for cross-document analysis
- **Key idea extraction**: Identifies and structures main concepts from uploaded content

### AI-Powered Analysis

- **Summarization**: Condenses long documents into digestible summaries
- **Q&A interface**: Interactive question-answering based on source content
- **Explanation generation**: Simplifies complex topics with structured explanations
- **Cross-document reasoning**: Connects ideas across multiple uploaded sources

### Audio Overviews

- **Podcast generation**: Converts documents into conversational discussions between two AI hosts
- **Interactive mode**: Users can "Join" the conversation and ask questions directly (December 2024)
- **Language support**: Available in 80+ languages
- **Accessibility**: Makes complex content accessible through audio format

### Video Overviews (May 2025)

- **Visual summaries**: Transforms documents into slide-style videos
- **AI narration**: Combines spoken explanations with visual elements
- **Diagrams and images**: Includes generated visuals, diagrams, and structured layouts
- **Multi-language**: Supports 80+ languages

### Visualization Features (November 2025)

- **Infographics**: Generates visual infographics from source material
- **Slide Decks**: Creates presentation-ready slides
- **Nano Banana Pro**: Powered by Google's image generation model

### NotebookLM Plus (Premium Tier)

- **Higher usage limits**: Extended quotas for power users
- **Longer documents**: Support for larger document uploads
- **Collaborative notebooks**: Shared workspaces for teams
- **Enhanced controls**: Additional output customization options

---

## Technical Architecture

### Stack Components

| Component        | Technology                                |
| ---------------- | ----------------------------------------- |
| AI Model         | Google Gemini (multimodal, long-context)  |
| Audio Generation | Google AI voice synthesis                 |
| Image Generation | Nano Banana Pro (for infographics/slides) |
| Platform         | Google Labs infrastructure                |
| Integration      | Google Workspace, Google Cloud            |

### Processing Flow

<eg>
User uploads sources (PDFs, Docs, Slides, URLs)
    |
Gemini processes and indexes content
    |
User interacts via Q&A, summary requests, or overview generation
    |
AI generates responses grounded in source material
    |
Output: Text summaries, Audio Overviews, Video Overviews, Infographics
</eg>

### Source Grounding

NotebookLM responses are grounded in user-uploaded content, reducing hallucination risk by limiting AI responses to information present in the provided sources. This differs from general-purpose chatbots that draw from training data.

---

## Pricing and Availability

### Free Tier

- Basic access to NotebookLM features
- Standard usage limits
- Available via Google account

### NotebookLM Plus

- **Individual**: Via Google One AI Premium subscription
- **Enterprise**: Via Google Workspace and Google Cloud (December 2024)
- **Features**: Higher limits, longer documents, collaboration, enhanced controls

### Platform Availability

| Platform | Requirement        | App               |
| -------- | ------------------ | ----------------- |
| Web      | Any modern browser | notebooklm.google |
| Android  | Android 10+        | Google Play Store |
| iOS      | iOS 17+            | App Store         |
| iPadOS   | iPadOS 17+         | App Store         |

---

## Timeline

| Date              | Milestone                                                          |
| ----------------- | ------------------------------------------------------------------ |
| May 2023          | Introduced as "Project Tailwind" at Google I/O                     |
| 2024              | Rebranded to NotebookLM, broader rollout                           |
| September 2024    | Audio Overviews feature released                                   |
| October 17, 2024  | "Experimental" status removed, becomes stable product              |
| December 2024     | NotebookLM Plus launched (enterprise); Interactive Audio Overviews |
| February 10, 2025 | NotebookLM Plus available to individuals via Google One AI Premium |
| May 2025          | Video Overviews feature launched                                   |
| 2025              | Audio/Video Overviews expanded to 80+ languages                    |
| November 2025     | Infographics and Slide Deck features (Nano Banana Pro)             |

---

## Relevance to Claude Code Development

### Direct Applications

1. **Research Workflow**: NotebookLM demonstrates effective document synthesis patterns - grounding AI responses in provided sources to reduce hallucination.

2. **Multi-Modal Output**: The progression from text to audio to video overviews shows how to make AI-generated content accessible across different consumption preferences.

3. **Interactive AI Sessions**: The "Join" feature for Audio Overviews demonstrates real-time user participation in AI-generated content - a pattern applicable to interactive coding sessions.

4. **Source Grounding Pattern**: NotebookLM's approach of limiting responses to uploaded content is a strong anti-hallucination pattern worth studying for skill-based systems.

### Patterns Worth Adopting

1. **Notebook Organization**: Grouping related sources into notebooks enables cross-document reasoning - similar to how skills could group related references.

2. **Format Flexibility**: Same content delivered as text, audio, video, or infographics - Claude Code could offer multiple output formats for documentation.

3. **Interactive Overviews**: Users joining AI discussions could inspire interactive code review or pair programming patterns.

4. **Progressive Disclosure**: NotebookLM starts with summaries and allows drilling into details - relevant for skill documentation structure.

### Integration Opportunities

1. **Research Phase Tool**: Use NotebookLM to synthesize technical documentation before creating skills.

2. **Audio Learning**: Generate audio overviews of complex codebases for auditory learners.

3. **Documentation Synthesis**: Process multiple API docs/READMEs into unified understanding.

4. **Competitive Analysis**: Compare how NotebookLM's source grounding differs from Claude Code's skill-based approach.

### Comparison with Claude Code

| Aspect            | NotebookLM                       | Claude Code                          |
| ----------------- | -------------------------------- | ------------------------------------ |
| Primary Use       | Document research and synthesis  | Developer workflow automation        |
| Source Grounding  | User-uploaded documents          | Skills, references, codebase context |
| Output Formats    | Text, Audio, Video, Infographics | Text, code, structured outputs       |
| Interaction Model | Q&A, overview generation         | Agentic task execution               |
| Knowledge Scope   | Limited to uploaded sources      | Skills + codebase + reasoning        |
| Collaboration     | Shared notebooks (Plus)          | Shared skills, git workflows         |
| Platform          | Web, mobile apps                 | CLI, IDE integration                 |

---

## Notable Adoption

- **Spotify Wrapped 2024**: Used NotebookLM's Audio Overview feature to generate personalized podcast-style summaries of individual listening habits.
- **Enterprise Research**: Adopted by companies and students for document synthesis and research workflows.
- **Academic Use**: Students use it for studying complex topics and preparing for exams.

---

## Installation & Usage

### Getting Started

**1. Access NotebookLM**

Visit https://notebooklm.google and sign in with any Google account. No installation is required beyond a standard browser.

**2. Create a Notebook**

Click "New notebook" to create a workspace. Each notebook is an isolated workspace for organizing and analyzing related documents.

**3. Add Sources**

Click "Add" in the Sources panel to upload your first document. Supported formats include:
- PDFs
- Google Docs  
- Google Slides
- YouTube videos and links
- Website URLs

With NotebookLM Plus: Up to 300 sources per notebook (vs. 50 on the free tier).

**4. Ask Questions**

Type a question in the chat panel on the right. The chat responds strictly from your uploaded sources, reducing hallucination by grounding responses in your data.

**5. Generate Overviews**

Click the Studio tab to generate structured outputs from your sources in one click:
- **Audio Overviews**: Podcast-style conversations in four formats (Deep Dive, The Brief, The Critique, The Debate) available in 80+ languages
- **Video Overviews**: Narrated, animated deep-dive videos (launched May 2025)
- **Study Guides**: Structured summaries and key concepts
- **Flashcards**: Auto-generated review cards
- **Mind Maps**: Visual concept relationships
- **Infographics**: Visual summaries with diagrams (launched November 2025, powered by Nano Banana Pro image generation)

Source: NotebookLM feature documentation and setup guides (accessed 2026-08-10).

### Platform Availability

| Platform | Access | Requirements |
|----------|--------|--------------|
| **Web** | notebooklm.google | Any modern browser |
| **Android** | Google Play Store | Android 10+ |
| **iOS** | App Store | iOS 17+ |
| **iPad** | App Store | iPadOS 17+ |

For desktop users without a dedicated app, create a PWA shortcut: In Chrome/Edge, go to the browser menu, select "Create shortcut" or "Install site as app", and save to your desktop.

Source: NotebookLM platform support documentation (accessed 2026-08-10).

### Pricing & Limits

**Free Standard Plan**
- 100 notebooks
- 50 sources per notebook
- 50 chat queries per day
- Basic Studio features

**NotebookLM Plus** (via Google One AI Premium)
- 500 notebooks  
- 300 sources per notebook
- 500 daily chat queries
- All Studio features including Video Overviews and Infographics
- Available since February 2026 to individual users

Source: NotebookLM pricing documentation (accessed 2026-08-10).

---

## References

| Source                        | URL                                                                                     | Accessed   |
| ----------------------------- | --------------------------------------------------------------------------------------- | ---------- |
| Official Website              | <https://notebooklm.google>                                                             | 2026-01-31 |
| Google Support                | <https://support.google.com/notebooklm>                                                 | 2026-01-31 |
| Wikipedia Article             | <https://en.wikipedia.org/wiki/NotebookLM>                                              | 2026-01-31 |
| Google Blog: Introduction     | <https://blog.google/technology/ai/notebooklm-google-ai/>                               | 2026-01-31 |
| Google Blog: Audio Overviews  | <https://blog.google/technology/ai/notebooklm-audio-overviews/>                         | 2026-01-31 |
| Google Play Store             | <https://play.google.com/store/apps/details?id=com.google.android.apps.labs.tailwind>   | 2026-01-31 |
| TechCrunch: Enterprise Launch | <https://techcrunch.com/2024/12/13/google-debuts-notebooklm-for-enterprises/>           | 2026-01-31 |
| TechCrunch: Individual Plus   | <https://techcrunch.com/2025/02/10/google-expands-notebooklm-plus-to-individual-users/> | 2026-01-31 |
| Ars Technica: Audio Overviews | <https://arstechnica.com/ai/2024/09/fake-ai-podcasters-are-reviewing-my-book/>          | 2026-01-31 |
| The Verge: Project Tailwind   | <https://www.theverge.com/2023/5/10/23719866/google-project-tailwind-ai-notebook>       | 2026-01-31 |

**Research Method**: Information gathered from Wikipedia article (citing multiple primary sources), Google official blog posts, official NotebookLM website, and Google Play Store listing. Feature timeline and version numbers verified via Wikipedia citations to TechCrunch, The Verge, 9to5Google, and official Google announcements.
