# Employee Leave Management (ELM)

This app implements the synchronized ELM v1.4 baseline as an independent Fusion Django domain module.

## Included capabilities

- CL, RH, SCL, EL, COL and VL policy/balance validation.
- First/second-half CL and the distinct-half overlap exception.
- Published holiday and RH calendars; VL vacation-window cache for the Academic Calendar integration.
- Station Leave details on the original application.
- Substitute nomination, accept/decline, replacement and explicit substitute inboxes.
- Explicit, fail-closed approval routes configured by category, organizational unit and applicant role.
- Unit Head final decision for CL/RH; Unit Head recommendation followed by configured Establishment/Sanctioning Authority steps for SCL/EL/COL/VL.
- Pending withdrawal; separate pre-start cancellation; separate extension and resumption requests.
- Audited balance ledger, offline-sanction synchronization and printable text export.
- Policy, calendar, workflow and SLA administration APIs.
- Year-end lapse/carry-forward/VL-to-EL conversion and SLA reminder/escalation management commands.
- Employee balance/history, assigned workflow inboxes and aggregate reports.

## Database setup

Run migrations after installing the repository's normal dependencies and configuring PostgreSQL:

```bash
python manage.py migrate
```

The migration seeds the v1.4 baseline annual entitlements: CL 8, RH 2, SCL 15, EL 30 for non-faculty, COL 20 and VL 60 for faculty. The values remain editable through the policy administration API.

## Required institute configuration

ELM deliberately fails closed until the institute configures its real approvers. It does not guess a Unit Head or sanctioning authority.

1. Create active `LeaveWorkflowStep` rows for each leave category.
2. Set `organizational_unit` to the directory department/section/office string, or leave it blank for a generic route.
3. Set `designation` to the applicant's IAM active-role string, or leave it blank for a generic route.
4. Set each step's explicit `assignee_user_id`, `sequence` and `step_type` (`unit_head`, `establishment`, `sanction`).
5. CL/RH routes use the Unit Head as final authority. SCL/EL/COL/VL routes must include a Unit Head first and the configured higher authority path after it. Director self-sanction is represented by a sanction step assigned to the Director with `assignee_role="Director"`.
6. Configure SLA rows for task types such as `awaiting_substitute`, `awaiting_unit_head`, `awaiting_establishment`, `awaiting_sanction`, and `lifecycle:extension`. Escalation threshold must exceed reminder threshold.

A route without a configured assignee is rejected rather than leaving a request unassigned.

## Academic Calendar integration

VL requires vacation periods supplied by the institute Academic Calendar. The model `LeaveVacationPeriod` stores the synchronized periods used for validation. Until those periods are synchronized, VL requests are rejected. Do not manually invent vacation dates.

## API surface

Base path: `/api/v1/leave/`

- `GET applications`, `POST applications/apply`, `POST applications/{id}/withdraw`
- `POST applications/{id}/cancel`, `POST applications/{id}/extend`, `POST applications/{id}/resumption`
- `POST applications/{id}/substitute-response`, `POST applications/{id}/substitute-replacement`
- `GET substitute/inbox`, `GET substitute/lifecycle-inbox`
- `POST lifecycle/{id}/substitute-response`, `POST lifecycle/{id}/substitute-replacement`, `POST lifecycle/{id}/decision`
- `GET lifecycle/mine`, `GET balances`, `GET inbox`
- `GET applications/{id}/export`
- `GET/POST admin/policies`, `PUT/PATCH admin/policies/{id}`
- `GET/POST admin/calendars`, `PUT/PATCH admin/calendars/{id}`, `POST admin/calendars/{id}/publish`
- `GET/POST admin/workflow`, `PUT/PATCH admin/workflow/{id}`
- `GET/POST admin/sla`, `PUT/PATCH admin/sla/{id}`
- `POST admin/offline-sanction`, `GET admin/reports`

All endpoints require the Fusion IAM module grant and the relevant ELM permission.

## Scheduled operations

Run the event-triggered jobs from cron/Celery Beat after configuring the institute's year-end boundary and desired SLA polling cadence:

```bash
python manage.py process_leave_year_end --year 2026
python manage.py process_leave_sla
```

Year-end processing is idempotent by leave year and ledger reference. Inspect `LeaveYearEndRun.exceptions` before treating a failed run as complete.

## Tests

```bash
python manage.py test modules.leave
```

The included unit tests cover core category applicability, RH/vacation validation, the half-day overlap exception, year-end outcomes and state transitions. Run the full project test suite and migration checks in the Fusion development environment before deployment.
