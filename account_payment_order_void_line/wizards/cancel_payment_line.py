# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import _, fields, models


class CancelVoidPaymentLine(models.TransientModel):
    _name = "cancel.void.payment.line"
    _description = "Void Payment Line"

    reason = fields.Text(
        string="Reason for the cancel",
    )

    def cancel_payment_line_entry(self):
        bank_payment = self.env["bank.payment.line"].browse(
            self._context.get("active_id")
        )
        # find the counterpart line we are voiding
        counterpart_lines = bank_payment.order_id.move_ids.line_ids
        # account move line
        move_line = counterpart_lines.filtered(lambda l: l.bank_payment_line_id.id == bank_payment.id)
        # journal entry
        move_id = move_line.move_id
        moves_vals_list = []
        move_line.remove_move_reconcile()
        new_move_date = date.today()
        moves_vals_list.append(
            move_id.with_context(include_business_fields=True).copy_data(
                {
                    "date": new_move_date,
                    "invoice_date": new_move_date,
                    "journal_id": move_id.journal_id.id,
                    "ref": (_("Reversal of: %s")) % (move_id.name),
                    "partner_id": bank_payment.partner_id.id,
                }
            )[0]
        )
        # take out the voided payment and create a new entry
        reversed_move = self.env["account.move"].create(moves_vals_list)
        for acm_line in reversed_move.line_ids.with_context(check_move_validity=False):
            acm_line.write(
                {
                    "debit": acm_line.credit,
                    "credit": acm_line.debit,
                    "balance":-acm_line.balance,
                    "amount_currency": -acm_line.amount_currency,
                    "amount_residual": -acm_line.amount_residual,
                    "amount_residual_currency": -acm_line.amount_residual_currency,
                }
            )
        reversed_move.recompute()

        # identify lines that need to be taken out from the reversed move
        unlink_ids = reversed_move.mapped('line_ids').filtered(
            lambda l: l.partner_id.id != bank_payment.partner_id.id and l.move_id.id == reversed_move.id and l.debit == 0)
        debit = sum(unlink_ids.mapped('debit'))
        credit = sum(unlink_ids.mapped('credit'))
        total = abs(debit - credit)

        # identify line that needs to be adjusted for new payment amount
        payment_line_id = self.env["account.move.line"].search(
            [
                ("move_id", "=", reversed_move.id),
                (
                    "account_id",
                    "=",
                    reversed_move.journal_id.payment_credit_account_id.id,
                ),
                ("debit", ">", 0.0),
            ]
        )
        new_amount = abs(payment_line_id.debit - total)
        # update reversed move
        reversed_move.write(
            {
                "line_ids": [
                    (3, unlink_ids.ids),
                    (1, payment_line_id.id, {"debit": new_amount, "credit": 0.0}),
                ]
            }
        )

        # reconcile receivable/payable lines
        reconcile_lines = self.env["account.move.line"].search(
            [
                ("partner_id", "=", bank_payment.partner_id.id),
                ("move_id", "in", [move_id.id, reversed_move.id]),
                ("account_id", "!=", move_id.journal_id.payment_credit_account_id.id),
            ]
        )
        for line in reconcile_lines:
            if not line.account_id.reconcile:
                reconcile_lines -= line

        reversed_move.action_post()
        reconcile_lines.reconcile()

        for payment_line in bank_payment.payment_line_ids:
            payment_line.is_voided = True
            payment_line.void_date = date.today()
            payment_line.void_reason = self.reason
        bank_payment.is_voided = True
        bank_payment.void_date = date.today()
        bank_payment.void_reason = self.reason
        bank_payment.order_id.message_post(
            body=(
                _(
                    "Voiding Date: %s <br> Partner: %s <br> \
            Total Amount: %s <br> Invoice Ref #: %s \
            <br> Void Reason: %s"
                )
                % (
                    bank_payment.void_date,
                    bank_payment.partner_id.name,
                    bank_payment.amount_currency,
                    bank_payment.communication,
                    bank_payment.void_reason,
                )
            )
        )
        for payment_line in bank_payment.payment_line_ids:
            payment_line.move_line_id.move_id.message_post(
                body=(
                    _("Void Reason: %s <br> Void Date: %s")
                    % (bank_payment.void_reason, bank_payment.void_date)
                )
            )
