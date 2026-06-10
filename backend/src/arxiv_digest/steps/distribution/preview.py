"""Dummy digest data + a send helper for iterating on the email design (dev only).

No network, no LLM, no DB. ``arxiv-digest preview-email --to you@example.com [--count 20]``
renders a fake digest through the real template and sends it via SMTP, so you can tune
``render.py`` (and see how it scales) without running the pipeline.
"""

from datetime import UTC, datetime

from arxiv_digest.clients.arxiv import Author, Paper, Summary
from arxiv_digest.clients.email import send_email
from arxiv_digest.steps.distribution.render import render_digest_html

_DATE = datetime(2026, 6, 10, tzinfo=UTC)
_SPOTLIGHT_COUNT = 5
_HEADING = "Week of June 10, 2026"
_INSIGHT = (
    "Reasoning was the throughline this week, with two language-model papers attacking it from "
    "opposite ends: one gives attention a memory, the other has the model check its own work. "
    "The most practical result came from sparse-memory transformers, which keep long "
    "chain-of-thought reasoning inside a single GPU's budget."
)

# A pool of fake-but-plausible papers with human-written prose summaries (no em dashes).
_POOL: list[tuple[str, list[str], str, list[str]]] = [
    (
        "Sparse Memory Transformers for Long-Context Reasoning",
        ["LLMs", "Reasoning", "Efficient ML"],
        "The authors add a learned sparse memory to the attention layer so the model can recall "
        "earlier reasoning steps without re-reading the whole context. On long math and coding "
        "benchmarks it matches dense attention while using about 40 percent less memory, which "
        "makes longer chains of thought practical on a single GPU.",
        ["Lena Ortiz", "Wei Tan", "Priya Nair", "Marco Bianchi"],
    ),
    (
        "Self-Correcting Decoding Without Reward Models",
        ["LLMs", "Reasoning"],
        "Instead of training a separate reward model, this work lets the model critique and revise "
        "its own drafts during decoding using a lightweight confidence signal. The result is "
        "steadier multi-step reasoning and fewer arithmetic slips, with no extra human labels and "
        "only a small cost at inference time.",
        ["Hannah Cole", "Yusuf Demir", "Aria Patel"],
    ),
    (
        "Diffusion Priors for One-Shot 3D Reconstruction",
        ["Computer Vision", "Diffusion Models", "Generative Models"],
        "A pretrained image diffusion model is repurposed as a geometry prior, letting the method "
        "reconstruct a full 3D shape from a single photo without any 3D supervision. "
        "Reconstructions look noticeably cleaner on thin structures like chair legs and bicycle "
        "spokes, where earlier single-view methods tend to blur or hallucinate.",
        ["Sofia Marchetti", "Kenji Watanabe", "Olu Adeyemi", "Greta Lindqvist", "Tom Reyes"],
    ),
    (
        "Offline Reinforcement Learning with Latent World Models",
        ["Reinforcement Learning", "Model Architectures"],
        "By learning a compact world model and planning inside it, the agent gets more out of "
        "fixed offline datasets and avoids the overestimation problems of value-based methods. "
        "Across locomotion and manipulation tasks it improves sample efficiency and transfers "
        "better to slightly changed environments.",
        ["Diego Fuentes", "Mei Lin", "Jonas Berg"],
    ),
    (
        "Contrastive Pretraining for Low-Resource Speech Recognition",
        ["Speech & Audio", "Representation Learning"],
        "A simple contrastive objective on unlabeled audio narrows the gap between high and low "
        "resource languages, cutting word error rates on several underserved languages by double "
        "digits without any new labeled data.",
        ["Amara Diallo", "Sven Holm", "Rina Suzuki"],
    ),
    (
        "Token-Routed Mixtures for Cheaper Multimodal Models",
        ["Multimodal", "Efficient ML"],
        "Routing each token to a small subset of experts lets a vision-language model scale "
        "capacity without scaling cost. It reaches the quality of a much larger dense model while "
        "running roughly twice as fast at inference.",
        ["Bilal Khan", "Eva Novak", "Carlos Mendez"],
    ),
    (
        "Benchmarking Long-Horizon Planning in Open-Ended Worlds",
        ["Agents", "Benchmarks & Datasets"],
        "A new benchmark stresses agents on tasks that span hundreds of steps, and finds that "
        "today's strongest planners still collapse once goals require remembering decisions made "
        "far in the past. The authors release the tasks and a reproducible harness.",
        ["Nadia Farouk", "Peter Schulz", "Yuki Tanaka"],
    ),
    (
        "Provable Robustness Bounds for Graph Neural Networks",
        ["Graph Neural Networks", "Theory"],
        "This paper derives tight certificates for how much a graph can be perturbed before a GNN "
        "changes its prediction, turning robustness from an empirical hope into something you can "
        "actually guarantee for safety-critical graphs.",
        ["Irene Castillo", "Tomas Varga"],
    ),
    (
        "Time-Series Foundation Models that Respect Seasonality",
        ["Time Series", "Model Architectures"],
        "By baking seasonal structure directly into the architecture, this forecasting model "
        "generalizes across domains with little fine-tuning and beats specialized baselines on "
        "retail, energy, and traffic data.",
        ["Omar Haddad", "Lucia Romano", "Felix Brandt"],
    ),
    (
        "Interpretable Circuits for Arithmetic in Small Transformers",
        ["Interpretability", "LLMs"],
        "The authors reverse-engineer exactly how a small transformer adds numbers, identifying a "
        "compact circuit and showing it transfers to larger models. It is a clean case study in "
        "reading a network's computation rather than guessing at it.",
        ["Sara Ahmed", "Daniel Frost", "Mona Iqbal"],
    ),
]


def _paper(index: int) -> Paper:
    title, topics, short, authors = _POOL[index % len(_POOL)]
    cycle = index // len(_POOL)
    arxiv_id = f"2606.{10001 + index}"
    return Paper(
        arxiv_id=arxiv_id,
        entry_id=f"https://arxiv.org/abs/{arxiv_id}",
        title=title if cycle == 0 else f"{title} (part {cycle + 1})",
        abstract=short,
        authors=[Author(name=name) for name in authors],
        primary_category=topics[0],
        categories=topics,
        published=_DATE,
        updated=_DATE,
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        topics=topics,
        summary=Summary(short=short, long="", conclusions=""),
    )


def dummy_papers(count: int) -> list[Paper]:
    """``count`` fake papers cycling through the pool, each with a unique id."""
    return [_paper(i) for i in range(count)]


async def send_preview(to: str, count: int) -> None:
    """Render a ``count``-paper dummy digest through the real template and email it to ``to``."""
    papers = dummy_papers(count)
    # Spotlight the first paper of the first few topics, so the Spotlight section is varied.
    seen: set[str] = set()
    highlights: list[str] = []
    for paper in papers:
        if paper.primary_category not in seen:
            seen.add(paper.primary_category)
            highlights.append(paper.arxiv_id)
        if len(highlights) == _SPOTLIGHT_COUNT:
            break
    html = render_digest_html(
        _HEADING,
        _INSIGHT,
        papers,
        interests=[],
        unsubscribe_url="https://example.com/functions/v1/unsubscribe?token=preview",
        highlights=highlights,
    )
    await send_email(to=to, subject=f"arXiv ML Digest: preview ({count} papers)", html=html)
