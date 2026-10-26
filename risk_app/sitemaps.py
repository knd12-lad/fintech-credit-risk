from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            "home",
            "about",
            "how_it_works",
            "contact",
            "login",
            "register",
            "privacy",
            "terms",
        ]

    def location(self, item):
        return reverse(item)
