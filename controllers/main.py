import logging

import werkzeug
from markupsafe import Markup
from werkzeug.urls import url_encode

from odoo import _, http
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)


class EmailVerificationSignup(AuthSignupHome):
    @http.route(
        '/web/signup',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
        captcha='signup',
        list_as_website_content=_lt('Sign Up'),
    )
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext, do_login=False)
                user_model = request.env['res.users']
                user = user_model.sudo().search(
                    user_model._get_login_domain(qcontext.get('login')),
                    order=user_model._get_login_order(),
                    limit=1,
                )
                if user:
                    user.sudo().action_prepare_email_verification()
                    return request.redirect('/mail/verify?%s' % url_encode({'login': user.login}))
                qcontext['error'] = _('The account was created, but email verification could not be started.')
            except UserError as error:
                qcontext['error'] = error.args[0]
            except (SignupError, AssertionError) as error:
                user_model = request.env['res.users']
                existing_user = user_model.sudo().with_context(active_test=False).search(
                    user_model._get_login_domain(qcontext.get('login')),
                    limit=1,
                )
                if existing_user:
                    qcontext['error'] = _('Another user is already registered using this email address.')
                else:
                    _logger.warning('%s', error)
                    qcontext['error'] = _('Could not create a new account.') + Markup('<br/>') + str(error)

        response = request.render('auth_signup.signup', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response


class EmailVerificationController(http.Controller):
    def _find_signup_user(self, login):
        user_model = request.env['res.users'].sudo()
        user = user_model.search(
            user_model._get_login_domain(login),
            order=user_model._get_login_order(),
            limit=1,
        )
        if not user and login:
            user = user_model.search(user_model._get_email_domain(login), limit=1)
        return user.filtered(lambda current_user: current_user.share)[:1]

    @http.route('/mail/verify', type='http', auth='public', website=True, sitemap=False, methods=['GET', 'POST'])
    def verify_email(self, **kw):
        login = (kw.get('login') or '').strip()
        qcontext = {
            'login': login,
            'login_url': '/web/login?%s' % url_encode({'login': login}) if login else '/web/login',
            'code': '',
            'error': kw.get('error'),
            'message': kw.get('message'),
            'verified': False,
        }

        if request.httprequest.method == 'POST':
            code = (kw.get('code') or '').strip()
            qcontext['code'] = code
            user = self._find_signup_user(login)

            if not user:
                qcontext['error'] = _('No account found for this email address.')
            else:
                try:
                    user.sudo().action_verify_email_code(code)
                    qcontext['verified'] = True
                    qcontext['message'] = _('Email address verified. You can sign in now.')
                    qcontext['code'] = ''
                except UserError as error:
                    qcontext['error'] = error.args[0]

        response = request.render('emailverified.verify_email_page', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    @http.route('/mail/verify/resend', type='http', auth='public', website=True, sitemap=False, methods=['POST'])
    def resend_verification_email(self, **kw):
        login = (kw.get('login') or '').strip()
        params = {'login': login}
        user = self._find_signup_user(login)

        if not user:
            params['error'] = _('No account found for this email address.')
        else:
            try:
                user.sudo().action_prepare_email_verification()
                params['message'] = _('A new verification code has been sent.')
            except UserError as error:
                params['error'] = error.args[0]

        return request.redirect('/mail/verify?%s' % url_encode(params))


class WebsiteLoginEmailVerification(AuthSignupHome):
    @http.route()
    def web_login(self, *args, **kw):
        response = super().web_login(*args, **kw)
        if request.httprequest.method == 'POST' and request.params.get('login') and not request.session.uid:
            user = EmailVerificationController()._find_signup_user(request.params.get('login'))
            if user and not user.email_verified and isinstance(response.qcontext, dict):
                response.qcontext['error'] = _('Your email address is not verified. Enter the code sent to your email first.')
                response.qcontext['login'] = user.login
                response.qcontext['email_verification_url'] = '/mail/verify?%s' % url_encode({'login': user.login})
        return response