"""Categorization logic: assign multi-label topic tags to a single paper.

The taxonomy lives here as ``PaperTopics`` — one boolean field per topic, each with a
``title`` (the display label) and a ``description`` (the guidance the model tags by).
That schema is the single source of truth: ``complete_structured`` serializes it (with
the descriptions) to the model, so the prompt itself names no categories.
"""

from pydantic import BaseModel, Field

from arxiv_digest.clients.arxiv import Paper
from arxiv_digest.clients.llm import complete_structured

_SYSTEM_PROMPT = (
    "You tag machine-learning papers with topic labels for a research digest. Given a "
    "paper's metadata, decide which of the provided topic fields apply. Set a field true "
    "only if the paper substantively concerns that topic — judge by the field descriptions, "
    "not a passing mention. Most papers fit one to three topics; leave the rest false."
)


class PaperTopics(BaseModel):
    """Multi-label topic membership for one paper (each field true iff it applies)."""

    # Topical — what the paper is about
    llms: bool = Field(
        default=False,
        title="LLMs",
        description="Large language models: pretraining, prompting, fine-tuning, evaluation",
    )
    nlp: bool = Field(
        default=False,
        title="NLP",
        description="Language tasks beyond LLMs: translation, information extraction, parsing",
    )
    computer_vision: bool = Field(
        default=False,
        title="Computer Vision",
        description="Image/video understanding: detection, segmentation, recognition",
    )
    multimodal: bool = Field(
        default=False,
        title="Multimodal",
        description="Cross-modal models: vision-language, audio-text, any modality fusion",
    )
    speech_audio: bool = Field(
        default=False,
        title="Speech & Audio",
        description="Speech recognition/synthesis, audio generation and understanding",
    )
    diffusion_models: bool = Field(
        default=False,
        title="Diffusion Models",
        description="Diffusion and score-based generative models",
    )
    generative_models: bool = Field(
        default=False,
        title="Generative Models",
        description="Other generative models: GANs, VAEs, normalizing flows, autoregressive",
    )
    graph_neural_networks: bool = Field(
        default=False,
        title="Graph Neural Networks",
        description="Graph learning, GNNs, geometric deep learning",
    )
    reinforcement_learning: bool = Field(
        default=False,
        title="Reinforcement Learning",
        description="RL, control, policy learning, bandits",
    )
    agents: bool = Field(
        default=False,
        title="Agents",
        description="Tool-use, multi-agent, and autonomous/agentic systems",
    )
    reasoning: bool = Field(
        default=False,
        title="Reasoning",
        description="Mathematical, logical, planning, or multi-step reasoning",
    )
    retrieval_rag: bool = Field(
        default=False,
        title="Retrieval & RAG",
        description="Retrieval, ranking, and retrieval-augmented generation",
    )
    time_series: bool = Field(
        default=False,
        title="Time Series",
        description="Forecasting and sequential/temporal modelling",
    )
    model_architectures: bool = Field(
        default=False,
        title="Model Architectures",
        description="New backbones or building blocks: transformers, SSMs, attention variants",
    )
    representation_learning: bool = Field(
        default=False,
        title="Representation Learning",
        description="Self-supervised, contrastive, and representation/embedding learning",
    )
    ai_for_science: bool = Field(
        default=False,
        title="AI for Science",
        description="Applications to biology, chemistry, materials, health, or physics",
    )

    # Transversal — the paper's primary concern or method
    optimization: bool = Field(
        default=False,
        title="Optimization",
        description="Optimizers, training dynamics, and optimization/control methods",
    )
    efficient_ml: bool = Field(
        default=False,
        title="Efficient ML",
        description="Quantization, distillation, pruning, and fast/cheap inference",
    )
    theory: bool = Field(
        default=False,
        title="Theory",
        description="Learning theory, statistical theory, and formal analysis",
    )
    safety_alignment: bool = Field(
        default=False,
        title="Safety & Alignment",
        description="Alignment, robustness, red-teaming, and guardrails",
    )
    interpretability: bool = Field(
        default=False,
        title="Interpretability",
        description="Explainability, mechanistic interpretability, and probing",
    )
    benchmarks_datasets: bool = Field(
        default=False,
        title="Benchmarks & Datasets",
        description="New benchmarks, evaluations, or released datasets",
    )


def _selected_titles(topics: PaperTopics) -> list[str]:
    """Return the display titles of the topics the model marked true."""
    return [
        field.title or name
        for name, field in PaperTopics.model_fields.items()
        if getattr(topics, name)
    ]


def _format_metadata(paper: Paper) -> str:
    """Render the metadata the categorizer judges (no full text — it runs before parsing)."""
    authors = ", ".join(a.name for a in paper.authors) or "—"
    return (
        f"Title: {paper.title}\n"
        f"Authors: {authors}\n"
        f"Primary category: {paper.primary_category}\n"
        f"Abstract: {paper.abstract}"
    )


async def categorize_paper(paper: Paper) -> list[str]:
    """Assign zero or more topic tags to a paper from its metadata."""
    topics = await complete_structured(_SYSTEM_PROMPT, _format_metadata(paper), PaperTopics)
    return _selected_titles(topics)
