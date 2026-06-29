---
title: "microgpt Playground"
last_verified: "2026-02-23"
version_at_verification: "n/a (single-file, no releases)"
next_review: "2026-05-23"
---

## Overview

microgpt Playground is a browser-native interactive demo for building, training, and running miniature GPT language models entirely inside the browser — zero server required. It is a faithful JavaScript port of Andrej Karpathy's [microgpt.py](https://gist.github.com/karpathy/8627fe009c40f57531cb18360106ce95) gist, preserving the algorithm line-for-line while adapting it for JavaScript environments (browsers and Node.js). Users supply plain text, watch the model train in real time, and generate outputs — all without any ML framework dependencies or network calls.

---

## Problem Addressed

| Problem                                                  | Solution                                                                           |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| LLM training/inference requires backend infrastructure   | Full training and inference loop runs natively in browser with no server           |
| ML frameworks are heavy, installation-intensive barriers | Zero-dependency pure JavaScript — no PyTorch, TensorFlow, or npm packages          |
| GPT internals are abstracted away by high-level APIs     | Every step (autograd, attention, Adam) hand-rolled in ~200 lines for full transparency |
| Demos that send data to external APIs compromise privacy | All computation is local; no data leaves the user's device                         |
| Python-centric ML is inaccessible to web developers      | JavaScript port unlocks browser/Node.js/Deno/Bun environments for LLM prototyping |

---

## Key Statistics

| Metric             | Value                       | Date Gathered |
| ------------------ | --------------------------- | ------------- |
| HF Space Likes     | 30                          | 2026-02-23    |
| GitHub Stars       | 65 (xenova/microgpt.js)     | 2026-02-23    |
| GitHub Forks       | 7                           | 2026-02-23    |
| Primary Language   | JavaScript                  | 2026-02-23    |
| Repository Size    | Single file (~200 lines)    | 2026-02-23    |
| License            | MIT                         | 2026-02-23    |

---

## Key Features

### Browser-Native Execution

- Runs entirely client-side with no backend, no npm install, and no build step
- Uses Web Workers to execute the training loop off the main thread, keeping the UI responsive
- Works in any modern browser as well as Node.js, Deno, and Bun runtimes

### Zero-Dependency GPT Implementation

- Implements full GPT-2-style architecture in pure JavaScript (ES modules or CommonJS)
- No external ML libraries — only native JavaScript `Math` operations and arrays
- Line-for-line translation of Karpathy's `microgpt.py`, making it ideal for comparing Python vs JS implementations

### Custom Autograd Engine

- `Value` class tracks scalar operations and computes gradients via reverse-mode autodiff (backprop)
- Implements `add`, `mul`, `tanh`, `exp`, `pow`, and composite ops with associated backward functions
- Inspired by Karpathy's [micrograd](https://github.com/karpathy/micrograd)

### Miniature GPT Architecture

- Character-level tokenizer: each unique character (+ BOS token) mapped to an integer
- Token embeddings (`wte`) and positional embeddings (`wpe`), summed per position
- Single transformer decoder block: multi-head self-attention (4 heads, 16-dim, 16-token context) + feedforward MLP
- RMSNorm (no learnable parameters) applied before each sublayer (pre-norm)
- Adam optimizer hand-rolled from first principles

### Interactive Training Playground

- Upload any `.txt` file or use the bundled `names.txt` example dataset
- Live loss display during training with periodic inference samples
- Demonstrated on character-level name generation (baby names dataset)

---

## Technical Architecture

<eg>
Input Text
    │
    ▼
Character-level Tokenizer
    │  (unique chars + BOS → int IDs)
    ▼
Embedding Lookup
    │  wte[token_id] + wpe[position]
    ▼
Transformer Decoder Block
    │  ┌─ RMSNorm
    │  ├─ Multi-Head Self-Attention (Q/K/V projections, causal mask)
    │  ├─ Residual Add
    │  ├─ RMSNorm
    │  ├─ Feedforward MLP (Linear → GELU → Linear)
    │  └─ Residual Add
    ▼
LM Head (unembedding: Linear → logits)
    │
    ▼
Softmax → Cross-Entropy Loss (training) / Sampling (inference)
    │
    ▼
Adam Optimizer Update (custom, scalar autograd)
</eg>

All operations are implemented as scalar arithmetic using the `Value` autograd class; no tensor library is used.

---

## Installation & Usage

**HuggingFace Space (no install)**:

```
https://huggingface.co/spaces/webml-community/microgpt-playground
```

**Node.js / CLI**:

```bash
# Clone and run directly — no npm install required
git clone https://github.com/xenova/microgpt.js
node microgpt.js
```

**Browser (script tag)**:

```html
<script type="module">
  import { train, generate } from './microgpt.js';
  // Load text, call train(), then generate()
</script>
```

**Web Worker (non-blocking training)**:

```js
const worker = new Worker('./microgpt-worker.js');
worker.postMessage({ text: myTextData });
worker.onmessage = (e) => console.log('Loss:', e.data.loss);
```

---

## Relevance to Claude Code Development

### Applications

- **Educational reference**: Demonstrates the complete GPT pipeline in ~200 lines — useful when building skills that explain transformer internals or LLM concepts
- **Browser-hosted agent tools**: The pattern of full ML inference running client-side (no server) applies to lightweight Claude Code plugins that need embedded inference
- **Algorithm verification**: Compare Python and JavaScript implementations side-by-side to validate porting exercises or cross-language agent skills

### Patterns Worth Adopting

- **Zero-dependency single-file design**: Ship complete functionality as one file with no external dependencies — applies to Claude Code skill scripts that need to be portable
- **Web Worker pattern for CPU-bound tasks**: Offload long-running Claude Code hooks or background skill logic to Web Workers to avoid blocking the main thread in browser-based UIs
- **Scalar autograd as teaching tool**: When building skills that teach AI concepts, a minimal autograd engine is more pedagogically effective than importing a full framework

### Integration Opportunities

- Could power a Claude Code skill that trains a tiny character-level LM on the user's codebase for local completion suggestions (no external API calls)
- Demonstrates how to run any Python ML algorithm in-browser — relevant for Claude Code plugins deployed as HuggingFace Spaces
- The HF Space deployment model (static files + JS) is a replicable pattern for lightweight Claude Code demos

---

## References

- [microgpt Playground (HuggingFace Space)](https://huggingface.co/spaces/webml-community/microgpt-playground) (accessed 2026-02-23)
- [xenova/microgpt.js (GitHub)](https://github.com/xenova/microgpt.js) (accessed 2026-02-23)
- [Karpathy's microgpt.py gist](https://gist.github.com/karpathy/8627fe009c40f57531cb18360106ce95) (accessed 2026-02-23)
- [webml-community on HuggingFace](https://huggingface.co/webml-community) (accessed 2026-02-23)
- [Andrej Karpathy's microGPT Architecture — Complete Guide](https://dev.to/rsrini7/andrej-karpathys-microgpt-architecture-complete-guide-em8) (accessed 2026-02-23)
- [Karpathy's microgpt.py Dissected](https://blog.sotaaz.com/post/microgpt-en) (accessed 2026-02-23)

---
