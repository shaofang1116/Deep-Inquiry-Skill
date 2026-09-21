# ADR 0001: One-Way v1 Import Boundary

## Status

Accepted for Task 10 on 2026-09-17.

## Context

The v1 session contains useful knowledge and teaching-era state. The vNext
topic is the only durable knowledge owner, but its claim, evidence, gap, and
counterexample contracts cannot represent every v1 field without inventing
knowledge semantics.

An explicit repeat import must create a new immutable topic version. It must
not overwrite knowledge that has evolved through the vNext learner.

## Decision

1. `TopicKnowledge` has optional `migration_metadata`. It is canonical
   provenance, not active knowledge and not an input to convergence.
2. The importer accepts exactly v1 (`schema_version == 1`). Missing optional
   collections are valid partial input; malformed fields that are present are
   rejected.
3. Representable v1 knowledge maps into claims, evidence, counterexamples, and
   gaps. Unsupported rule annotations, evidence context, counterexample
   context, and teaching state remain under `migration_metadata`.
4. Imported gaps use low priority and low expected gain because v1 has no
   equivalent fields. Later learning must assess their value explicitly.
5. Default import creates version 1 and rejects an existing topic.
6. Explicit repeat import is allowed only when the current topic is an
   importer-owned snapshot and its version equals the last imported target
   version recorded in metadata. Any later vNext save blocks re-import.
7. The source bytes are read once, hashed, checked again before commit, and
   never written. A post-commit source change does not turn a durable success
   into a reported failure; the committed metadata identifies the exact bytes
   imported.
8. `KnowledgeStore` remains the only durable writer.

## Consequences

- Import provenance and unsupported legacy context are auditable without
  reactivating teaching behavior.
- A changed v1 source can be explicitly re-imported while the topic remains
  importer-owned.
- Re-import cannot erase post-import vNext learning.
- Imported unresolved items do not falsely assert high expected value.
- Existing non-imported topics omit `migration_metadata`, preserving their
  canonical shape.

## Rejected Alternatives

- Return-only metadata: not durable enough to govern later re-import.
- Encoding teaching or provenance as claims/evidence: corrupts knowledge
  semantics.
- Unrestricted explicit overwrite: can replace newer vNext knowledge with
  legacy state.
- A second migration sidecar owner: creates another persistence contract
  outside `KnowledgeStore`.

## Verification

- Valid, partial, corrupt, repeat, and evolved-topic checks.
- Source hash and byte equality before/after import.
- Store snapshot/version checks and full related regression suite.
