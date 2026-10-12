from django.urls import path
from modules.leave.api import views

urlpatterns = [
    path("applications", views.MyApplicationsView.as_view(), name="leave-applications"),
    path("applications/apply", views.ApplyView.as_view(), name="leave-apply"),
    path("applications/<int:pk>/withdraw", views.WithdrawView.as_view(), name="leave-withdraw"),
    path("applications/<int:pk>/substitute-response", views.SubstituteResponseView.as_view(), name="leave-substitute-response"),
    path("applications/<int:pk>/decision", views.DecisionView.as_view(), name="leave-decision"),
    path("balances", views.BalancesView.as_view(), name="leave-balances"),
    path("inbox", views.InboxView.as_view(), name="leave-inbox"),
]
