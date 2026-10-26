import time

from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date


class SplitSessionMiddleware(SessionMiddleware):
    """
    Middleware that separates admin sessions from public website sessions.
    Requests starting with '/admin/' use the session cookie 'rw_admin_sessionid',
    while all other requests use settings.SESSION_COOKIE_NAME ('sessionid').
    This prevents admin logins from leaking to the public site and vice-versa.
    """

    ADMIN_COOKIE_NAME = "rw_admin_sessionid"

    def _get_cookie_name(self, request):
        if request.path.startswith("/admin/"):
            return self.ADMIN_COOKIE_NAME
        return settings.SESSION_COOKIE_NAME

    def process_request(self, request):
        cookie_name = self._get_cookie_name(request)
        session_key = request.COOKIES.get(cookie_name)
        request.session = self.SessionStore(session_key)

    def process_response(self, request, response):
        """
        If request.session was modified, or if the configuration is to save the
        session every time, save the changes and set a session cookie or delete
        the session cookie if the session has been emptied.
        Uses SplitSessionMiddleware cookie name based on request path.
        """
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        cookie_name = self._get_cookie_name(request)

        # First check if we need to delete this cookie.
        # The session should be deleted only if the session is entirely empty.
        if cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            need_vary_cookie = True
        else:
            # If the session was accessed, it must be varied on, regardless of
            # whether it was modified or will be saved.
            need_vary_cookie = accessed
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires_time = time.time() + max_age
                    expires = http_date(expires_time)
                # Save the session data and refresh the client cookie.
                # Skip session save for 5xx responses.
                if response.status_code < 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SessionInterrupted(
                            "The request's session was deleted before the "
                            "request completed. The user may have logged "
                            "out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        cookie_name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
                    # With a session cookie set, it must be varied on.
                    need_vary_cookie = True
        if need_vary_cookie:
            patch_vary_headers(response, ("Cookie",))
        return response


class ViewAsReadOnlyMiddleware:
    """
    Middleware that enforces read-only mode during an active admin view-as session.
    When 'view_as_admin_id' is present in request.session, all non-GET/HEAD/OPTIONS
    requests except POST /view-as/exit/ are blocked and redirected back (or home)
    with messages.error("Read-only admin view: changes are disabled.").
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = getattr(request, "session", None)
        if session and session.get("view_as_admin_id"):
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                if request.path != "/view-as/exit/":
                    try:
                        from django.contrib import messages
                        messages.error(request, "Read-only admin view: changes are disabled.")
                    except Exception:
                        pass
                    referer = request.META.get("HTTP_REFERER")
                    if referer:
                        from django.shortcuts import redirect
                        return redirect(referer)
                    from django.shortcuts import redirect
                    return redirect("home")
        return self.get_response(request)
