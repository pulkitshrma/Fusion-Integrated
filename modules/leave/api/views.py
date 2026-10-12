"""ELM HTTP boundary. Domain failures are translated to stable API errors."""
from django.utils import timezone\nfrom django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from core.api.exceptions import ConflictError
from modules.leave.api import serializers as s
from modules.leave.domain.rules import PolicyViolation
from modules.leave.models import (
    LeaveApplication, LeaveBalance, LeaveCalendar, LeaveLifecycleRequest,
    LeavePolicy, LeaveSLAConfig, LeaveWorkflowStep, LeaveSLAEvent,
)
from modules.leave.selectors import applications as selectors
from modules.leave.services import applications as service
from modules.leave.services import lifecycle


MODULE = HasModuleGrant("employee_leave_management")
P_SELF = "leave.application.view_self"
P_CREATE = "leave.application.create"
P_REVIEW = "leave.workflow.review"
P_SANCTION = "leave.workflow.sanction"


def actor(request):
    return request.principal


def _run(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except PolicyViolation as exc:
        raise ConflictError(str(exc), code=exc.code) from exc
    except service.workflow.WorkflowConfigurationError as exc:
        raise ConflictError(str(exc), code="workflow_configuration_error") from exc


class MyApplicationsView(generics.ListAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_SELF)]
    def get_queryset(self):
        return selectors.own_applications(actor(self.request).user_id)


class ApplyView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]
    def post(self, request):
        payload = s.LeaveApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = _run(service.apply, actor=actor(request), **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.withdraw")]
    def post(self, request, pk):
        app = service.withdraw(application_id=pk, actor=actor(request))
        return Response(s.LeaveApplicationSerializer(app).data)


class SubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission("leave.substitute.respond")]
    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = _run(service.respond_substitute, application_id=pk,
                   actor=actor(request), **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(app).data)


class ReplacementSubstituteView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]
    def post(self, request, pk):
        payload = s.ReplacementSubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = _run(service.nominate_replacement, application_id=pk,
                   actor=actor(request), **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(app).data)


class DecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_SANCTION)]
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = _run(service.decide, application_id=pk, actor=actor(request),
                   **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(app).data)


class BalancesView(generics.ListAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE, HasPermission(P_SELF)]
    def get_queryset(self):
        year = int(self.request.query_params.get("year", timezone.localdate().year))
        return selectors.own_balances(actor(self.request).user_id, year)


class InboxView(generics.ListAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_SANCTION)]
    def get_queryset(self):
        return selectors.assigned_inbox(actor(self.request).user_id)


class CancellationView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.cancel")]
    def post(self, request, pk):
        payload = s.CancellationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = _run(lifecycle.request_cancellation, application_id=pk,
                    actor=actor(request), **payload.validated_data)
        return Response(s.LifecycleRequestSerializer(item).data, status=201)


class ExtensionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.extend")]
    def post(self, request, pk):
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = _run(lifecycle.request_extension, application_id=pk,
                    actor=actor(request), **payload.validated_data)
        return Response(s.LifecycleRequestSerializer(item).data, status=201)


class LifecycleSubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission("leave.substitute.respond")]
    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = _run(lifecycle.respond_extension_substitute, request_id=pk,
                    actor=actor(request), **payload.validated_data)
        return Response(s.LifecycleRequestSerializer(item).data)


class LifecycleReplacementSubstituteView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]
    def post(self, request, pk):
        payload = s.ReplacementSubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = _run(lifecycle.nominate_extension_replacement, request_id=pk,
                    actor=actor(request), **payload.validated_data)
        return Response(s.LifecycleRequestSerializer(item).data)


class ResumptionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.resume")]
    def post(self, request, pk):
        payload = s.ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = _run(lifecycle.submit_resumption, application_id=pk,
                    actor=actor(request), **payload.validated_data)
        return Response(s.LifecycleRequestSerializer(item).data, status=201)


class LifecycleDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_SANCTION)]
    def post(self, request, pk):
        payload = s.LifecycleDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = _run(lifecycle.decide_lifecycle, request_id=pk,
                    actor=actor(request), **payload.validated_data)
        return Response(s.LifecycleRequestSerializer(item).data)


class MyLifecycleRequestsView(generics.ListAPIView):
    serializer_class = s.LifecycleRequestSerializer
    permission_classes = [MODULE, HasPermission(P_SELF)]
    def get_queryset(self):
        return LeaveLifecycleRequest.objects.filter(
            application__user_id=actor(self.request).user_id
        ).order_by("-created_at")


class PolicyAdminView(generics.ListCreateAPIView):
    queryset = LeavePolicy.objects.all().order_by("category")
    serializer_class = s.PolicySerializer
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]


