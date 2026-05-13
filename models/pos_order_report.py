from odoo import fields, models


class PosOrderReport(models.Model):
    _inherit = 'report.pos.order'

    is_non_revenue = fields.Boolean(string="Non-Revenue", readonly=True)
    revenue_price_total = fields.Float(string="Revenue Total", readonly=True)
    non_revenue_price_total = fields.Float(string="Non-Revenue Total", readonly=True)
    revenue_price_subtotal_excl = fields.Float(string="Revenue Subtotal w/o Tax", readonly=True)
    non_revenue_price_subtotal_excl = fields.Float(string="Non-Revenue Subtotal w/o Tax", readonly=True)
    revenue_product_qty = fields.Float(string="Revenue Quantity", readonly=True)
    non_revenue_product_qty = fields.Float(string="Non-Revenue Quantity", readonly=True)

    def _select(self):
        select = super()._select()
        select = select.replace(
            "(array_agg(pc.id))[1] AS id",
            "(array_agg(pc.id))[1] AS id,\n"
            "                    COALESCE((array_agg(pc.exclude_from_report_turnover))[1], FALSE) AS exclude_from_report_turnover"
        )
        return select.replace(
            "fpc.id AS pos_categ_id",
            "fpc.id AS pos_categ_id,\n"
            "                COALESCE(fpc.exclude_from_report_turnover, FALSE) AS is_non_revenue,\n"
            "                CASE WHEN COALESCE(fpc.exclude_from_report_turnover, FALSE) THEN 0 "
            "ELSE ROUND((l.price_subtotal_incl) / COALESCE(NULLIF(s.currency_rate, 0), 1.0), cu.decimal_places) END AS revenue_price_total,\n"
            "                CASE WHEN COALESCE(fpc.exclude_from_report_turnover, FALSE) "
            "THEN ROUND((l.price_subtotal_incl) / COALESCE(NULLIF(s.currency_rate, 0), 1.0), cu.decimal_places) ELSE 0 END AS non_revenue_price_total,\n"
            "                CASE WHEN COALESCE(fpc.exclude_from_report_turnover, FALSE) THEN 0 "
            "ELSE ROUND((l.price_subtotal) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END, cu.decimal_places) END AS revenue_price_subtotal_excl,\n"
            "                CASE WHEN COALESCE(fpc.exclude_from_report_turnover, FALSE) "
            "THEN ROUND((l.price_subtotal) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END, cu.decimal_places) ELSE 0 END AS non_revenue_price_subtotal_excl,\n"
            "                CASE WHEN COALESCE(fpc.exclude_from_report_turnover, FALSE) THEN 0 ELSE l.qty END AS revenue_product_qty,\n"
            "                CASE WHEN COALESCE(fpc.exclude_from_report_turnover, FALSE) THEN l.qty ELSE 0 END AS non_revenue_product_qty"
        )
