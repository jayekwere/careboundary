from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from pydantic import Field

from app.common import (
    Contract,
    DomainError,
    Identity,
    Ref,
    get,
    independent,
    put,
    require,
    stamp,
)


class Patient(Ref):
    synthetic: Literal[True]
    clinic: Literal["north", "south"]
    assigned_clinician: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    observation: Literal["synthetic-normal", "synthetic-follow-up"]


class Access(Ref):
    purpose: Literal["treatment", "support"]
    emergency_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9-]{0,63}$")


class Emergency(Ref):
    patient_id: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    justification: str = Field(min_length=30, max_length=300)
    minutes: int = Field(ge=1, le=30)


class EmergencyReview(Ref):
    accepted: bool
    rationale: str = Field(min_length=20, max_length=300)


class Incident(Ref):
    data_category: Literal["synthetic-health", "synthetic-contact"]
    sensitivity: Literal["high", "low"]
    misuse_probability: Literal["likely", "unlikely", "unknown"]
    affected_count: int = Field(ge=1, le=1_000_000)
    occurred_at: str = Field(min_length=20, max_length=40)
    containment: str = Field(min_length=10, max_length=300)


class PrivacyDecision(Ref):
    notify: bool
    rationale: str = Field(min_length=30, max_length=500)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class DataFlow(Ref):
    source_system: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    destination_system: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    region: Literal["CA", "US", "EU", "unknown"]
    category: Literal["synthetic-health", "synthetic-contact"]
    retention_days: int = Field(ge=1, le=2555)
    encrypted: bool | None
    owner: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")


MODELS: dict[str, type[Contract]] = {
    "register-patient": Patient,
    "read-patient": Access,
    "request-emergency": Emergency,
    "review-emergency": EmergencyReview,
    "record-incident": Incident,
    "privacy-decision": PrivacyDecision,
}

MODELS["register-data-flow"] = DataFlow


def dispatch(
    state: dict[str, Any], actor: Identity, action: str, value: Contract, now: str
) -> dict[str, Any]:
    data = value.model_dump()
    if action == "register-data-flow":
        require(actor, "privacy")
        return put(
            state,
            "flow",
            data["id"],
            {
                **data,
                "review": "human_privacy_review_required",
                "recorded_at": now,
                "risk": "encryption-not-demonstrated"
                if data["encrypted"] is not True
                else "region-and-retention-review-required",
                "jurisdiction_decision": "not_automated",
            },
            create=True,
        )
    if action == "register-patient":
        require(actor, "operator")
        return put(state, "patient", data["id"], {**data, "created_at": now}, create=True)
    if action == "request-emergency":
        require(actor, "clinician")
        patient = get(state, "patient", data["patient_id"])
        if patient["assigned_clinician"] == actor.subject:
            raise DomainError("Assigned clinician does not require emergency access")
        return put(
            state,
            "emergency",
            data["id"],
            {
                **data,
                "requested_by": actor.subject,
                "created_at": now,
                "expires_at": (stamp(now) + timedelta(minutes=data["minutes"])).isoformat(),
                "review": None,
                "uses": 0,
            },
            create=True,
        )
    if action == "review-emergency":
        emergency = get(state, "emergency", data["id"])
        independent(actor, emergency["requested_by"])
        if emergency["review"] is not None:
            raise DomainError("Emergency review already completed")
        emergency["review"] = {**data, "reviewer": actor.subject, "at": now}
        return put(state, "emergency", data["id"], emergency)
    if action == "read-patient":
        patient = get(state, "patient", data["id"])
        if data["purpose"] == "support":
            require(actor, "support")
            if data["emergency_id"] is not None:
                raise DomainError("Support cannot use emergency access", 403)
            return {
                "id": patient["id"],
                "clinic": patient["clinic"],
                "synthetic": True,
                "clinical_fields": "redacted",
            }
        require(actor, "clinician")
        authorized = patient["assigned_clinician"] == actor.subject
        if data["emergency_id"] is not None:
            emergency = get(state, "emergency", data["emergency_id"])
            if (
                emergency["requested_by"] != actor.subject
                or emergency["patient_id"] != patient["id"]
                or stamp(emergency["expires_at"]) <= stamp(now)
                or (emergency["review"] and not emergency["review"]["accepted"])
            ):
                raise DomainError("Emergency authorization invalid", 403)
            emergency["uses"] += 1
            put(state, "emergency", data["emergency_id"], emergency)
            authorized = True
        if not authorized:
            raise DomainError("Patient is outside assigned care relationship", 403)
        return {**patient, "purpose": "treatment"}
    if action == "record-incident":
        require(actor, "operator")
        if stamp(data["occurred_at"]) > stamp(now):
            raise DomainError("Incident cannot occur in the future", 422)
        return put(
            state,
            "incident",
            data["id"],
            {
                **data,
                "recorded_by": actor.subject,
                "decision": None,
                "suggestion": "human-assessment-required",
                "retain_until": (stamp(now) + timedelta(days=730)).isoformat(),
                "retention_basis": "demo-policy-730-days-not-jurisdiction-determination",
            },
            create=True,
        )
    require(actor, "privacy")
    incident = get(state, "incident", data["id"])
    if actor.subject == incident["recorded_by"]:
        raise DomainError("An independent privacy decision is required", 403)
    if incident["decision"] is not None:
        raise DomainError("Privacy decision already recorded")
    incident["decision"] = {
        **data,
        "reviewer": actor.subject,
        "at": now,
        "scope": "human_recorded_decision_not_legal_advice",
    }
    return put(state, "incident", data["id"], incident)


def view(state: dict[str, Any], actor: Identity, now: str) -> dict[str, Any]:
    if not set(actor.roles) & {
        "operator",
        "reviewer",
        "clinician",
        "support",
        "privacy",
        "auditor",
    }:
        raise DomainError("Role not authorized", 403)
    patients = [
        {"id": p["id"], "clinic": p["clinic"], "synthetic": True}
        for p in state.get("patient", {}).values()
        if "clinician" not in actor.roles or p["assigned_clinician"] == actor.subject
    ]
    emergencies = [
        {
            "id": e["id"],
            "patient_id": e["patient_id"],
            "uses": e["uses"],
            "status": "expired"
            if stamp(e["expires_at"]) <= stamp(now)
            else "reviewed"
            if e["review"]
            else "review-required",
        }
        for e in state.get("emergency", {}).values()
        if set(actor.roles) & {"reviewer", "privacy"} or e["requested_by"] == actor.subject
    ]
    incidents = (
        list(state.get("incident", {}).values())
        if set(actor.roles) & {"privacy", "reviewer"}
        else []
    )
    return {
        "patients": patients,
        "data_flows": list(state.get("flow", {}).values())
        if set(actor.roles) & {"privacy", "reviewer"}
        else [],
        "emergencies": emergencies,
        "incidents": incidents,
        "data_policy": "synthetic-only",
        "bulk_export": "unsupported",
    }
