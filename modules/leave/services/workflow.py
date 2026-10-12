"""Fail-closed workflow routing from the administrator-maintained route table."""
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
    else:
        steps = [s for s in steps if s.step_type in {"unit_head", "establishment", "sanction"}]
    if not steps or steps[0].step_type != "unit_head":
        raise WorkflowConfigurationError("The configured route must begin with a Unit Head.")
    if any(s.assignee_user_id is None for s in steps):
        raise WorkflowConfigurationError("Every active workflow step must have an explicit assignee user.")
    for step in steps:
        if step.assignee_user_id == application.user_id and step.assignee_role.lower() != "director":
            raise WorkflowConfigurationError("An employee cannot approve their own leave request.")
    return steps


def initial_assignee(application):
    return route_steps(application)[0].assignee_user_id


def next_step(application, current_assignee_user_id):
    steps = route_steps(application)
    for index, step in enumerate(steps):
        if step.assignee_user_id == current_assignee_user_id:
            return steps[index + 1] if index + 1 < len(steps) else None
    raise WorkflowConfigurationError("Current assignee is not part of the configured route.")
