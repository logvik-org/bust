# bust 1.0.0 release roadmap

Living tracking artifact owned by the release manager. Reconciled against the
GitHub issue backlog each session. Source of truth for what ships in 1.0.0, what
is deferred (with reason), and the open decisions that gate the release.

Integration branch: `claude/lucid-ritchie-f86qnt` (release vehicle is the draft
tracking PR #164 into `master`). Current version: `1.0.0a0`, the first 1.0.0
pre-release, published for selected testers before the final release.

## Where the work actually stands

The local-bus refactor is **complete and merged on the integration branch**, well
beyond what the older design docs (`local-bus-hdl.md`, `generator-step3-scope.md`)
imply. Verified state:

- Local-bus HDL architecture (`<mod>_localbus_pkg`, `<mod>_regfile_pkg`,
  `<mod>_regfile`, per-bus endpoints, thin top) designed (step 1) and UVVM-verified
  (step 2).
- Full bust 1.0 access-mode system in the domain model: `SwAccess`, `HwAccess`,
  `OnRead`, `OnWrite`, modifiers (`we`/`wel`/`hwset`/`hwclr`/`swmod`/`swacc`),
  `singlepulse`, `enums`, register-level defaults with per-field override, and a
  legacy-schema compatibility layer (`bust/core/legacy_schema.py`).
- Generator emits the verified architecture for all six buses (AXI4-Lite, IPBus,
  SBI, Avalon-MM, Wishbone, APB); legacy PIF generators, templates, and CLI flags
  retired.
- Access modes expressed in generated headers (C/C++/Python/IPBus-XML) and LaTeX.
- Generated UVVM testbenches cover the access-mode matrix for all six buses.
- Goldens regenerated for `example_axi`, `example_ipbus`, and the full-coverage
  `example_prototype`.
- CI: `mypy bust` clean; `pytest` green (`test_doc` requires `pylatexenc`, run in
  CI); `vhdl_sim.yml` simulates the prototype, the generated regfile package, and
  the generated endpoints **and** testbenches for all six buses end-to-end.

Consequence: 1.0.0 is now a **finishing/release** effort, not feature work. With
all six buses merged and doc finalization done, the only remaining 1.0.0 steps are
the `1.0.0a0` pre-release for selected testers and the final version bump
(`bump2version release` from the last pre-release to `1.0.0`, R9), the
integration -> `master` merge (R10), and the `1.0.0` tag. All three are pending
human approval.

## Environment note

`pylatexenc` (and the pinned `docopt`) fail to build wheels in the web sandbox,
so `test_doc` fails locally with `ModuleNotFoundError`. This is an env gap, not a
regression. CI installs them and runs `test_doc`. Do not treat the local
`test_doc` failure as a code problem.

## Remaining 1.0.0 work

| # | Item | Type | Status | Notes |
|---|------|------|--------|-------|
| R1 | Backlog reconciliation (triage every open issue to 1.0 / deferred) | release | in progress | this document |
| R2 | Doc finalization: normalize org refs to `logvik-org`, fix README badge + "dev branch" link, pyproject `Homepage` (`grottviq` -> `logvik-org`) | docs | done | badge, dev-branch/clone URLs, `Homepage`, sim GHCR cache namespace all on `logvik-org`; vip_ipbus dependency left alone |
| R3 | Decide CONTRIBUTING.md / CODE_OF_CONDUCT.md: add them or drop README links | docs | done | added minimal CONTRIBUTING.md + Contributor Covenant v2.1 CODE_OF_CONDUCT.md |
| R4 | License resolved (#90): switched MIT -> Apache License 2.0 (PR #190, merged). LICENSE + NOTICE + README + pyproject classifier + CLAUDE.md + source headers updated | legal/scope | done | no golden churn (generated files carry no header) |
| R5 | Bus scope DECIDED: ship all six prototyped buses. All merged: AXI4-Lite + IPBus, plus SBI (#13), Avalon-MM (#75), Wishbone (#1), APB. Each = endpoint generator template + generated TB + goldens + sim wiring, one PR per bus | scope | done | all six endpoints, TBs, goldens, and sim wiring merged |
| R6 | Independent adversarial review of the shared foundation (regfile/access-mode generation, schema/validation/legacy) before building the new buses | verify | done | foundation sound; 3 defects fixed, 2 minor deferred (below) |
| R7 | Sim verification | verify | done, via CI | no Docker locally; `vhdl_sim.yml` runs nvc on every `example/**/*.vhd` + `hdl/**/*.vhd` per PR; all six buses simulate |
| R8 | Mark design docs historical; ensure no stale "in progress / not yet" language remains user-facing | docs | done | `local-bus-hdl.md`/`generator-step3-scope.md` carry a historical-record note pointing here |
| R9 | Versioning switched to PEP 440 and set to `1.0.0a0` for a tester pre-release; further `a`/`b`/`rc` pre-releases as feedback requires, then `bump2version release` to `1.0.0` | release | in progress | the maintainer publishes each pre-release as a GitHub pre-release |
| R10 | Un-draft + merge PR #164 to `master` (merge method), tag `1.0.0`, draft release notes | release | **needs human** | requires approval |

## Backlog triage (34 open issues)

### Resolved by the refactor — close as part of 1.0.0 (verify first)
- **#144** Refactor access handling, SystemRDL alignment — the whole refactor.
- **#143** Internal/local bus interface template — implemented (local bus).
- **#104** Register enumerated values — implemented (`enums` -> VHDL enum type).
- **#108** Rename PIF — PIF retired; `regfile` naming throughout.
- **#107** Restructure AXI pif (fewer processes) — superseded by the regfile.
- **#106** Volatile registers (bus + user writable) — covered by `sw rw` + `hw rw`.
- **#109** Remove TB script generation — bust no longer emits sim run-scripts.
- **#120** VHDL verification test framework — `sim/` + generated-TB simulation in CI.
- **#49** pulse-register TB bug — new `singlepulse` model + regenerated TB; confirm
  the original failure mode is gone (legacy `pulse_cycles != 1` is now reported,
  not silently mis-generated).
- **#76** Refactor codebase (partial) — Jinja2, f-strings, `core/generators/...`
  layout done; confirm remaining sub-boxes before closing or keep open scoped.

### Shipped in 1.0.0 (all six prototyped buses merged)
- **#1** Wishbone, **#13** SBI, **#75** Avalon-MM, and APB are all merged, alongside
  AXI4-Lite and IPBus. Each landed as endpoint-template + generated-TB + goldens +
  sim wiring, one PR per bus, sequenced after the foundation review (R6). Close the
  issues as part of 1.0.0.

### Deferred to post-v1 (out of scope, with reason)
- **#98** SystemRDL "beyond" features (counters, interrupts, FIFO/LIFO, array regs,
  RAM) — explicitly deferred; each needs design sign-off.
- **#155** Raw whole-register HW access — explicitly post-v1 in the issue.
- **#62 / #167** vsg style / auto-run vsg — output-style enhancement; post-v1
  unless promoted.
- **#112** pydantic models, **#117** error/logging consistency, **#118** split test
  suite, **#102** CLI, **#101** editor stability, **#103** testing strategy —
  quality refactors, post-v1.
- **#93** IP-XACT export, **#94** SystemRDL export, **#95** TOML input,
  **#96** Markdown docs, **#99** revision number — new-format features, post-v1.
- **#122** Sphinx API docs, **#39** API/CLI docs, **#123** README contribution
  guide — documentation enhancements; #123/#39 partially overlap R2/R3.
- **#125** dependency mgmt + security scanning, **#126** perf regression testing —
  priority-low infra, post-v1.

### Resolved by a release decision
- **#90** License change — RESOLVED: adopted Apache License 2.0 (PR #190 merged). Close as part of 1.0.0.

## Foundation review (R6) outcome

Two independent adversarial reviewers covered (a) regfile/access-mode VHDL
generation and (b) the schema/model/validation/legacy translation. The full sw/hw
matrix, we/wel, hwclr>hwset>we>sw precedence, the eight onwrite effects, onread,
singlepulse, swmod/swacc, bit slices, base-address handling, and the 1-cycle AXI/
IPBus handshake all matched the verified prototype. Three defects were found and
fixed before building the new buses:

- **Enum encode by position, not value (critical).** `to_slv` used the VHDL
  literal position; sparse/reordered enums round-tripped wrong. Now a value-keyed
  `case`, with a regression test and the hand-written prototype pkg updated to match.
- **Enum reset outside the declared set (major).** An explicit reset matching no
  enum value silently fell back to the first literal; now rejected.
- **Legacy `mode` mixed with bust 1.0 keys (major).** Silently honored one and
  dropped the other; now rejected.
- Plus a diagnostic fix: address-less register parse errors now surface as
  `InvalidRegister` instead of "An unknown error has occurred".

Deferred (tracked, not release-blocking):
- **Dead `mode` metadata.** New-schema registers default `mode=RW`, which leaks
  into the `type_vhdl` infix and `num_*_regs` counts. Cosmetic / test-only and
  internally consistent; deriving `mode` from sw/hw or dropping it churns naming
  goldens and needs a small naming decision. Open a cleanup issue.
- **singlepulse/pulse + non-zero reset.** The reset is silently ineffective
  (self-clearing field). A hard reject would break committed legacy examples
  (`example_axi`/`ipbus` reg9/reg10 carry non-zero resets), so this should be a
  warning, not an error. Track separately.

## Decisions log

- **Bus scope (RESOLVED 2026-06-28; SHIPPED).** All six prototyped buses are
  merged in 1.0.0: AXI4-Lite, IPBus, SBI, Avalon-MM, Wishbone, APB. CLAUDE.md and
  README "Bus support" text updated to match.
- **Verification (RESOLVED 2026-06-28).** Independent adversarial review + sim.
  Foundation review completed (3 defects fixed); every bus is simulated in CI per
  PR (no local Docker).
- **License (RESOLVED 2026-06-28).** Adopted Apache License 2.0 (#90, PR #190
  merged). MIT (status quo) and Polyform Noncommercial 1.0 were considered; the
  maintainer chose Apache 2.0 for permissive adoption plus an explicit patent grant.
- **Roadmap home (RESOLVED).** This doc is the source of truth; mirror into a
  pinned GitHub tracking issue once scope is frozen.

## Working agreement

- Feature/finishing work branches off `claude/lucid-ritchie-f86qnt`, PR back into
  it, one unit per PR, CI-gated, squash disabled (merge with `merge`).
- HDL and its UVVM testbench change together; goldens regenerated byte-exact on any
  output change; `mypy`/`pytest`/sim must be green.
- No version edits by hand (bumpversion); commit messages one line imperative
  <=72 chars; no em-dashes.
