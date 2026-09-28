"""End-to-end completion coverage for schema-v3 cognitive reader reports."""

from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.autonomous_runtime import HostRun, PendingCursor
from scripts.convergence import evaluate_convergence
from scripts.knowledge_schema import (
    ConvergenceAssessment,
    KnowledgeSchemaError,
    TopicKnowledge,
)
from scripts.knowledge_store import KnowledgeStoreError
from scripts.renderer import render_knowledge_report
from scripts.vnext_host import VNextHost, VNextHostError
from tests.test_cognitive_reader_document_schema import _schema_v3_topic


_AUDIT_LEAKAGE_TERMS = (
    "convergence history",
    "knowledge by dimension",
    "topic id",
    "claim-",
    "evidence-",
    "gap-",
    "skeptic review",
    "audit record",
    "pending cursor",
    "completion cursor",
    "host run",
)


def _replace_references(value: object, replacements: dict[str, str]) -> object:
    if isinstance(value, dict):
        return {
            key: _replace_references(item, replacements)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_replace_references(item, replacements) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    return value


def _ready_schema_v3_topic() -> TopicKnowledge:
    source = _schema_v3_topic()
    source["topic_id"] = "cognitive-reader-report-e2e"
    source["title"] = "Cognitive reader report completion"
    source["coverage_dimensions"] = ["scope", "risk"]
    source["counterexamples"] = []
    claim_ids = [
        f"{dimension}-{kind}"
        for dimension in ("scope", "risk")
        for kind in ("mechanism", "condition", "boundary", "synthesis")
    ]
    source["claims"] = [
        {
            "id": f"{dimension}-{kind}",
            "dimension": dimension,
            "kind": kind,
            "statement": f"{dimension.title()} {kind} is established.",
            "confidence": "medium" if kind == "synthesis" else "low",
            "evidence_ids": (
                ["evidence-1"]
                if (dimension, kind) == ("scope", "mechanism")
                else (
                    [f"evidence-{dimension}-synthesis"]
                    if kind == "synthesis"
                    else []
                )
            ),
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        }
        for dimension in ("scope", "risk")
        for kind in ("mechanism", "condition", "boundary", "synthesis")
    ]
    source["evidence"] = [
        {
            "id": "evidence-1",
            "source": "A reviewed source.",
            "supports_claim_ids": ["scope-mechanism"],
        },
        *[
            {
                "id": f"evidence-{dimension}-synthesis",
                "source": f"Reviewed synthesis evidence for {dimension}.",
                "supports_claim_ids": [f"{dimension}-synthesis"],
            }
            for dimension in ("scope", "risk")
        ],
    ]
    source["gaps"][0]["priority"] = "low"
    source["gaps"][0]["expected_gain"] = "low"
    source["convergence_history"] = [
        {
            "cycle": cycle,
            "phase": "post_baseline",
            "delta": {},
            "gain_level": "low",
            "skeptic_structural_hit": False,
        }
        for cycle in (1, 2)
    ]
    source["reader_document"] = _replace_references(
        source["reader_document"],
        {
            "claim-1": "scope-mechanism",
            "claim-2": "risk-condition",
        },
    )
    document = source["reader_document"]
    assert isinstance(document, dict)
    synthesis = document["synthesis"]
    assert isinstance(synthesis, dict)
    synthesis["claim_ids"] = claim_ids
    further_learning = document["further_learning"]
    assert isinstance(further_learning, list)
    for item in further_learning:
        assert isinstance(item, dict)
        item["evidence_ids"] = []
    return TopicKnowledge.from_dict(source)


def _cross_topic_fixture(
    *,
    topic_id: str,
    title: str,
    proposition: str,
    central_question: str,
    scope: str,
    conclusion: str,
    orientation: str,
    concepts: list[tuple[str, str, str, str]],
    relationships: list[tuple[str, str, str, str, str]],
    variable: tuple[str, list[str], str, str, str],
    sections: list[tuple[str, str, str, str, list[str]]],
    synthesis: str,
    transfer_prompt: str,
    reusable_model: str,
    reevaluate: list[str],
    boundary_type: str,
    boundary: str,
    sources: list[str],
) -> TopicKnowledge:
    """Build a complete schema-v3/topic reader-document-v2 test fixture."""

    dimensions = [concept_id for concept_id, _, _, _ in concepts]
    claim_ids = [f"claim-{index}" for index in range(1, len(concepts) + 1)]
    evidence_ids = [f"evidence-{index}" for index in range(1, len(concepts) + 1)]
    claims = [
        {
            "id": claim_id,
            "dimension": dimension,
            "kind": "mechanism",
            "statement": statement,
            "confidence": "high",
            "evidence_ids": [evidence_id],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        }
        for (dimension, _, _, statement), claim_id, evidence_id in zip(
            concepts,
            claim_ids,
            evidence_ids,
        )
    ]
    evidence = [
        {
            "id": evidence_id,
            "source": source,
            "supports_claim_ids": [claim_id],
        }
        for claim_id, evidence_id, source in zip(claim_ids, evidence_ids, sources)
    ]
    concept_claim_ids = dict(zip(dimensions, claim_ids))
    concept_evidence_ids = dict(zip(dimensions, evidence_ids))
    document: dict[str, object] = {
        "schema_version": 2,
        "orientation": {
            "central_question": central_question,
            "scope": scope,
            "current_conclusion": {
                "text": conclusion,
                "claim_ids": [claim_ids[0]],
                "evidence_ids": [evidence_ids[0]],
            },
            "paragraphs": [orientation],
            "claim_ids": [claim_ids[0]],
            "evidence_ids": [evidence_ids[0]],
        },
        "domain_map": {
            "concepts": [
                {
                    "id": concept_id,
                    "label": label,
                    "definition": definition,
                    "claim_ids": [concept_claim_ids[concept_id]],
                    "evidence_ids": [concept_evidence_ids[concept_id]],
                }
                for concept_id, label, definition, _ in concepts
            ],
            "relationships": [
                {
                    "id": relation_id,
                    "type": relation_type,
                    "from_concept_id": from_concept_id,
                    "to_concept_id": to_concept_id,
                    "condition": condition,
                    "claim_ids": [concept_claim_ids[to_concept_id]],
                    "evidence_ids": [concept_evidence_ids[to_concept_id]],
                }
                for (
                    relation_id,
                    relation_type,
                    from_concept_id,
                    to_concept_id,
                    condition,
                ) in relationships
            ],
            "keystone_concept_ids": dimensions,
            "prerequisite_edges": [
                {
                    "before_concept_id": dimensions[index],
                    "after_concept_id": dimensions[index + 1],
                }
                for index in range(len(dimensions) - 1)
            ],
            "key_variables": [
                {
                    "name": variable[0],
                    "concept_refs": variable[1],
                    "change_direction": variable[2],
                    "effect": variable[3],
                    "claim_ids": [concept_claim_ids[variable[4]]],
                    "evidence_ids": [concept_evidence_ids[variable[4]]],
                    "project_input_required": True,
                }
            ],
        },
        "sections": [
            {
                "id": concept_id,
                "heading": heading,
                "cognitive_question": question,
                "concept_refs": [concept_id],
                "paragraphs": [paragraph],
                "mechanism_chain": mechanism_chain,
                "dimension_refs": [concept_id],
                "claim_ids": [concept_claim_ids[concept_id]],
                "evidence_ids": [concept_evidence_ids[concept_id]],
            }
            for concept_id, heading, question, paragraph, mechanism_chain in sections
        ],
        "synthesis": {
            "paragraphs": [synthesis],
            "claim_ids": claim_ids,
            "evidence_ids": evidence_ids,
        },
        "transfer_guidance": [
            {
                "prompt": transfer_prompt,
                "reusable_model": reusable_model,
                "reevaluate": reevaluate,
                "concept_refs": dimensions,
                "claim_ids": claim_ids,
                "evidence_ids": evidence_ids,
            }
        ],
        "boundary_notes": [
            {
                "type": boundary_type,
                "text": boundary,
                "claim_ids": [claim_ids[-1]],
                "evidence_ids": [evidence_ids[-1]],
                "gap_ids": [],
            }
        ],
        "further_learning": [],
    }
    return TopicKnowledge.from_dict(
        {
            "schema_version": 3,
            "topic_id": topic_id,
            "title": title,
            "proposition": proposition,
            "version": 1,
            "coverage_dimensions": dimensions,
            "claims": claims,
            "evidence": evidence,
            "gaps": [],
            "counterexamples": [],
            "convergence_history": [],
            "created_at": "2026-09-24T00:00:00+00:00",
            "updated_at": "2026-09-24T00:00:00+00:00",
            "migration_metadata": {},
            "reader_document": document,
        }
    )


def _engineering_feasibility_fixture() -> TopicKnowledge:
    return _cross_topic_fixture(
        topic_id="battery-inspection-drone-feasibility",
        title="Battery Inspection Drone Feasibility",
        proposition="Payload, wind, and reserve energy jointly determine whether a mission is feasible.",
        central_question="Can a battery inspection drone complete a bridge survey safely?",
        scope="Short-range visual inspections with a fixed battery and a mandatory return reserve.",
        conclusion="The mission is feasible only when payload and wind leave enough energy for the survey and return reserve.",
        orientation="Treat feasibility as an energy budget under field conditions, not as a nominal flight-time claim.",
        concepts=[
            (
                "payload",
                "Payload mass",
                "The camera and mounting mass carried by the aircraft.",
                "Added payload raises propulsion energy demand.",
            ),
            (
                "wind",
                "Headwind",
                "The opposing air flow that increases power needed for ground progress.",
                "Headwind lengthens the high-power portion of the route.",
            ),
            (
                "reserve",
                "Return reserve",
                "Energy retained to fly back and land without exhausting the battery.",
                "A protected reserve limits the usable survey energy.",
            ),
        ],
        relationships=[
            (
                "payload-constrains-reserve",
                "constrains",
                "payload",
                "reserve",
                "When added mass raises the energy needed for the planned flight.",
            ),
            (
                "wind-constrains-reserve",
                "constrains",
                "wind",
                "reserve",
                "When wind persists on the outbound or return leg.",
            ),
        ],
        variable=(
            "Headwind strength",
            ["wind", "reserve"],
            "higher",
            "A stronger headwind consumes the return reserve sooner and can turn a nominally feasible route into an infeasible one.",
            "reserve",
        ),
        sections=[
            (
                "payload",
                "Account for payload mass",
                "Why does payload change the feasible route?",
                "Payload mass raises the thrust required to hold the planned speed and altitude.",
                [
                    "Camera and mount mass",
                    "higher propulsion demand",
                    "less usable battery energy",
                    "shorter survey route",
                ],
            ),
            (
                "wind",
                "Model the wind leg",
                "How does headwind alter the energy budget?",
                "Headwind slows ground progress, so the aircraft spends longer at the power setting needed to stay on route.",
                [
                    "Headwind on the route",
                    "longer high-power flight",
                    "greater energy consumption",
                    "reduced route margin",
                ],
            ),
            (
                "reserve",
                "Protect the return reserve",
                "What makes a route safe rather than merely possible?",
                "The return reserve must remain after the survey segment, so it is a constraint rather than spare capacity.",
                [
                    "Survey energy use",
                    "remaining battery check",
                    "protected return reserve",
                    "launch or abort decision",
                ],
            ),
        ],
        synthesis="Payload and wind compound: heavier equipment reduces margin before headwind extends the high-power leg, so feasibility must be judged from the combined budget.",
        transfer_prompt="For a new inspection route, which payload, wind forecast, and return reserve would make you shorten the survey or decline launch?",
        reusable_model="Compute usable mission energy after reserving return energy, then test whether route conditions consume that budget.",
        reevaluate=["Payload mass", "Wind on each route leg", "Required return reserve"],
        boundary_type="project_input",
        boundary="The actual route distance, launch location, and wind forecast must be measured for the specific survey.",
        sources=[
            "Aircraft energy-budget test note.",
            "Wind-affected route timing observation.",
            "Return-reserve operating procedure.",
        ],
    )


def _comparison_tradeoff_fixture() -> TopicKnowledge:
    return _cross_topic_fixture(
        topic_id="image-compression-tradeoff",
        title="Image Compression Trade-off",
        proposition="Compression choice trades transfer speed against image fidelity under the needs of the downstream decision.",
        central_question="When should an inspection workflow choose lossy rather than lossless image compression?",
        scope="Transferring inspection images when bandwidth is limited and reviewers may need to identify fine defects.",
        conclusion="Choose lossy compression for rapid triage only while the retained detail remains sufficient for the decision; reverse to lossless when fine defects must be inspected.",
        orientation="The recommendation depends on decision tolerance for lost detail, not on file size alone.",
        concepts=[
            (
                "bandwidth",
                "Bandwidth",
                "The rate available to transfer image data.",
                "Lower bandwidth makes large image transfers slower.",
            ),
            (
                "compression",
                "Compression level",
                "The degree to which encoding reduces image size and can remove detail.",
                "Higher lossy compression reduces transfer size while discarding detail.",
            ),
            (
                "defect-detail",
                "Defect detail",
                "The visual detail needed to recognize a material defect.",
                "Fine defects can become indistinguishable when compression removes relevant detail.",
            ),
        ],
        relationships=[
            (
                "bandwidth-depends-on-compression",
                "depends_on",
                "bandwidth",
                "compression",
                "When transfer time is constrained by a limited link.",
            ),
            (
                "compression-trades-off-detail",
                "trades_off_with",
                "compression",
                "defect-detail",
                "When lossy encoding removes information needed for close inspection.",
            ),
        ],
        variable=(
            "Required defect detail",
            ["compression", "defect-detail"],
            "higher",
            "As the decision requires finer defect detail, the recommendation reverses from lossy triage to lossless transfer despite the bandwidth cost.",
            "defect-detail",
        ),
        sections=[
            (
                "bandwidth",
                "Start with the transfer constraint",
                "What does limited bandwidth make costly?",
                "Limited bandwidth makes raw or lossless images slower to deliver, which can delay a broad first-pass review.",
                [
                    "Limited bandwidth",
                    "longer image transfer",
                    "slower reviewer access",
                    "triage delay",
                ],
            ),
            (
                "compression",
                "Choose the compression trade-off",
                "What does lossy compression buy and cost?",
                "Lossy compression reduces file size and speeds transfer, but it does so by removing some visual information.",
                [
                    "Lossy encoding choice",
                    "smaller file size",
                    "faster transfer",
                    "reduced visual fidelity",
                ],
            ),
            (
                "defect-detail",
                "Apply the reversal condition",
                "When must speed give way to fidelity?",
                "If a reviewer must inspect fine cracks or corrosion edges, choose lossless transfer even when it delays delivery.",
                [
                    "Fine-defect inspection required",
                    "detail loss becomes material",
                    "lossy image is insufficient",
                    "lossless recommendation",
                ],
            ),
        ],
        synthesis="Bandwidth pressure favors lossy transfer for broad triage, but the same choice becomes wrong when the next decision depends on details that compression can erase.",
        transfer_prompt="For a new image stream, what decision will the reviewer make, and what smallest visible defect must remain distinguishable before you allow lossy compression?",
        reusable_model="Match an information-reduction choice to the detail threshold of the downstream decision.",
        reevaluate=["Available bandwidth", "Required defect detail", "Whether the next step is triage or final inspection"],
        boundary_type="professional_judgment",
        boundary="The point at which detail is sufficient for a specific defect decision requires reviewer judgment and may differ by material and lighting.",
        sources=[
            "Limited-link image transfer measurement.",
            "Lossy encoding fidelity comparison.",
            "Fine-defect inspection example.",
        ],
    )


def _conceptual_dispute_fixture() -> TopicKnowledge:
    return _cross_topic_fixture(
        topic_id="model-explanation-dispute",
        title="What Counts as a Model Explanation?",
        proposition="Predictive usefulness, feature attribution, and causal explanation answer different questions about a model.",
        central_question="Does a feature-attribution chart explain why a model made a prediction?",
        scope="Interpreting model outputs when correlations may not represent causal mechanisms.",
        conclusion="A feature-attribution chart can describe model sensitivity, but it does not by itself establish a causal explanation.",
        orientation="Separate what the model responds to from what caused the real-world outcome.",
        concepts=[
            (
                "prediction",
                "Predictive pattern",
                "A correlation the model uses to estimate an outcome.",
                "A model can predict well by exploiting correlations in its training distribution.",
            ),
            (
                "attribution",
                "Feature attribution",
                "A summary of how changing an input changes the model output under a chosen method.",
                "Attribution identifies model sensitivity rather than a verified real-world cause.",
            ),
            (
                "causation",
                "Causal explanation",
                "An account of how an intervention would change the outcome through a real mechanism.",
                "Causal explanation requires assumptions or evidence beyond predictive sensitivity.",
            ),
        ],
        relationships=[
            (
                "prediction-depends-on-attribution",
                "depends_on",
                "prediction",
                "attribution",
                "When the chart is used to summarize the fitted model.",
            ),
            (
                "attribution-exception-to-causation",
                "exception_to",
                "attribution",
                "causation",
                "When correlated inputs can change the prediction without causing the outcome.",
            ),
        ],
        variable=(
            "Distribution shift",
            ["prediction", "attribution", "causation"],
            "greater",
            "A larger shift can make a learned correlation and its attribution less reliable while leaving the causal question unresolved.",
            "prediction",
        ),
        sections=[
            (
                "prediction",
                "Identify the predictive pattern",
                "What is the model actually using?",
                "A predictive model may rely on a stable correlation because it improves estimates within the observed data.",
                [
                    "Observed correlation",
                    "fitted predictive weight",
                    "changed model score",
                    "useful prediction",
                ],
            ),
            (
                "attribution",
                "Read attribution as sensitivity",
                "What does an attribution chart establish?",
                "An attribution chart reports how the fitted model output responds to an input under its calculation method.",
                [
                    "Selected input feature",
                    "attribution calculation",
                    "changed model output",
                    "sensitivity description",
                ],
            ),
            (
                "causation",
                "Do not equate sensitivity with cause",
                "Why is causal explanation a stronger claim?",
                "A feature can change a prediction because it is correlated with the outcome even when changing that feature would not change the outcome.",
                [
                    "Correlated feature",
                    "model sensitivity",
                    "missing intervention evidence",
                    "causal claim withheld",
                ],
            ),
        ],
        synthesis="Prediction and attribution can support useful model interpretation together, yet neither substitutes for causal evidence when the question is what would change the real-world outcome.",
        transfer_prompt="When reading a new attribution chart, which claim is about model sensitivity, and what intervention evidence would you need before making a causal claim?",
        reusable_model="Separate predictive correlation, model sensitivity, and intervention-based causation before deciding what an explanation supports.",
        reevaluate=["Distribution shift", "Attribution method assumptions", "Available intervention evidence"],
        boundary_type="frontier_dispute",
        boundary="Researchers disagree about which explanatory standards are appropriate for different model uses; attribution alone does not settle that dispute.",
        sources=[
            "Predictive-model correlation example.",
            "Feature-attribution method note.",
            "Causal-inference interpretation note.",
        ],
    )


def _cross_topic_fixtures() -> tuple[TopicKnowledge, ...]:
    return (
        _engineering_feasibility_fixture(),
        _comparison_tradeoff_fixture(),
        _conceptual_dispute_fixture(),
    )


def write_blind_reader_reports(
    output_dir: Path | None = None,
) -> tuple[Path, ...]:
    """Create a fresh Markdown-only handoff for blind-reader acceptance."""

    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="cognitive-reader-report-blind-"))
    elif output_dir.exists():
        raise ValueError("blind-reader handoff directory must be fresh")
    else:
        output_dir.mkdir(parents=True)
    if tuple(output_dir.iterdir()):
        raise AssertionError("blind-reader handoff directory must start empty")

    paths: list[Path] = []
    for topic in _cross_topic_fixtures():
        path = output_dir / f"{topic.topic_id}.md"
        path.write_bytes(render_knowledge_report(topic))
        paths.append(path.resolve())
    return tuple(paths)


