"""Fail-closed workflow routing from the administrator-maintained route table."""
from types import SimpleNamespace

from modules.directory.contracts import get_users
from modules.leave.models import LeaveWorkflowStep


class WorkflowConfigurationError(ValueError):
    pass


def applicant_context(application):
    person = get_users([application.user_id]).get(application.user_id)
    if person is None:
        raise WorkflowConfigurationError("Applicant is not present in the institute directory.")
    return person


def route_steps(application):
    if application.workflow_snapshot:
        return [SimpleNamespace(**row) for row in application.workflow_snapshot]
    person = applicant_context(application)
    unit = person.department or ""
    role = application.applicant_role or ""
    rows = LeaveWorkflowStep.objects.filter(
        category=application.category, is_active=True
    ).filter(organizational_unit__in=[unit, ""]).filter(
        designation__in=[role, ""]
    ).order_by("sequence")
    # Prefer unit-specific rows over generic rows at the same sequence.
    steps = list(rows)
    if unit:
        unit_specific = [s for s in steps if s.organizational_unit == unit]
        if unit_specific:
            steps = unit_specific
        else:
            steps = [s for s in steps if not s.organizational_unit]
    role_specific = [s for s in steps if s.designation == role]
    if role and role_specific:
        steps = role_specific
    else:
        steps = [s for s in steps if not s.designation]
    if not steps:
        raise WorkflowConfigurationError(
            f"No approval route is configured for {application.category} in {unit or 'the applicant unit'}."
        )
    director_self = [
        s for s in steps
        if role.lower() == "director" and s.step_type == "sanction"
        and s.assignee_role.lower() == "director"
        and s.assignee_user_id == application.user_id
    ]
    if director_self:
        steps = director_self
    elif application.category in {"CL", "RH"}:
        steps = [s for s in steps if s.step_type == "unit_head"]
        if len(steps) != 1:
            raise WorkflowConfigurationError("CL/RH requires exactly one Unit Head as final authority.")
    else:
        steps = [s for s in steps if s.step_type in {"unit_head", "establishment", "sanction"}]
        types = [s.step_type for s in steps]
        if types not in (["unit_head", "sanction"], ["unit_head", "establishment", "sanction"]):
            raise WorkflowConfigurationError("Higher-sanction route must be Unit Head, optional Establishment, then Sanctioning Authority.")
    if not steps or (not director_self and steps[0].step_type != "unit_head"):
        raise WorkflowConfigurationError("The configured route must begin with a Unit Head unless Director self-sanction applies.")
    if any(s.assignee_user_id is None for s in steps):
        raise WorkflowConfigurationError("Every active workflow step must have an explicit assignee user.")
    assignees = [step.assignee_user_id for step in steps]
    if len(assignees) != len(set(assignees)):
        raise WorkflowConfigurationError("Each approval step must have a distinct assignee.")
    directory_people = get_users(assignees)
    if any(user_id not in directory_people for user_id in assignees):
        raise WorkflowConfigurationError("Every configured approver must exist in the institute directory.")
    for step in steps:
        if step.assignee_user_id == application.user_id and step.assignee_role.lower() != "director":
            raise WorkflowConfigurationError("An employee cannot approve their own leave request.")
    return steps


def initial_assignee(application):
    return route_steps(application)[0].assignee_user_id


def next_step(application, current_assignee_user_id, current_step_type=None):
    steps = route_steps(application)
    for index, step in enumerate(steps):
        if (step.assignee_user_id == current_assignee_user_id
                and (current_step_type is None or step.step_type == current_step_type)):
            return steps[index + 1] if index + 1 < len(steps) else None
    raise WorkflowConfigurationError("Current assignee is not part of the configured route.")
