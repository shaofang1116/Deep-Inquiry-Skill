# ADR 0003: Publication Audit Journal

## Status

Accepted on 2026-09-22.

## Context

The durable knowledge projection previously recorded accepted deltas only as
topic snapshots. That could not prove a skeptic rejection, the review chain
for a publication, or a retried candidate after a process interruption.

## Decision

- `KnowledgePublisher` owns lifecycle policy and returns one terminal
  `PublicationOutcome`.
- `KnowledgeStore` remains the only topic lock owner and durable writer.
- Each new lifecycle operation appends canonical, immutable, per-topic JSON
  records under `topics/<topic-id>/audit/`.
- Records are ordered by zero-padded sequence and use the states `proposed`,
  `reviewed`, `published`, `rejected`, and `retired`.
- A successful publication writes the next immutable topic snapshot and
  `knowledge.json` before its `published` audit record.
- Retry of the same candidate returns an existing terminal record. When a
  snapshot exists but a published record is missing, the store verifies the
  deterministic candidate snapshot and appends only that missing terminal
  record.
- Rejections do not change `knowledge.json` or the current topic version.
- Existing topics without `audit/` remain readable and receive no historical
  rewrite.

## Consequences

Each attempted lifecycle action has a durable terminal trail, while query
continues to read only published `knowledge.json`. The host remains unchanged
in this slice; Task 2 will route its durable commit boundary through
`KnowledgePublisher`.

The journal is not a second writer or a public compatibility path. It is
written only within the existing `KnowledgeStore` topic lock.
