{
    'name': 'Website Email Verification',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Require website users to verify email after signup',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'auth_signup',
        'website',
        'mail',
    ],
    'data': [
        'data/mail_template.xml',
        'views/email_verification_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}