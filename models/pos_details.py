from odoo import fields, models


class PosDetails(models.TransientModel):
    _inherit = 'pos.details.wizard'

    apply_non_revenue_filter = fields.Boolean(
        string="Separate non-revenue activity",
        default=True,
        help="Move POS categories marked as non-revenue out of merchandise sales and tax totals. "
             "Disable this to print Odoo's native Sales Details report.",
    )

    def generate_report(self):
        data = {
            'date_start': self.start_date,
            'date_stop': self.end_date,
            'config_ids': self.pos_config_ids.ids,
            'apply_non_revenue_filter': self.apply_non_revenue_filter,
        }
        return self.env.ref('point_of_sale.sale_details_report').report_action([], data=data)
