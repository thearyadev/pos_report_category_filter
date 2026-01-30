from odoo import models, fields


class PosCategory(models.Model):
    _inherit = 'pos.category'

    exclude_from_report_turnover = fields.Boolean(
        string="Exclude from POS Sales Report",
        default=False,
        help="If checked, items in this POS category will be separated from net sales "
             "in the POS Z-Report and shown in a separate 'Payouts & Adjustments' section."
    )
