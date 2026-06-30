from __future__ import annotations

from signalgraph.models import ResearchTrack

DEFAULT_TRACKS: tuple[ResearchTrack, ...] = (
    ResearchTrack(
        name="products",
        prompt=(
            "Find overseas product and startup launch signals related to the theme. "
            "Prioritize recent products, clear user pain, unusual positioning, and "
            "evidence that builders or early adopters care."
        ),
    ),
    ResearchTrack(
        name="oss",
        prompt=(
            "Find open-source and developer-tool signals related to the theme. "
            "Prioritize repositories with recent momentum, technically meaningful "
            "changes, ecosystem adoption, and practical implementation relevance."
        ),
    ),
    ResearchTrack(
        name="research",
        prompt=(
            "Find research and paper signals related to the theme. Prioritize work "
            "that could become product capability, infrastructure shifts, benchmarks, "
            "or applied techniques within 6-18 months."
        ),
    ),
    ResearchTrack(
        name="community",
        prompt=(
            "Find community signals from builders, operators, or early adopters. "
            "Prioritize concrete complaints, workflows, adoption friction, surprising "
            "use cases, and repeated discussion patterns."
        ),
    ),
    ResearchTrack(
        name="funding",
        prompt=(
            "Find funding, accelerator, and startup ecosystem signals related to the "
            "theme. Prioritize capital movement, new categories, and evidence that "
            "investors or founders are clustering around a problem."
        ),
    ),
)
