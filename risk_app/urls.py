from django.contrib.auth import views as auth_views
from django.urls import path

from . import view_as, views
from .forms import EmailLoginForm

urlpatterns = [
    path("", views.home, name="home"),
    
    path("about/", views.about_view, name="about"),
    path("how-it-works/", views.how_it_works_view, name="how_it_works"),
    path("privacy/", views.privacy_view, name="privacy"),
    path("terms/", views.terms_view, name="terms"),
    path("contact/", views.contact_view, name="contact"),

    # Profile
    path("profile/", views.profile_view, name="profile"),
    path(
        "profile/edit/",
        views.edit_profile_view,
        name="edit_profile",
    ),

    # Change Password — unchanged
    path(
        "profile/change-password/",
        views.RiskWisePasswordChangeView.as_view(),
        name="password_change",
    ),

    # Risk Checker
    path("risk-checker/", views.risk_checker_view, name="risk_checker"),
    path("history/", views.history_view, name="history"),
    path(
        "result/<int:application_id>/",
        views.result_view,
        name="result",
    ),
    path(
        "api/what-if/<int:application_id>/",
        views.what_if_api,
        name="what_if_api",
    ),
    path(
        "result/<int:application_id>/report.pdf",
        views.download_pdf_report,
        name="download_pdf_report",
    ),

    # Authentication
    path("register/", views.register_view, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="login.html",
            authentication_form=EmailLoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Admin view-as hand-off & exit (non-admin routes)
    path("view-as/enter/", view_as.view_as_enter, name="view_as_enter"),
    path("view-as/exit/", view_as.view_as_exit, name="view_as_exit"),
]