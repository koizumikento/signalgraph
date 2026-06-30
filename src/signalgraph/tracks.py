from __future__ import annotations

from signalgraph.models import ResearchTrack

DEFAULT_TRACKS: tuple[ResearchTrack, ...] = (
    ResearchTrack(
        name="products",
        prompt=(
            "Find overseas product and startup launch signals related to the theme. "
            "Focus on concrete product behavior, packaging, target users, and early "
            "adoption rather than generic category hype."
        ),
        source_priorities=(
            "Product launch pages, changelogs, pricing pages, docs, and demo videos.",
            "Product Hunt, launch directories, founder posts, and credible startup coverage.",
            "Customer quotes, public usage examples, integrations, and community reactions.",
        ),
        include_if=(
            "The product introduces a specific workflow, distribution wedge, pricing model, or UI pattern.",
            "There is evidence of early adopter pull, repeated discussion, or a clear unsolved pain.",
            "The signal suggests a product category that could localize or adapt to Japan.",
        ),
        reject_if=(
            "It is only a generic AI wrapper with no differentiated workflow or evidence of use.",
            "The source is a stale listicle, SEO page, or title-only launch mention.",
            "The Japan angle is merely 'translate it' without a business or adoption rationale.",
        ),
        scoring_notes=(
            "Raise novelty when the product changes who can perform a workflow or how fast it can be done.",
            "Raise momentum when multiple independent sources discuss adoption or concrete usage.",
            "Raise credibility when the primary product page confirms the capability.",
        ),
        japan_translation=(
            "Explain which Japanese buyer, operator, or consumer segment would care, what local friction "
            "might slow adoption, and what experiment could test demand."
        ),
    ),
    ResearchTrack(
        name="oss",
        prompt=(
            "Find open-source and developer-tool signals related to the theme. "
            "Focus on implementation momentum, ecosystem adoption, and whether the repo enables "
            "a new product or automation pattern."
        ),
        source_priorities=(
            "GitHub repositories, releases, READMEs, issues, discussions, and package registries.",
            "Technical blog posts, benchmark repos, integration examples, and developer community threads.",
            "Maintainer announcements and downstream projects using the repo.",
        ),
        include_if=(
            "The repo has recent meaningful commits, releases, stars, forks, issue activity, or integrations.",
            "The technical approach unlocks a workflow that was hard or expensive before.",
            "The project can be inspected or trialed by a small team without enterprise procurement.",
        ),
        reject_if=(
            "The repository is abandoned, mostly empty, or only a README concept.",
            "The signal is only star-count hype without technical or adoption evidence.",
            "The repo is unrelated infrastructure with no clear path to the theme or Japan-facing use.",
        ),
        scoring_notes=(
            "Raise novelty for new abstractions, protocols, eval methods, developer UX, or runtime patterns.",
            "Raise momentum for recent releases, active issues, downstream adoption, and ecosystem mentions.",
            "Raise credibility for primary repository evidence over aggregator posts.",
        ),
        japan_translation=(
            "Explain whether this could become a product feature, internal automation, developer tool, "
            "or service wedge for Japanese teams."
        ),
    ),
    ResearchTrack(
        name="research",
        prompt=(
            "Find research and paper signals related to the theme. Prioritize work "
            "that could become product capability, infrastructure shifts, benchmarks, "
            "or applied techniques within 6-18 months."
        ),
        source_priorities=(
            "arXiv, conference pages, lab blogs, benchmark reports, code releases, and model cards.",
            "Paper implementations, replication discussions, citations from practitioners, and dataset pages.",
            "Author or lab announcements that clarify intended applications and limitations.",
        ),
        include_if=(
            "The work shows a capability, cost, reliability, safety, or evaluation shift relevant to the theme.",
            "There is an implementation, benchmark, dataset, or reproducible method to inspect.",
            "The result can plausibly affect products or operations within 6-18 months.",
        ),
        reject_if=(
            "The paper is only loosely related background or lacks evidence beyond an abstract.",
            "The claim depends on a narrow benchmark with no practical path to deployment.",
            "The source cannot support a concrete Japan-facing implication.",
        ),
        scoring_notes=(
            "Raise novelty for new capabilities, cost reductions, evaluation methods, or safety constraints.",
            "Raise momentum when labs, builders, or OSS projects are already adapting the work.",
            "Raise credibility for primary papers with methods, baselines, and limitations.",
        ),
        japan_translation=(
            "Translate the technical result into product timing: what becomes possible, who should watch it, "
            "and what proof would be needed before investing."
        ),
    ),
    ResearchTrack(
        name="community",
        prompt=(
            "Find community signals from builders, operators, or early adopters. "
            "Prioritize concrete complaints, workflows, adoption friction, surprising "
            "use cases, and repeated discussion patterns."
        ),
        source_priorities=(
            "Hacker News, Reddit, Discord/forum excerpts when accessible, practitioner blogs, and comment threads.",
            "Repeated complaints, workaround posts, migration stories, and tool comparison discussions.",
            "Founder, operator, or developer posts describing real usage or failed attempts.",
        ),
        include_if=(
            "The discussion reveals a repeated pain, workaround, buying trigger, or adoption blocker.",
            "Multiple people describe similar behavior, not just one viral opinion.",
            "The signal helps explain demand, distrust, switching cost, or workflow friction.",
        ),
        reject_if=(
            "It is only sentiment, memes, culture-war commentary, or generic excitement.",
            "The source cannot be tied to a concrete user segment or workflow.",
            "The Japan implication would be pure speculation without a comparable local context.",
        ),
        scoring_notes=(
            "Raise novelty when users describe a new workaround or unexpected use case.",
            "Raise momentum when separate threads converge on the same complaint or behavior.",
            "Raise credibility when commenters provide concrete details, examples, or links.",
        ),
        japan_translation=(
            "Explain what the discussion implies about Japanese adoption barriers, localization needs, "
            "trust requirements, or customer discovery questions."
        ),
    ),
    ResearchTrack(
        name="funding",
        prompt=(
            "Find funding, accelerator, and startup ecosystem signals related to the "
            "theme. Prioritize capital movement, new categories, and evidence that "
            "investors or founders are clustering around a problem."
        ),
        source_priorities=(
            "VC blogs, accelerator batches, funding announcements, startup databases, and founder posts.",
            "Investor theses, category maps, demo day summaries, and credible startup media.",
            "Hiring pages or product pages that corroborate what the funded company actually does.",
        ),
        include_if=(
            "Funding clusters around a specific problem, buyer, infrastructure layer, or behavior shift.",
            "The company category is new, newly renamed, or gaining repeated investor attention.",
            "The signal can indicate where overseas founders expect budget to move.",
        ),
        reject_if=(
            "It is a single funding round with no category signal or operational detail.",
            "The source is only PR language without product, buyer, or market evidence.",
            "There is no plausible Japan market analogue, partner, competitor, or timing implication.",
        ),
        scoring_notes=(
            "Raise novelty for new category formation or surprising buyer/problem combinations.",
            "Raise momentum for repeated rounds, accelerator clustering, and thesis convergence.",
            "Raise credibility when product pages and investor claims corroborate each other.",
        ),
        japan_translation=(
            "Explain what capital movement suggests about timing, competitor emergence, partnership angles, "
            "or categories Japanese incumbents may copy."
        ),
    ),
)
