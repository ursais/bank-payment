# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Payment Order Email",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Odoo Community Association (OCA)",
    "maintainers": "Open Source Integrators",
    "website": "https://github.com/OCA/bank-payment",
    "category": "Accounting",
    "depends": ["account_payment_order", "account_payment_mode"],
    "data": [
        "data/ach_payment_email_template.xml",
        "views/account_payment_mode_view.xml",
        "views/account_payment_order_view.xml",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
}
