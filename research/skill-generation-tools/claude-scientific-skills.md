# Claude Scientific Skills

**Research Date**: 2026-03-16
**Source URL**: <https://github.com/K-Dense-AI/claude-scientific-skills>
**GitHub Repository**: <https://github.com/K-Dense-AI/claude-scientific-skills>
**Version at Research**: Latest commit 575f1e5 (2026-03-11)
**License**: MIT License

---

## Overview

Claude Scientific Skills is a comprehensive open-source repository containing 170+ ready-to-use scientific and research skills for AI agents following the Agent Skills standard. Created by K-Dense Inc., it provides curated documentation, examples, and best practices for scientific libraries, databases, and tools spanning bioinformatics, cheminformatics, clinical research, machine learning, materials science, and more. The collection includes 250+ accessible scientific and financial databases, 60+ optimized Python package skills, 15+ scientific integration skills, and 35+ analysis and communication tools.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Scientific workflows require extensive API documentation research | Pre-documented skills with curated examples and best practices eliminate setup overhead |
| Complex multi-step scientific pipelines are time-consuming to assemble | Skills enable agents to execute production-ready workflows with single prompts |
| Agent access to scientific tools is limited to package functionality alone | Explicitly defined skills with integration guides and use cases unlock compound capabilities |
| Scientists lose days configuring environments and dependencies | Skills automatically manage Python dependencies via uv package manager |
| Cross-disciplinary workflows require knowledge spanning multiple domains | 170 skills unified in one repository enable seamless bioinformatics-to-cheminformatics integration |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | Not extracted (needs live query) | 2026-03-16 |
| Total Skills | 175 skill directories | 2026-03-16 |
| Database Coverage | 250+ accessible databases | 2026-03-16 |
| Repository Size | 26 MB | 2026-03-16 |
| Latest Commit | 575f1e5 (Merge PR #91) | 2026-03-11 |
| Contributors | 50+ open source projects acknowledged | 2026-03-16 |
| Last Activity | 2026-03-11 | 2026-03-16 |

---

## Key Features

### Skill Organization by Scientific Domain

**Bioinformatics & Genomics (20+ skills)**
- Sequence analysis: BioPython, pysam, scikit-bio, BioServices
- Single-cell analysis: Scanpy, AnnData, scvi-tools, scVelo (RNA velocity), Arboreto, Cellxgene Census
- Genomic tools: gget, geniml, gtars, deepTools, FlowIO, Zarr, TileDB-VCF for scalable variant storage
- Phylogenetics: ETE Toolkit, MAFFT, IQ-TREE 2, FastTree

**Cheminformatics & Drug Discovery (13+ skills)**
- Molecular manipulation: RDKit, Datamol, Molfeat
- Deep learning: DeepChem, TorchDrug
- Docking & screening: DiffDock for structure-based drug design
- Molecular dynamics: OpenMM + MDAnalysis for MD simulation and trajectory analysis
- Drug-likeness: MedChem, BindingDB for drug-target binding affinities
- Benchmarks: PyTDC for pre-curated drug discovery datasets

**Clinical Research & Precision Medicine (16+ skills)**
- Clinical databases: ClinicalTrials.gov, ClinVar, ClinPGx, COSMIC, FDA Databases
- Cancer genomics: cBioPortal (somatic mutations, CNAs, expression across 400+ studies), DepMap (cancer dependency scores)
- Disease-gene associations: Monarch Initiative (OMIM, ORPHANET, HPO cross-species data)
- Healthcare AI: PyHealth, NeuroKit2, Clinical Decision Support
- Variant analysis: Ensembl, NCBI Gene integration

**Machine Learning & AI (16+ skills)**
- Deep learning: PyTorch Lightning, Transformers, Stable Baselines3, PufferLib
- Classical ML: scikit-learn, scikit-survival, SHAP
- Time series: aeon, TimesFM (Google's zero-shot foundation model)
- Bayesian methods: PyMC
- Graph ML: Torch Geometric for network analysis
- Statistical modeling: statsmodels

**Scientific Communication (24+ skills)**
- Literature: OpenAlex, PubMed, bioRxiv, Literature Review
- Advanced paper search: BGPT Paper Search (25+ structured fields extracted from full text)
- Web search: Perplexity Search (AI-powered with real-time info), Parallel Web (synthesized summaries)
- Scientific writing, peer review, and document processing
- Presentations: Scientific Slides, LaTeX Posters, PPTX Posters
- Citation management and publishing workflows

**Scientific Databases (37+ dedicated skills → 250+ databases total)**
- Protein: UniProt, PDB, AlphaFold DB, InterPro
- Chemical: PubChem, ChEMBL, DrugBank, ZINC, HMDB, BindingDB
- Genomic: Ensembl, NCBI Gene, GEO, ENA, GWAS Catalog, gnomAD, GTEx, JASPAR
- Clinical: ClinVar, COSMIC, ClinicalTrials.gov, cBioPortal, DepMap, Monarch Initiative
- Imaging: NCI Imaging Data Commons (radiology & pathology datasets)
- Financial: edgartools (SEC filings), FRED (800,000+ economic time series), Alpha Vantage

### Cross-Domain Integration Capability

Skills are bundled together in one repository specifically to enable interdisciplinary workflows. Users can combine genomics + cheminformatics + clinical data + machine learning in a single agent prompt without managing separate packages or repositories.

### Standards Compliance

All skills follow the open Agent Skills specification (agentskills.io), ensuring compatibility with Cursor, Claude Code, Codex, and Gemini CLI.

---

## Technical Architecture

### Skill Structure

Each skill is a self-contained directory following the Agent Skills standard with:
- `SKILL.md` file: Metadata frontmatter (name, description, license) plus comprehensive documentation
- `references/` directory: Additional documentation, examples, and integration guides
- Frontmatter-based metadata enabling agent auto-discovery

Example SKILL.md structure:
```yaml
---
name: scanpy
description: Standard single-cell RNA-seq analysis pipeline
license: BSD-3-Clause license
metadata:
    skill-author: K-Dense Inc.
---
```

Source: scientific-skills/scanpy/SKILL.md — SKILL metadata format

### Dependency Management

Skills declare Python dependencies in their SKILL.md files. The repository recommends `uv` as the primary package manager for automated dependency installation. Each skill can be independently installed by copying its directory to the agent's skills folder:

```bash
cp -r claude-scientific-skills/scientific-skills/scanpy ~/.claude/skills/
```

### Database Access Pattern

Database skills provide optimized REST API or programmatic access to 250+ databases:
- Direct skills: Single-database access (e.g., ChEMBL, PubMed)
- Multi-database packages: Collective access (BioServices: 40 bioinformatics services + 30+ PSICQUIC databases; BioPython: 38 NCBI Entrez sub-databases; gget: 20+ genomics databases)

### Integration with K-Dense Web

The repository documents that K-Dense Web (k-dense.ai) is the hosted platform built on top of these open-source skills, offering cloud GPUs, 200+ exclusive skills, and publication-ready output generation.

---

## Installation & Usage

### Installation

Clone the repository and copy skills to your agent's skills directory:

```bash
git clone https://github.com/K-Dense-AI/claude-scientific-skills.git
cp -r claude-scientific-skills/scientific-skills/* ~/.claude/skills/
```

Supported agent skill directories:
- **Cursor**: `~/.cursor/skills/` or `.cursor/skills/` (project-level)
- **Claude Code**: `~/.claude/skills/` or `.claude/skills/` (project-level)
- **Codex**: `~/.codex/skills/` or `.codex/skills/` (project-level)
- **Gemini CLI**: `~/.gemini/skills/` or `.gemini/skills/` (project-level)

### Prerequisites

- Python 3.9+ (3.12+ recommended)
- `uv` package manager (installed via `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Client supporting Agent Skills standard (Cursor, Claude Code, Codex, Gemini CLI)

### Usage Example — Drug Discovery Pipeline

```
Use available skills you have access to whenever possible. Query ChEMBL for EGFR inhibitors (IC50 < 50nM),
analyze structure-activity relationships with RDKit, generate improved analogs with datamol, perform virtual
screening with DiffDock against AlphaFold EGFR structure, search PubMed for resistance mechanisms, check
COSMIC for mutations, and create visualizations and a comprehensive report.
```

This example leverages: ChEMBL, RDKit, datamol, DiffDock, AlphaFold DB, PubMed, COSMIC, scientific visualization skills.

Source: README.md — Quick Examples section (accessed 2026-03-16)

### Usage Example — Single-Cell RNA-seq Analysis

```python
import scanpy as sc
import pandas as pd

# Configure settings
sc.settings.verbosity = 3
sc.settings.set_figure_params(dpi=80)

# Load 10X data
adata = sc.read_10x_h5('path/to/data.h5')

# QC and preprocessing
sc.pp.calculate_qc_metrics(adata)
sc.pp.normalize_total(adata)
sc.pp.log1p(adata)
sc.tl.pca(adata)
sc.pp.neighbors(adata)
sc.tl.umap(adata)
sc.tl.leiden(adata)
```

Source: scientific-skills/scanpy/SKILL.md — Quick Start section (accessed 2026-03-16)

---

## Relevance to Claude Code Development

### Applications

- **Multi-domain workflow composition**: The repository enables unified access to 170+ skills across biology, chemistry, physics, and engineering — a pattern we could adopt for Claude Code's skill composition
- **Explicit skill metadata format**: The Agent Skills standard with `SKILL.md` frontmatter is directly applicable to our skill discovery and routing mechanisms
- **Dependency isolation**: The use of `uv` for automatic dependency management aligns with our Python runtime strategy
- **Documentation-as-skill pattern**: Curated documentation embedded in skill files (not external docs) ensures agents can reason about tool capabilities without external knowledge

### Patterns Worth Adopting

1. **Comprehensive domain coverage through modular skills**: Rather than monolithic "bioinformatics" or "cheminformatics" packages, decompose into fine-grained skills (one per library or database), each self-contained and independently discoverable
2. **Skill frontmatter-based metadata**: The SKILL.md YAML frontmatter (name, description, license, skill-author) provides machine-readable skill identity without external registries
3. **Bundled cross-domain examples**: Providing multi-step workflow examples that span domains (drug discovery combining genomics + cheminformatics + clinical data) demonstrates integration patterns to agents
4. **Open source attribution**: Acknowledging 50+ upstream projects in a centralized [open-source-sponsors.md](docs/open-source-sponsors.md) file sets a standard for upstream contribution visibility

### Integration Opportunities

- **Adopt Agent Skills standard in Claude Code skills**: Align our skill directory structure with agentskills.io to enable interoperability with other tools
- **Skill composition templates**: Document patterns for agents to combine related skills (e.g., combining Scanpy + scVelo for RNA velocity analysis)
- **Database skill taxonomy**: Create a similar structured catalog of API-driven data access skills (we have some; this shows how to scale to 250+)
- **Multi-step example library**: Adapt the "Quick Examples" pattern from this repository as a reference for providing complex workflow templates

---

## References

- [Claude Scientific Skills GitHub Repository](https://github.com/K-Dense-AI/claude-scientific-skills) (accessed 2026-03-16)
- [Agent Skills Standard Specification](https://agentskills.io/) (referenced in README.md, accessed 2026-03-16)
- [K-Dense Inc. — AI Co-Scientist Platform](https://k-dense.ai) (referenced in README.md, accessed 2026-03-16)
- [Repository README.md — Overview and Quick Examples](https://github.com/K-Dense-AI/claude-scientific-skills/blob/main/README.md) (accessed 2026-03-16)
- [Scientific Skills Documentation](https://github.com/K-Dense-AI/claude-scientific-skills/blob/main/docs/scientific-skills.md) (accessed 2026-03-16)
- [Open Source Sponsors List](https://github.com/K-Dense-AI/claude-scientific-skills/blob/main/docs/open-source-sponsors.md) (accessed 2026-03-16)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [SkillKit - Universal Package Manager for AI Agent Skills](./skillkit.md) | skill-generation-tools | Aggregates and distributes 15,000+ skills (including scientific skills) across 32 AI agents; demonstrates cross-agent skill translation patterns applicable to scientific skill distribution |
| [mcpskills-cli - MCP-to-Skill Converter](./mcpskills-cli.md) | skill-generation-tools | Generates SKILL.md files from MCP server tools; pattern applicable to converting scientific database APIs into skill format |
| [Skill Seekers - Documentation to AI Skills Automation](./skill-seekers.md) | skill-generation-tools | Automatically converts documentation websites and GitHub repositories into production-ready skills; relevant for scaling scientific skill generation from research library docs |
| [Obsidian Skills Repository](./obsidian-skills.md) | skill-generation-tools | Reference implementation of Agent Skills specification with multi-format support (Markdown, YAML, JSON); demonstrates skill decomposition pattern applicable to scientific domain skills |
| [Anthropic Agent Skills Repository](./anthropics-skills.md) | skill-generation-tools | Official Anthropic skill repository with skill-creator and mcp-builder skills; provides production skill examples and authorship guidance applicable to scientific skill development |
| [Docs MCP Server (Grounded Docs)](../mcp-ecosystem/docs-mcp-server.md) | mcp-ecosystem | Provides versioned documentation indexing for Python, JavaScript, and other scientific libraries; complements claude-scientific-skills' database access with on-demand documentation context |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-16 |
| Version at Verification | commit 575f1e5 (2026-03-11) |
| Next Review Recommended | 2026-06-16 |
| Confidence Map | `Overview: high`, `Key Features: high (code-read)`, `Technical Architecture: high (code-read)`, `Installation & Usage: high`, `Relevance: medium (inference from repository patterns)` |

---

## Notes

**High Activity Observed**: Latest commit on 2026-03-11 indicates active maintenance. Given the repository's status as a rapidly growing skill collection (175 skills, 250+ databases), recommend review at 4-6 week intervals to track:
- New skill additions and removals
- Version changes in pinned dependencies
- Major releases in upstream projects (BioPython, RDKit, Scanpy, etc.)
- K-Dense Web platform feature parity changes
