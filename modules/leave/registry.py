"""ELM module registry and role grants."""
MODULE = {
    "code": "employee_leave_management", "label": "Employee Leave Management",
    "icon": "FaCalendarCheck", "base_path": "/leave",
    "nav_section": "Administration", "sort_order": 40, "status": "active",
}
PERMISSIONS = [
    ("employee_leave_management.application.view_self", "View own leave applications and balances"),
    ("employee_leave_management.application.create", "Apply for leave"),
    ("employee_leave_management.application.withdraw", "Withdraw a pending leave request"),
    ("employee_leave_management.application.cancel", "Request cancellation of approved leave"),
    ("employee_leave_management.application.extend", "Request extension of ongoing leave"),
    ("employee_leave_management.application.resume", "Submit resumption of duty"),
    ("employee_leave_management.workflow.review", "Review leave requests"),
    ("employee_leave_management.workflow.sanction", "Make final leave decisions"),
    ("employee_leave_management.substitute.respond", "Accept or decline substitute responsibility"),
    ("employee_leave_management.calendar.manage", "Maintain and publish holiday and RH calendars"),
    ("employee_leave_management.policy.manage", "Maintain leave policy and hierarchy configuration"),
    ("employee_leave_management.records.manage", "Maintain authorized leave records"),
    ("employee_leave_management.report.view", "View leave management reports"),
]
SYSTEM_PERMISSIONS = ["employee_leave_management.workflow.year_end", "employee_leave_management.workflow.sla"]
_EMPLOYEE = [
    "employee_leave_management.application.view_self", "employee_leave_management.application.create",
    "employee_leave_management.application.withdraw", "employee_leave_management.application.cancel",
    "employee_leave_management.application.extend", "employee_leave_management.application.resume",
]
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "employee": _EMPLOYEE,
    "unit_head": [*_EMPLOYEE, "employee_leave_management.workflow.review"],
    "Head of Department": [*_EMPLOYEE, "employee_leave_management.workflow.review"],
    "Head of Section": [*_EMPLOYEE, "employee_leave_management.workflow.review"],
    "Head of Office": [*_EMPLOYEE, "employee_leave_management.workflow.review"],
    "leave_administrator": [*_EMPLOYEE, "employee_leave_management.policy.manage",
        "employee_leave_management.calendar.manage", "employee_leave_management.records.manage", "employee_leave_management.report.view"],
    "Leave Administrator": [*_EMPLOYEE, "employee_leave_management.policy.manage",
        "employee_leave_management.calendar.manage", "employee_leave_management.records.manage", "employee_leave_management.report.view"],
    "Deputy Registrar (Estt.)": ["employee_leave_management.workflow.review", "employee_leave_management.workflow.sanction",
                                 "employee_leave_management.report.view"],
    "Dean": ["employee_leave_management.workflow.review", "employee_leave_management.workflow.sanction", "employee_leave_management.report.view"],
    "Registrar": ["employee_leave_management.workflow.review", "employee_leave_management.workflow.sanction", "employee_leave_management.report.view"],
    "Director": ["employee_leave_management.workflow.review", "employee_leave_management.workflow.sanction", "employee_leave_management.report.view"],
}
NAV_ITEMS = [
    {"code":"employee_leave_management.mine","label":"My Leave","icon":"FaCalendarAlt","to":"/leave/mine",
     "required_permission":"employee_leave_management.application.view_self","sort_order":10},
    {"code":"employee_leave_management.inbox","label":"Leave Approvals","icon":"FaInbox","to":"/leave/inbox",
     "required_permission":"employee_leave_management.workflow.review","sort_order":20},
    {"code":"employee_leave_management.admin","label":"Leave Administration","icon":"FaSlidersH","to":"/leave/admin",
     "required_permission":"employee_leave_management.policy.manage","sort_order":30},
]
