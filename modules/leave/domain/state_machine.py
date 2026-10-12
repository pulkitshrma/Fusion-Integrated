"""ELM request lifecycle state machine; pure Python."""
from dataclasses import dataclass

DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_SANCTION = "awaiting_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLATION_PENDING = "cancellation_pending"
CANCELLED = "cancelled"
EXTENSION_PENDING = "extension_pending"
EXTENDED = "extended"

@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    action: str

EDGES = (
    Edge(DRAFT, AWAITING_SUBSTITUTE, "submit_with_substitute"),
    Edge(DRAFT, AWAITING_UNIT_HEAD, "submit_without_substitute"),
    Edge(AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, "substitute_accept"),
    Edge(AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, "substitute_decline"),
    Edge(APPLICANT_ACTION_REQUIRED, AWAITING_SUBSTITUTE, "nominate_replacement"),
    Edge(AWAITING_SUBSTITUTE, WITHDRAWN, "withdraw"),
    Edge(APPLICANT_ACTION_REQUIRED, WITHDRAWN, "withdraw"),
    Edge(AWAITING_UNIT_HEAD, WITHDRAWN, "withdraw"),
    Edge(AWAITING_ESTABLISHMENT, WITHDRAWN, "withdraw"),
    Edge(AWAITING_SANCTION, WITHDRAWN, "withdraw"),
    Edge(AWAITING_UNIT_HEAD, APPROVED, "unit_head_approve_cl_rh"),
    Edge(AWAITING_UNIT_HEAD, REJECTED, "unit_head_reject_cl_rh"),
    Edge(AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, "recommend"),
    Edge(AWAITING_UNIT_HEAD, AWAITING_SANCTION, "recommend_direct"),
    Edge(AWAITING_ESTABLISHMENT, AWAITING_SANCTION, "route_to_authority"),
    Edge(AWAITING_SANCTION, APPROVED, "sanction_approve"),
    Edge(AWAITING_SANCTION, REJECTED, "sanction_reject"),
    Edge(APPROVED, CANCELLATION_PENDING, "request_cancellation"),
    Edge(CANCELLATION_PENDING, CANCELLED, "cancellation_approve"),
    Edge(CANCELLATION_PENDING, APPROVED, "cancellation_reject"),
    Edge(APPROVED, EXTENSION_PENDING, "request_extension"),
    Edge(EXTENSION_PENDING, EXTENDED, "extension_approve"),
    Edge(EXTENSION_PENDING, APPROVED, "extension_reject"),
)

def transition(source, action):
    for edge in EDGES:
        if edge.source == source and edge.action == action:
            return edge.target
    raise ValueError(f"Invalid ELM transition: {source} -> {action}")
