from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from core.api.exceptions import PermissionDeniedError
from modules.leave.api import serializers as s
from modules.leave.selectors import applications as selectors
from modules.leave.services import applications as service
from modules.leave.models import LeaveApplication, LeaveBalance

MODULE = HasModuleGrant("employee_leave_management")
P_SELF = "leave.application.view_self"
P_CREATE = "leave.application.create"
P_REVIEW = "leave.workflow.review"
P_SANCTION = "leave.workflow.sanction"


def actor(request):
    return request.principal


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
        app = service.apply(actor=actor(request), **payload.validated_data)
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
        app = service.respond_substitute(application_id=pk, actor=actor(request), **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(app).data)


class DecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_SANCTION)]
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = service.decide(application_id=pk, actor=actor(request), **payload.validated_data)
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
