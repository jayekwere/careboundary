from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.common import DEMO_IDENTITIES, DomainError, Identity
from app.domain import (
    Access,
    Emergency,
    EmergencyReview,
    Incident,
    Patient,
    PrivacyDecision,
    dispatch,
    view,
)

NOW = "2026-11-01T12:00:00Z"
LATER = "2026-11-01T13:00:00Z"
OP = DEMO_IDENTITIES["demo-operator"]
DR = DEMO_IDENTITIES["demo-clinician"]
REVIEW = DEMO_IDENTITIES["demo-reviewer"]


def seed() -> dict[str, Any]:
    state: dict[str, Any] = {}
    dispatch(
        state,
        OP,
        "register-patient",
        Patient(
            id="patient",
            synthetic=True,
            clinic="north",
            assigned_clinician="dr-other",
            observation="synthetic-normal",
        ),
        NOW,
    )
    return state


def test_only_synthetic_fields_and_minimal_support_metadata() -> None:
    with pytest.raises(ValidationError):
        Patient.model_validate(
            dict(
                id="patient",
                synthetic=False,
                clinic="north",
                assigned_clinician="dr-other",
                observation="real diagnosis",
            )
        )
    state = seed()
    result = dispatch(
        state,
        DEMO_IDENTITIES["demo-support"],
        "read-patient",
        Access(id="patient", purpose="support"),
        NOW,
    )
    assert "observation" not in result and result["clinical_fields"] == "redacted"
    assert view(state, DR, NOW)["patients"] == []
    with pytest.raises(DomainError):
        dispatch(state, OP, "read-patient", Access(id="patient", purpose="treatment"), NOW)
    with pytest.raises(DomainError):
        dispatch(
            state,
            DEMO_IDENTITIES["demo-support"],
            "read-patient",
            Access(id="patient", purpose="support", emergency_id="unused"),
            NOW,
        )


def test_emergency_binding_expiry_negative_review_and_same_subject() -> None:
    state = seed()
    request = Emergency(
        id="emergency",
        patient_id="patient",
        justification="A justified synthetic clinical emergency exercise.",
        minutes=5,
    )
    dispatch(state, DR, "request-emergency", request, NOW)
    access = Access(id="patient", purpose="treatment", emergency_id="emergency")
    with pytest.raises(DomainError):
        dispatch(state, DR, "read-patient", access, LATER)
    stranger = Identity(tenant="alder", subject="dr-stranger", roles=["clinician"])
    with pytest.raises(DomainError):
        dispatch(state, stranger, "read-patient", access, NOW)
    same = Identity(tenant="alder", subject=DR.subject, roles=["reviewer"])
    with pytest.raises(DomainError):
        dispatch(
            state,
            same,
            "review-emergency",
            EmergencyReview(
                id="emergency",
                accepted=True,
                rationale="Independent review is required for this grant.",
            ),
            NOW,
        )
    dispatch(
        state,
        REVIEW,
        "review-emergency",
        EmergencyReview(
            id="emergency",
            accepted=False,
            rationale="This exercise does not justify continued emergency access.",
        ),
        NOW,
    )
    with pytest.raises(DomainError):
        dispatch(state, DR, "read-patient", access, NOW)
    with pytest.raises(DomainError):
        dispatch(
            state,
            REVIEW,
            "review-emergency",
            EmergencyReview(
                id="emergency",
                accepted=True,
                rationale="Attempt to override a completed independent review.",
            ),
            NOW,
        )
    assert view(state, REVIEW, LATER)["emergencies"][0]["status"] == "expired"


def test_assigned_access_and_independent_privacy_record() -> None:
    state = seed()
    assigned = Identity(tenant="alder", subject="dr-other", roles=["clinician"])
    assert (
        dispatch(state, assigned, "read-patient", Access(id="patient", purpose="treatment"), NOW)[
            "observation"
        ]
        == "synthetic-normal"
    )
    with pytest.raises(DomainError):
        dispatch(
            state,
            assigned,
            "request-emergency",
            Emergency(
                id="e",
                patient_id="patient",
                justification="This assigned clinician already has normal access.",
                minutes=5,
            ),
            NOW,
        )
    incident = Incident(
        id="incident",
        data_category="synthetic-health",
        sensitivity="high",
        misuse_probability="unknown",
        affected_count=1,
        occurred_at=NOW,
        containment="Disabled the synthetic integration.",
    )
    with pytest.raises(DomainError):
        dispatch(
            state, OP, "record-incident", incident.model_copy(update={"occurred_at": LATER}), NOW
        )
    dispatch(state, OP, "record-incident", incident, NOW)
    decision = PrivacyDecision(
        id="incident",
        notify=False,
        rationale="A human privacy reviewer documents this synthetic assessment.",
        evidence_sha256="a" * 64,
    )
    same = Identity(tenant="alder", subject=OP.subject, roles=["privacy"])
    with pytest.raises(DomainError):
        dispatch(state, same, "privacy-decision", decision, NOW)
    dispatch(state, DEMO_IDENTITIES["demo-privacy"], "privacy-decision", decision, NOW)
    with pytest.raises(DomainError):
        dispatch(state, DEMO_IDENTITIES["demo-privacy"], "privacy-decision", decision, NOW)


def test_data_flow_inventory_is_privacy_scoped() -> None:
    from app.domain import DataFlow

    state = seed()
    flow = DataFlow(
        id="flow",
        source_system="clinic",
        destination_system="reports",
        region="unknown",
        category="synthetic-health",
        retention_days=90,
        encrypted=None,
        owner="privacy",
    )
    with pytest.raises(DomainError):
        dispatch(state, OP, "register-data-flow", flow, NOW)
    result = dispatch(state, DEMO_IDENTITIES["demo-privacy"], "register-data-flow", flow, NOW)
    assert (
        result["risk"] == "encryption-not-demonstrated"
        and result["jurisdiction_decision"] == "not_automated"
    )
    assert view(state, DEMO_IDENTITIES["demo-support"], NOW)["data_flows"] == []


def test_synthetic_marker_rejects_integer_and_string_aliases() -> None:
    for marker in [1, "true", False, None]:
        with pytest.raises(ValidationError):
            Patient.model_validate(
                {
                    "id": "patient",
                    "synthetic": marker,
                    "clinic": "north",
                    "assigned_clinician": "dr-other",
                    "observation": "synthetic-normal",
                }
            )
