## Context

See proposal.md — Why.

The constraints that shape the approach:

- **The repository is public.** Any rule borrowed from a downstream project has to be
  generalised. Much of what such a project enforces — provisioning, result-tracking
  cycles, its own CLI wrapper, ticket workflow — is specific to its environment and both
  meaningless and inappropriate here.
- **Spektrum predates several of the conventions worth writing down.** `raise_a` catches
  base `Exception`, quote delimiters are mixed, older modules carry no type hints. Any
  standards document has to say what it applies to, or it reads as authorisation to
  reformat the tree.
- **`openspec/` already contains empty `specs/` and `changes/` directories.** Git cannot
  store an empty directory, so these exist only in working copies. Nothing in them is
  tracked, and nothing depends on them.
- **`tests/` is pytest, while the project itself is a spec framework.** This surprises
  every reader and needs explaining rather than restating.

## Goals / Non-Goals

**Goals:**

- An agent or new contributor can find the layout, the commands, and the review bar from
  the repository root without asking.
- The library risk profile is stated explicitly, including which modules are on the path
  that renders downstream output.
- OpenSpec tooling actually runs against this repo.
- Documents remain true for a reader with no connection to any particular downstream
  consumer.

**Non-Goals:**

- Fixing the pre-existing convention violations the standards document names. Recording a
  rule and retrofitting it are separate pieces of work; bundling them makes the diff
  unreviewable.
- Backfilling `docs/release_notes/index.rst`, which has had no entry since 1.0.0.
- Writing capability specs. This change adds no runtime behaviour.
- Documenting any specific downstream consumer's workflow.

## Decisions

**One `AGENTS.md` at the root, with `CLAUDE.md` as a symlink.** A single file avoids the
two-file drift where one copy is updated and the other rots. The symlink means
tool-specific filename expectations resolve to the same content. Alternative considered: a
`CLAUDE.md` that merely points at `AGENTS.md` — rejected, since a reader following the
pointer pays two hops for nothing.

**Split the rules by lifetime.** `openspec/project.md` holds the process that governs a
change (how to prove it, what blocks a PR, scope discipline); `.claude/conventions.md`
holds the Python standards; `AGENTS.md` holds the map. Process, style, and orientation
change on different cadences, and one combined document guarantees the stale parts drag
down trust in the fresh parts.

**Scope the conventions document to new and modified code, in its own text.** Stating this
inside the document is what stops it from being read as a reformatting mandate. Rejected
alternative: fixing the violations first so the document can be unconditional — that is a
much larger, riskier change and would have to be justified on its own merits.

**Generalise rather than copy.** Where a downstream project's rule encodes a real
engineering constraint (prove a fix with a failing test first; do not widen a diff; do not
reformat vendored code), keep the constraint and drop the environment. Where the rule is
purely about that project's infrastructure, drop it entirely. Copying wholesale would put
internal detail in a public repository and leave rules no contributor here could follow.

**Set `skip_specs: true` rather than author a token capability.** The change adds no
runtime behaviour, and OpenSpec provides this marker precisely so a docs change is not
forced to invent a requirement to pass validation.

**Document the reporter contract by consequence, not by listing files.** The useful fact
is not that `testrail.py` exists but that it is reached *per-case during a run*, so a
failure there destroys results already collected. That framing is what makes a
contributor cautious in the right place.

## Risks / Trade-offs

- **Documentation drifts from the code it describes** → Keep the file map at directory and
  responsibility granularity, not function-by-function, so ordinary changes do not
  invalidate it.
- **The standards document is read as a mandate to reformat** → Stated explicitly in the
  document itself, and again under scope discipline in `openspec/project.md`.
- **Internal detail leaks into a public repository** → Every document is written for an
  outside reader; anything naming a specific downstream product, tracker, host, or
  internal process is out. Worth an explicit grep before the PR rather than trusting a
  read-through.
- **The red-then-green rule reads as bureaucratic for a trivial fix** → It is scoped to
  behavioural changes; typo and docs changes are not covered.
- **`AGENTS.md` duplicates `README.rst`** → They address different readers: `README.rst`
  is for someone using the library, `AGENTS.md` for someone changing it. Keep the overlap
  to the commands and cross-link rather than restate.

## Migration Plan

Not applicable — additive files only, nothing to deploy or roll back. Deleting the added
files restores the previous state exactly.

## Open Questions

- Whether `CONTRIBUTING.md` and a PR template are wanted here, or whether
  `openspec/project.md` covering the same ground is enough. Deferrable: it adds a file
  without changing anything already written.
- Whether release notes should be backfilled from 1.1.0 onward, and by whom. Deferrable
  and better handled as its own change, since it means reconstructing three versions of
  history.