class CalendarAdminView(generics.ListCreateAPIView):
    queryset = LeaveCalendar.objects.all().order_by("-year", "kind")
    serializer_class = s.CalendarSerializer
    permission_classes = [MODULE, HasPermission("leave.calendar.manage")]


class CalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.manage")]
    def post(self, request, pk):
        calendar = LeaveCalendar.objects.filter(pk=pk).first()
        if calendar is None:
            from core.api.exceptions import NotFoundError
            raise NotFoundError("No such calendar.")
        if not isinstance(calendar.dates, list) or not calendar.dates:
            raise ConflictError("A calendar must contain at least one date.", code="invalid_calendar")
        from datetime import date
        try:
            dates = [date.fromisoformat(value) for value in calendar.dates]
        except (TypeError, ValueError) as exc:
            raise ConflictError("Calendar dates must be ISO YYYY-MM-DD values.", code="invalid_calendar") from exc
        if len(dates) != len(set(dates)) or any(d.year != calendar.year for d in dates):
            raise ConflictError("Calendar dates must be unique and belong to the selected year.", code="invalid_calendar")
        from django.utils import timezone as tz
        LeaveCalendar.objects.filter(year=calendar.year, kind=calendar.kind,
                                     is_published=True).exclude(pk=calendar.pk).update(is_published=False)
        calendar.is_published = True
        calendar.published_at = tz.now()
        calendar.published_by_user_id = actor(request).user_id
        calendar.save(update_fields=["is_published", "published_at", "published_by_user_id", "updated_at"])
        return Response(s.CalendarSerializer(calendar).data)


class WorkflowAdminView(generics.ListCreateAPIView):
    queryset = LeaveWorkflowStep.objects.all().order_by("category", "sequence")
    serializer_class = s.WorkflowStepSerializer
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]


class SLAAdminView(generics.ListCreateAPIView):
    queryset = LeaveSLAConfig.objects.all().order_by("task_type")
    serializer_class = s.SLAConfigSerializer
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]


class OfflineSanctionRecordView(APIView):
    permission_classes = [MODULE, HasPermission("leave.records.manage")]
    def post(self, request):
        payload = s.OfflineSanctionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = _run(service.record_offline_sanctioned, actor=actor(request),
                   **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(app).data, status=201)


class PolicyDetailAdminView(generics.RetrieveUpdateAPIView):
    queryset = LeavePolicy.objects.all()
    serializer_class = s.PolicySerializer
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]


class CalendarDetailAdminView(generics.RetrieveUpdateAPIView):
    queryset = LeaveCalendar.objects.all()
    serializer_class = s.CalendarSerializer
    permission_classes = [MODULE, HasPermission("leave.calendar.manage")]


class WorkflowDetailAdminView(generics.RetrieveUpdateAPIView):
    queryset = LeaveWorkflowStep.objects.all()
    serializer_class = s.WorkflowStepSerializer
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]


class SLADetailAdminView(generics.RetrieveUpdateAPIView):
    queryset = LeaveSLAConfig.objects.all()
    serializer_class = s.SLAConfigSerializer
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]


class ApplicationExportView(APIView):
    permission_classes = [MODULE, HasPermission(P_SELF, P_REVIEW, P_SANCTION)]
    def get(self, request, pk):
        item = LeaveApplication.objects.filter(pk=pk).first()
        if item is None:
            from core.api.exceptions import NotFoundError
            raise NotFoundError("No such leave application.")
        principal = actor(request)
        if item.user_id != principal.user_id and item.current_assignee_user_id != principal.user_id:
            if not principal.has_permission("leave.report.view"):
                from core.api.exceptions import PermissionDeniedError
                raise PermissionDeniedError("You cannot export this leave application.")
        body = (
            "EMPLOYEE LEAVE APPLICATION\\n"
            f"Reference: {item.pk}\\nEmployee user ID: {item.user_id}\\n"
            f"Category: {item.category}\\nPeriod: {item.start_date} to {item.end_date}\\n"
            f"Requested days: {item.requested_days}\\nPurpose: {item.purpose}\\n"
            f"Status: {item.status}\\nStation Leave: {item.station_leave_required}\\n"
            f"Station Leave details: {item.station_leave_details}\\n"
            f"Final decision: {item.decision_note}\\n"
        )
        return HttpResponse(body, content_type="text/plain; charset=utf-8")


class LeaveReportView(APIView):
    permission_classes = [MODULE, HasPermission("leave.report.view")]
    def get(self, request):
        from django.db.models import Count
        by_status = list(LeaveApplication.objects.values("status").annotate(count=Count("id")).order_by("status"))
        by_category = list(LeaveApplication.objects.values("category").annotate(count=Count("id")).order_by("category"))
        return Response({"applications_by_status": by_status, "applications_by_category": by_category})
