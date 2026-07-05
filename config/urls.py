from django.contrib import admin
from django.urls import path
from accounts import views
from accounts import api_views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
schema_view = get_schema_view(
    openapi.Info(
        title="SmartBank Pro API",
        default_version="v1",
        description="SmartBank Pro REST API Documentation",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)
urlpatterns = [
    path("admin/", admin.site.urls),

    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("deposit/", views.deposit, name="deposit"),
path("withdraw/", views.withdraw, name="withdraw"),
path("transactions/", views.transaction_history, name="transactions"),
path("transfer/", views.transfer_money, name="transfer"),
path("logout/", views.logout_view, name="logout"),
path("api/register/", api_views.RegisterAPIView.as_view(), name="api-register"),
path("api/login/", api_views.LoginAPIView.as_view(), name="api-login"),
path("api/dashboard/", api_views.DashboardAPIView.as_view(), name="api-dashboard"),
path("api/deposit/", api_views.DepositAPIView.as_view(), name="api-deposit"),
path("api/withdraw/", api_views.WithdrawAPIView.as_view(), name="api-withdraw"),
path("api/transfer/", api_views.TransferAPIView.as_view(), name="api-transfer"),
path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
path("api/transactions/", api_views.TransactionHistoryAPIView.as_view(), name="api-transactions"),
path("api/profile/", api_views.ProfileAPIView.as_view(), name="api-profile"),
path("api/change-password/", api_views.ChangePasswordAPIView.as_view(), name="api-change-password"),
path("api/update-profile/",api_views.UpdateProfileAPIView.as_view(),name="api-update-profile"),
path("api/balance/",api_views.BalanceAPIView.as_view(), name="api-balance"),
path("api/statement/",api_views.AccountStatementAPIView.as_view(),name="api-statement"),
path("api/delete-account/",api_views.DeleteAccountAPIView.as_view(),name="api-delete-account"),
path("swagger/",schema_view.with_ui("swagger", cache_timeout=0),name="swagger-ui",),
path("redoc/",schema_view.with_ui("redoc", cache_timeout=0),name="redoc",),
path("api/statement/pdf/",api_views.BankStatementPDFAPIView.as_view(),name="api-statement-pdf",),
path("admin-dashboard/", views.admin_dashboard, name="admin-dashboard"),
path( "api/statement/pdf/", api_views.BankStatementPDFAPIView.as_view(), name="api-statement-pdf",),
path( "api/statement/excel/", api_views.BankStatementExcelAPIView.as_view(),name="api-statement-excel",),
path("test-ai/", views.test_ai, name="test_ai"),
path("chatbot/", views.chatbot, name="chatbot"),
path("ask-ai/", views.ask_ai, name="ask_ai"),
path("profile/", views.profile, name="profile"),
path("statement/pdf/", views.download_statement_pdf, name="download-pdf"),
path("statement/excel/", views.download_statement_excel, name="download-excel"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)