import random
from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import AccessDenied, UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    email_verified = fields.Boolean(string='Email Verified', default=True, copy=False)
    email_verification_code = fields.Char(string='Email Verification Code', copy=False, groups='base.group_system')
    email_verification_expire = fields.Datetime(string='Email Verification Expire', copy=False, groups='base.group_system')

    def _generate_email_verification_code(self):
        self.ensure_one()
        return f"{random.SystemRandom().randint(0, 999999):06d}"

    def action_prepare_email_verification(self):
        template = self.env.ref('emailverified.mail_template_email_verification', raise_if_not_found=False)
        if not template:
            raise UserError(_('Email verification template could not be found.'))

        for user in self:
            if not user.email:
                raise UserError(_('Cannot send the verification code because the user has no email address.'))

            user.sudo().write({
                'email_verified': False,
                'email_verification_code': user._generate_email_verification_code(),
                'email_verification_expire': fields.Datetime.now() + timedelta(minutes=30),
            })
            template.sudo().send_mail(user.id, force_send=True)

        return True

    def action_verify_email_code(self, code):
        self.ensure_one()

        if not code:
            raise UserError(_('Please enter the verification code.'))
        if self.email_verified:
            return True
        if not self.email_verification_code:
            raise UserError(_('No verification code was generated for this account.'))
        if self.email_verification_expire and fields.Datetime.now() > self.email_verification_expire:
            raise UserError(_('The verification code has expired. Please request a new one.'))
        if self.email_verification_code != code.strip():
            raise UserError(_('The verification code is incorrect.'))

        self.sudo().write({
            'email_verified': True,
            'email_verification_code': False,
            'email_verification_expire': False,
        })
        return True

    def _check_credentials(self, credential, env):
        auth_info = super()._check_credentials(credential, env)
        if credential.get('type') == 'password' and self.share and not self.email_verified:
            raise AccessDenied(_('Email address is not verified. Please verify your email before signing in.'))
        return auth_info