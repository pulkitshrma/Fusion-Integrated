"""ELM module registry and role grants."""
MODULE = {
    "code": "employee_leave_management", "label": "Employee Leave Management",
    "icon": "FaCalendarCheck", "base_path": "/leave",
    "nav_section": "Administration", "sort_order": 40, "status": "active",
}
PERMISSIONS = [
    ("leave.application.view_self", "View own leave applications and balances"),
    ("leave.application.create", "Apply for leave"),
    ("leave.application.withdraw", "Withdraw a pending leave request"),
    ("leave.application.cancel", "Request cancellation of approved leave"),
    ("leave.application.extend", "Request extension of ongoing leave"),
    ("leave.application.resume", "Submit resumption of duty"),
    ("leave.workflow.review", "Review leave requests"),
    ("leave.workflow.sanction", "Make final leave decisions"),
    ("leave.substitute.respond", "Accept or decline substitute responsibility"),
    ("leave.calendar.manage", "Maintain and publish holiday and RH calendars"),
    ("leave.policy.manage", "Maintain leave policy and hierarchy configuration"),
    ("leave.records.manage", "Maintain authorized leave records"),
    ("leave.report.view", "View leave management reports"),
]
SYSTEM_PERMISSIONS = ["leave.workflow.year_end", "leave.workflow.sla"]
_EMPLOYEE = [
    "leave.application.view_self", "leave.application.create",
    "leave.application.withdraw", "leave.application.cancel",
    "leave.application.extend", "leave.application.resume",
]
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "employee": _EMPLOYEE,
    "unit_head": ["leave.application.view_self", "leave.workflow.review",
                  "leave.substitute.respond"],
    "Head of Department": ["leave.workflow.review", "leave.substitute.respond"],
    "Head of Section": ["leave.workflow.review", "leave.substitute.respond"],
    "Head of Office": ["leave.workflow.review", "leave.substitute.respond"],
    "leave_administrator": ["leave.application.view_self", "leave.policy.manage",
        "leave.calendar.manage", "leave.records.manage", "leave.report.view"],
    "Leave Administrator": ["leave.policy.manage", "leave.calendar.manage",
        "leave.records.manage", "leave.report.view"],
    "Deputy Registrar (Estt.)": ["leave.workflow.review", "leave.workflow.sanction",
                                 "leave.report.view"],
    "Dean": ["leave.workflow.review", "leave.workflow.sanction", "leave.report.view"],
    "Registrar": ["leave.workflow.review", "leave.workflow.sanction", "leave.report.view"],
    "Director": ["leave.workflow.review", "leave.workflow.sanction", "leave.report.view"],
}
NAV_ITEMS = [
    {"code":"leave.mine","label":"My Leave","icon":"FaCalendarAlt","to":"/leave/mine",
     "required_permission":"leave.application.view_self","sort_order":10},
    {"code":"leave.inbox","label":"Leave Approvals","icon":"FaInbox","to":"/leave/inbox",
     "required_permission":"leave.workflow.review","sort_order":20},
    {"code":"leave.admin","label":"Leave Administration","icon":"FaSlidersH","to":"/leave/admin",
     "required_permission":"leave.policy.manage","sort_order":30},
]
