# bust 1.0.0 release roadmap

Living tracking artifact owned by the release manager. Reconciled against the
GitHub issue backlog each session. Source of truth for what ships in 1.0.0, what
is deferred (with reason), and the open decisions that gate the release.

Integration branch: `lucid-ritchie-f86qnt` (release vehicle is the draft
tracking PR #164 into `master`). Current version: `1.0.0-dev`.

## Where the work actually stands

The local-bus refactor is **complete and merged on the integration branch**, well
beyond what the older design docs (`local-bus-hdl.md`, `generator-step3-scope.md`)
imply. Verified state:

- Local-bus HDL architecture (`localbus_pkg`, `<mod>_regfile_pkg`, `<mod>_regfile`,
  per-bus endpoints, thin top) designed (step 1) and UVVM-verified (step 2).
- Full bust 1.0 access-mode system in the domain model: `SwAccess`, `HwAccess`,
  `OnRead`, `OnWrite`, modifiers (`we`/`wel`/`hwset`/`hwclr`/`swmod`/`swacc`),
  `singlepulse`, `enums`, register-level defaults with per-field override, and a
  legacy-schema compatibility layer (`bust/core/legacy_schema.py`).
- Generator emits the verified architecture for AXI4-Lite and IPBus; legacy PIF
  generators, templates, and CLI flags retired.
- Access modes expressed in generated headers (C/C++/Python/IPBus-XML) and LaTeX.
- Generated UVVM testbenches cover the access-mode matrix for both buses.
- Goldens regenerated for `example_axi`, `example_ipbus`, and the full-coverage
  `example_prototype`.
- CI: `mypy bust` clean; `pytest` green (107 passed, 1 skipped; `test_doc`
  requires `pylatexenc`, run in CI); `vhdl_sim.yml` simulates the prototype, the
  generated regfile package, and the generated AXI/IPBus endpoints **and**
  testbenches end-to-end (plus SBI/Avalon/Wishbone/APB prototypes).

Consequence: 1.0.0 is now a **finishing/release** effort, not feature work.

## Environment note

`pylatexenc` (and the pinned `docopt`) fail to build wheels in the web sandbox,
so `test_doc` fails locally with `ModuleNotFoundError`. This is an env gap, not a
regression. CI installs them and runs `test_doc`. Do not treat the local
`test_doc` failure as a code problem.

## Remaining 1.0.0 work

| # | Item | Type | Status | Notes |
|---|------|------|--------|-------|
| R1 | Backlog reconciliation (triage every open issue to 1.0 / deferred) | release | in progress | this document |
| R2 | Doc finalization: normalize org refs to `logvik-org`, fix README badge + "dev branch" link, pyproject `Homepage` (`grottviq` -> `logvik-org`) | docs | todo | no issue yet |
| R3 | Decide CONTRIBUTING.md / CODE_OF_CONDUCT.md: add them or drop README links | docs | todo | files referenced but absent |
| R4 | License resolution (#90): LICENSE/README/pyproject say MIT; #90 proposes Polyform Noncommercial | legal/scope | **needs human** | blocks tag |
| R5 | Bus scope: AXI+IPBus only, or promote Wishbone (#1) into 1.0.0 | scope | **needs human** | Wishbone endpoint+TB verified as prototype |
| R6 | Independent adversarial review of the completed refactor (generator vs spec, edge cases) | verify | proposed | release-manager due diligence |
| R7 | Full sim pass on the integration branch (nvc) before release | verify | todo | confirm green, not just CI-trusted |
| R8 | Mark design docs historical; ensure no stale "in progress / not yet" language remains user-facing | docs | todo | `local-bus-hdl.md`/`step3-scope.md` read as live plans |
| R9 | Version finalize `1.0.0-dev` -> `1.0.0` via bumpversion; update doc-test pin + `.tex` goldens | release | todo (last) | after all output frozen |
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

### Deferred to post-v1 (out of scope, with reason)
- **#98** SystemRDL "beyond" features (counters, interrupts, FIFO/LIFO, array regs,
  RAM) — explicitly deferred; each needs design sign-off.
- **#155** Raw whole-register HW access — explicitly post-v1 in the issue.
- **#75** Avalon, **#13** SBI — verified prototypes exist, but bus scope is
  AXI+IPBus; adding them is template+TB work for a later release.
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

### Decision-gated (see Open decisions)
- **#90** License change — R4.
- **#1** Wishbone bus support — R5.

## Open decisions (pending human)

1. **License (#90).** MIT today vs Polyform Noncommercial 1.0 proposed. This
   changes LICENSE, README, pyproject, and every generated-file header. Must be
   settled before tagging 1.0.0.
2. **Bus scope (#5/#1).** Ship AXI+IPBus only (matches current the design notes) or
   promote Wishbone now (endpoint + TB are verified prototypes; generator is
   bus-agnostic, so it is one endpoint template + one TB body + goldens + sim).
3. **Verification depth.** Run an independent adversarial review of the generator
   against the access-mode spec and a full local nvc sim before declaring done, or
   trust the existing green CI.
4. **Roadmap home.** This doc, or also a pinned GitHub tracking issue mirroring it.

## Working agreement

- Feature/finishing work branches off `lucid-ritchie-f86qnt`, PR back into
  it, one unit per PR, CI-gated, squash disabled (merge with `merge`).
- HDL and its UVVM testbench change together; goldens regenerated byte-exact on any
  output change; `mypy`/`pytest`/sim must be green.
- No version edits by hand (bumpversion); commit messages one line imperative
  <=72 chars; no em-dashes.