def _converged_assessment() -> ConvergenceAssessment:
    return ConvergenceAssessment.from_dict(
        {
            "gain_level": "low",
            "open_high_value_gap_ids": [],
            "evidence_deficit_claim_ids": [],
            "structural_hit": False,
            "continue_learning": False,
            "reason": (
                "The complete low-gain record leaves no higher-value "
                "investigation to pursue."
            ),
        }
    )


class CognitiveReaderReportE2ETests(unittest.TestCase):
    def _host_and_cursor(
        self,
        *,
        convergence: dict[str, object] | None = None,
    ) -> tuple[VNextHost, HostRun, PendingCursor]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        host = VNextHost(
            state_path=str(root / "state.json"),
            knowledge_root=str(root / "knowledge"),
        )
        topic = host.knowledge.create(_ready_schema_v3_topic())
        topic = host.knowledge.save(topic, base_version=topic.version)
        topic = host.knowledge.save(topic, base_version=topic.version)
        run = HostRun.new(
            topic_id=topic.topic_id,
            knowledge_root=str(host.knowledge.root.resolve()),
            base_version=topic.version,
        )
        host._save_run(run)
        decision = (
            convergence
            if convergence is not None
            else evaluate_convergence(topic, _converged_assessment()).__dict__
        )
        cursor = PendingCursor(
            schema_version=1,
            runtime_kind="vnext_host_pending",
            run_id=run.run_id,
            topic_id=topic.topic_id,
            knowledge_root=run.knowledge_root,
            stage="checkpoint_or_complete",
            expected_version=topic.version,
            commit_marker=None,
            payload={"cycle": 3, "convergence": decision},
        )
        return host, run, cursor

    def test_ready_schema_v3_converges_and_writes_an_immutable_report(self) -> None:
        host, run, cursor = self._host_and_cursor()

        outcome = host._advance_internal(cursor, run, discard_judgment=False)
        report_path = Path(outcome.result["report_path"])

        self.assertEqual(outcome.status, "done")
        self.assertTrue(report_path.is_absolute())
        self.assertEqual(
            report_path.read_bytes(),
            render_knowledge_report(host.knowledge.load(cursor.topic_id)),
        )
        self.assertEqual(host._load_run().status, "complete")

    def test_unready_schema_v3_is_blocked_by_the_reader_document_predicate(self) -> None:
        topic = _ready_schema_v3_topic()
        topic.reader_document = copy.deepcopy(topic.reader_document)
        assert topic.reader_document is not None
        orientation = topic.reader_document["orientation"]
        assert isinstance(orientation, dict)
        del orientation["central_question"]

        decision = evaluate_convergence(topic, _converged_assessment())

        self.assertFalse(decision.converged)
        self.assertEqual(decision.reason_code, "reader_document_not_ready")

    def test_unready_reader_document_does_not_mask_canonical_schema_corruption(
        self,
    ) -> None:
        topic = _ready_schema_v3_topic()
        topic.claims.append(copy.deepcopy(topic.claims[0]))
        topic.reader_document = copy.deepcopy(topic.reader_document)
        assert topic.reader_document is not None
        orientation = topic.reader_document["orientation"]
        assert isinstance(orientation, dict)
        del orientation["central_question"]

        with self.assertRaisesRegex(
            KnowledgeSchemaError,
            "claims contains duplicate IDs",
        ):
            evaluate_convergence(topic, _converged_assessment())

    def test_checkpoint_completion_has_no_report_path(self) -> None:
        host, run, cursor = self._host_and_cursor(
            convergence={
                "converged": False,
                "reason_code": "safety_checkpoint",
                "reason": "The run reached its safety checkpoint.",
                "checkpoint_required": True,
                "blocking_ids": [],
            }
        )

        outcome = host._advance_internal(cursor, run, discard_judgment=False)

        self.assertEqual(outcome.status, "done")
        self.assertNotIn("report_path", outcome.result)
        self.assertFalse(
            (host.knowledge.root / "topics" / cursor.topic_id / "reports").exists()
        )

    def test_stale_completion_cursor_is_refused_without_completing_the_run(self) -> None:
        host, run, cursor = self._host_and_cursor()
        topic = host.knowledge.load(cursor.topic_id)
        host.knowledge.save(topic, base_version=topic.version)

        with self.assertRaisesRegex(VNextHostError, "expected_version"):
            host._advance_internal(cursor, run, discard_judgment=False)

        self.assertEqual(host._load_run().status, "active")
        self.assertEqual(host._load_cursor().to_dict(), cursor.to_dict())

    def test_report_write_retry_reuses_the_cursor_and_immutable_bytes(self) -> None:
        host, run, cursor = self._host_and_cursor()
        original_writer = host.knowledge.write_markdown_report
        attempted_bytes: list[bytes] = []
        version_before = host.knowledge.load(cursor.topic_id).version

        def fail_once(topic: TopicKnowledge, payload: bytes) -> Path:
            attempted_bytes.append(payload)
            if len(attempted_bytes) == 1:
                raise KnowledgeStoreError("disk unavailable")
            return original_writer(topic, payload)

        with patch.object(
            host.knowledge,
            "write_markdown_report",
            side_effect=fail_once,
        ):
            with self.assertRaisesRegex(VNextHostError, "cannot write"):
                host._advance_internal(cursor, run, discard_judgment=False)

            self.assertEqual(host._load_run().status, "active")
            self.assertEqual(host._load_cursor().to_dict(), cursor.to_dict())
            self.assertEqual(
                host.knowledge.load(cursor.topic_id).version,
                version_before,
            )

            outcome = host._resume(host._load_run())

        report_path = Path(outcome.result["report_path"])
        self.assertEqual(outcome.status, "done")
        self.assertEqual(len(attempted_bytes), 2)
        self.assertEqual(attempted_bytes[0], attempted_bytes[1])
        self.assertEqual(report_path.read_bytes(), attempted_bytes[1])
        self.assertEqual(
            host.knowledge.load(cursor.topic_id).version,
            version_before,
        )
        self.assertEqual(host._load_run().status, "complete")

    def test_cross_topic_schema_v3_documents_render_without_audit_leakage(
        self,
    ) -> None:
        expected_boundaries = {
            "battery-inspection-drone-feasibility": "project input",
            "image-compression-tradeoff": "professional judgment",
            "model-explanation-dispute": "frontier dispute",
        }
        for topic in _cross_topic_fixtures():
            with self.subTest(topic=topic.topic_id):
                document = topic.reader_document
                self.assertEqual(topic.schema_version, 3)
                self.assertIsInstance(document, dict)
                assert isinstance(document, dict)
                self.assertEqual(document["schema_version"], 2)

                first = render_knowledge_report(topic)
                report = first.decode("utf-8")
                self.assertEqual(first, render_knowledge_report(topic))
                for heading in (
                    "## Orientation",
                    "## Domain Map",
                    "### Key Variables",
                    "## Synthesis",
                    "## Transfer the Model",
                    "## Further Learning",
                    "## Sources",
                ):
                    self.assertIn(heading, report)
                self.assertIn("**Central question:**", report)
                self.assertIn("**Scope:**", report)
                self.assertIn(" -> ", report)
                self.assertIn("**Try it:**", report)
                self.assertIn(
                    f"**Boundary ({expected_boundaries[topic.topic_id]}):**",
                    report,
                )
                domain_map = document["domain_map"]
                self.assertIsInstance(domain_map, dict)
                assert isinstance(domain_map, dict)
                keystone_ids = domain_map["keystone_concept_ids"]
                self.assertIsInstance(keystone_ids, list)
                for concept_id in keystone_ids:
                    self.assertIsInstance(concept_id, str)
                    heading = next(
                        section["heading"]
                        for section in document["sections"]
                        if section["id"] == concept_id
                    )
                    self.assertIn(
                        f"## {heading}",
                        report,
                    )
                for term in _AUDIT_LEAKAGE_TERMS:
                    self.assertNotIn(term, report.casefold())
                self.assertNotRegex(report, r"(?i)\bcycle\s+\d+\b")

    def test_cross_topic_rendered_reports_preserve_explicit_semantics(
        self,
    ) -> None:
        expected_semantics = {
            "battery-inspection-drone-feasibility": (
                "Payload mass raises the thrust required",
                "Headwind slows ground progress",
                "The return reserve must remain after the survey segment",
                "**Headwind strength (higher):**",
                "A stronger headwind consumes the return reserve sooner and can turn a nominally feasible route into an infeasible one.",
                "The actual route distance, launch location, and wind forecast must be measured for the specific survey.",
                "For a new inspection route, which payload, wind forecast, and return reserve would make you shorten the survey or decline launch?",
            ),
            "image-compression-tradeoff": (
                "inspect fine cracks or corrosion edges",
                "choose lossless transfer",
                "recommendation reverses from lossy triage to lossless transfer",
                "As the decision requires finer defect detail, the recommendation reverses from lossy triage to lossless transfer despite the bandwidth cost.",
                "The point at which detail is sufficient for a specific defect decision requires reviewer judgment and may differ by material and lighting.",
                "For a new image stream, what decision will the reviewer make, and what smallest visible defect must remain distinguishable before you allow lossy compression?",
            ),
            "model-explanation-dispute": (
                "does not by itself establish a causal explanation",
                "An attribution chart reports how the fitted model output responds",
                "**Boundary (frontier dispute):**",
                "A larger shift can make a learned correlation and its attribution less reliable while leaving the causal question unresolved.",
                "Researchers disagree about which explanatory standards are appropriate for different model uses; attribution alone does not settle that dispute.",
                "When reading a new attribution chart, which claim is about model sensitivity, and what intervention evidence would you need before making a causal claim?",
            ),
        }

        for topic in _cross_topic_fixtures():
            with self.subTest(topic=topic.topic_id):
                report = render_knowledge_report(topic).decode("utf-8")
                for semantic_text in expected_semantics[topic.topic_id]:
                    self.assertIn(semantic_text, report)

    def test_blind_reader_handoff_rejects_a_nonfresh_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_root:
            handoff_dir = Path(temporary_root) / "handoff"
            handoff_dir.mkdir()
            (handoff_dir / "prior.md").write_text("not a fresh handoff")

            with self.assertRaisesRegex(ValueError, "must be fresh"):
                write_blind_reader_reports(handoff_dir)

    def test_blind_reader_handoff_contains_only_current_rendered_markdown(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_root:
            handoff_dir = Path(temporary_root) / "handoff"
            self.assertFalse(handoff_dir.exists())

            paths = write_blind_reader_reports(handoff_dir)
            listing = tuple(sorted(path.name for path in handoff_dir.iterdir()))
            rendered_by_name = {
                f"{topic.topic_id}.md": render_knowledge_report(topic)
                for topic in _cross_topic_fixtures()
            }
            expected_listing = tuple(sorted(rendered_by_name))
            manifest = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths
            }
            expected_manifest = {
                name: hashlib.sha256(payload).hexdigest()
                for name, payload in rendered_by_name.items()
            }

            self.assertEqual(listing, expected_listing)
            self.assertEqual(
                tuple(sorted(path.name for path in paths)),
                expected_listing,
            )
            self.assertEqual(manifest, expected_manifest)
            for path in paths:
                self.assertEqual(path.read_bytes(), rendered_by_name[path.name])

    def test_conceptual_dispute_fixture_does_not_invent_project_management(
        self,
    ) -> None:
        report = render_knowledge_report(_conceptual_dispute_fixture()).decode(
            "utf-8"
        )

        self.assertIn("Feature attribution", report)
        self.assertIn("causal explanation", report.casefold())
        self.assertNotRegex(
            report,
            r"(?i)\b(project|manager|schedule|milestone|roadmap|backlog)\b",
        )


if __name__ == "__main__":
    unittest.main()
