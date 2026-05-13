from collections import defaultdict
import pytz

from odoo import models, api, _


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    def _get_sale_details_kwargs(self, kwargs):
        """Keep addon-only flags out of Odoo's report domain methods."""
        return {key: value for key, value in kwargs.items() if key != 'apply_non_revenue_filter'}

    def _get_report_pos_category(self, line):
        """Match Odoo's Sales Details grouping: the first POS category on the template."""
        return line.product_id.product_tmpl_id.pos_categ_ids[:1]

    def _is_non_revenue_line(self, line, excluded_category_ids):
        category = self._get_report_pos_category(line)
        return bool(category and category.id in excluded_category_ids)

    def _get_orders_for_sale_details(self, date_start, date_stop, config_ids, session_ids, **kwargs):
        domain = self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs)
        return self.env['pos.order'].search(domain)

    def _build_category_list(self, products_by_category):
        categories = []
        for category_name, product_list in products_by_category.items():
            categories.append({
                'name': category_name,
                'products': sorted([{
                    'product_id': product.id,
                    'product_name': product.name,
                    'code': product.default_code,
                    'quantity': qty,
                    'price_unit': price_unit,
                    'discount': discount,
                    'uom': product.uom_id.name,
                    'total_paid': product_total,
                    'base_amount': base_amount,
                } for (product, price_unit, discount), (qty, product_total, base_amount) in product_list.items()], key=lambda line: line['product_name']),
            })
        return sorted(categories, key=lambda category: str(category['name']))

    def _aggregate_non_revenue_line(self, line, excluded_aggregated):
        category = self._get_report_pos_category(line)
        category_name = category.display_name if category else _('Not Categorized')
        key = category.id if category else 0
        values = excluded_aggregated.setdefault(key, {
            'product_name': category_name,
            'quantity': 0.0,
            'base_amount': 0.0,
            'tax_amount': 0.0,
            'total_amount': 0.0,
        })
        values['quantity'] += line.qty
        values['base_amount'] += line.price_subtotal
        values['tax_amount'] += line.price_subtotal_incl - line.price_subtotal
        values['total_amount'] += line.price_subtotal_incl

    def _get_hourly_sales(self, orders, excluded_category_ids):
        """Calculate hourly sales breakdown, excluding non-revenue categories."""
        user_tz = self.env.context.get('tz') or self.env.user.tz or 'UTC'
        timezone = pytz.timezone(user_tz)

        hourly_data = defaultdict(lambda: {'total': 0.0, 'orders': 0, 'items': 0})

        for order in orders:
            if not order.date_order:
                continue

            local_dt = pytz.UTC.localize(order.date_order).astimezone(timezone)
            hour = local_dt.hour
            order_total = 0.0
            order_items = 0.0
            for line in order.lines.filtered(lambda order_line: order_line.qty >= 0):
                if self._is_non_revenue_line(line, excluded_category_ids):
                    continue
                order_total += line.price_subtotal
                order_items += line.qty

            if order_total or order_items:
                hourly_data[hour]['total'] += order_total
                hourly_data[hour]['orders'] += 1
                hourly_data[hour]['items'] += order_items

        hourly_sales = []
        for hour in sorted(hourly_data.keys()):
            data = hourly_data[hour]
            if hour == 0:
                hour_label = "12 AM"
            elif hour < 12:
                hour_label = f"{hour} AM"
            elif hour == 12:
                hour_label = "12 PM"
            else:
                hour_label = f"{hour - 12} PM"

            hourly_sales.append({
                'hour': hour_label,
                'total': data['total'],
                'orders': data['orders'],
                'items': data['items'],
            })

        return hourly_sales

    def _set_non_revenue_defaults(self, data, applied):
        data.setdefault('excluded_ops', [])
        data.setdefault('excluded_total', 0.0)
        data.setdefault('excluded_base_total', 0.0)
        data.setdefault('excluded_tax_total', 0.0)
        data.setdefault('hourly_sales', [])
        data.setdefault('non_revenue_summary', {})
        data['non_revenue_filter_applied'] = applied
        return data

    def _prepare_get_sale_details_args_kwargs(self, data):
        args, kwargs = super()._prepare_get_sale_details_args_kwargs(data)
        if 'apply_non_revenue_filter' in data:
            kwargs['apply_non_revenue_filter'] = data['apply_non_revenue_filter']
        return args, kwargs

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        """Separate non-revenue categories from sales without patching aggregate totals."""
        domain_kwargs = self._get_sale_details_kwargs(kwargs)
        data = super().get_sale_details(
            date_start=date_start,
            date_stop=date_stop,
            config_ids=config_ids,
            session_ids=session_ids,
            **domain_kwargs
        )

        if not kwargs.get('apply_non_revenue_filter', True):
            return self._set_non_revenue_defaults(data, applied=False)

        excluded_categories = self.env['pos.category'].search([('exclude_from_report_turnover', '=', True)])
        excluded_category_ids = set(excluded_categories.ids)
        orders = self._get_orders_for_sale_details(date_start, date_stop, config_ids, session_ids, **domain_kwargs)

        products_sold = {}
        taxes = {'base_amount': 0.0, 'taxes': {}}
        refund_done = {}
        refund_taxes = {'base_amount': 0.0, 'taxes': {}}
        excluded_aggregated = {}

        for order in orders:
            currency = order.session_id.currency_id
            for line in order.lines:
                if self._is_non_revenue_line(line, excluded_category_ids):
                    self._aggregate_non_revenue_line(line, excluded_aggregated)
                elif line.qty >= 0:
                    products_sold, taxes = self._get_products_and_taxes_dict(line, products_sold, taxes, currency)
                else:
                    refund_done, refund_taxes = self._get_products_and_taxes_dict(line, refund_done, refund_taxes, currency)

        products = self._build_category_list(products_sold)
        refund_products = self._build_category_list(refund_done)
        configs = self.env['pos.config'].browse(config_ids or [])
        if not configs and session_ids:
            configs = self.env['pos.session'].browse(session_ids).mapped('config_id')
        context_config_id = configs[0].id if configs else False
        products, products_info = self.with_context(config_id=context_config_id)._get_total_and_qty_per_category(products)
        refund_products, refund_info = self.with_context(config_id=context_config_id)._get_total_and_qty_per_category(refund_products)

        excluded_products = sorted(excluded_aggregated.values(), key=lambda line: line['product_name'])
        excluded_base_total = sum(line['base_amount'] for line in excluded_products)
        excluded_tax_total = sum(line['tax_amount'] for line in excluded_products)
        excluded_total = sum(line['total_amount'] for line in excluded_products)
        taxes_info = self._get_taxes_info(taxes)
        refund_taxes_info = self._get_taxes_info(refund_taxes)

        data['products'] = products
        data['products_info'] = products_info
        data['taxes'] = list(taxes['taxes'].values())
        data['taxes_info'] = taxes_info
        data['refund_products'] = refund_products
        data['refund_info'] = refund_info
        data['refund_taxes'] = list(refund_taxes['taxes'].values())
        data['refund_taxes_info'] = refund_taxes_info
        data['excluded_ops'] = excluded_products
        data['excluded_total'] = excluded_total
        data['excluded_base_total'] = excluded_base_total
        data['excluded_tax_total'] = excluded_tax_total
        data['hourly_sales'] = self._get_hourly_sales(orders, excluded_category_ids)
        data['non_revenue_summary'] = {
            'sales_base': taxes_info['base_amount'],
            'sales_tax': taxes_info['tax_amount'],
            'sales_total': taxes_info['base_amount'] + taxes_info['tax_amount'],
            'refund_base': refund_taxes_info['base_amount'],
            'refund_tax': refund_taxes_info['tax_amount'],
            'refund_total': refund_taxes_info['base_amount'] + refund_taxes_info['tax_amount'],
            'non_revenue_base': excluded_base_total,
            'non_revenue_tax': excluded_tax_total,
            'non_revenue_total': excluded_total,
            'payment_movement_total': data['currency']['total_paid'],
        }

        return self._set_non_revenue_defaults(data, applied=True)
