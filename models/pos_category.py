from odoo import models, fields


class PosCategory(models.Model):
    _inherit = 'pos.category'

    exclude_from_report_turnover = fields.Boolean(
        string="Non-Revenue / Clearing Activity",
        default=False,
        help="If checked, POS lines in this category are treated as cash movement or clearing activity "
             "instead of merchandise revenue in POS reports. Use this for lottery payouts, container "
             "deposits, and similar non-revenue items."
    )
