# RW-D1
from django.contrib.admin.apps import AdminConfig


class RiskWiseAdminConfig(AdminConfig):
    default_site = "risk_app.admin_site.RiskWiseAdminSite"
