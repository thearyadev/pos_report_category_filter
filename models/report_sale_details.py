from collections import defaultdict

from odoo import models, api


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    def _get_hourly_sales(self, date_start, date_stop, config_ids, session_ids, excluded_category_names, **kwargs):
        """Calculate hourly sales breakdown, excluding non-revenue categories."""
        domain = self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs)
        orders = self.env['pos.order'].search(domain)

        # Get user timezone for proper hour grouping
        user_tz = self.env.context.get('tz') or self.env.user.tz or 'UTC'

        hourly_data = defaultdict(lambda: {'total': 0.0, 'orders': 0, 'items': 0})

        for order in orders:
            # Convert to user timezone for hour extraction
            order_date = order.date_order
            if order_date:
                import pytz
                utc_dt = pytz.UTC.localize(order_date)
                local_dt = utc_dt.astimezone(pytz.timezone(user_tz))
                hour = local_dt.hour

                # Calculate order total excluding non-revenue items
                order_total = 0.0
                order_items = 0
                for line in order.lines:
                    if line.qty >= 0:  # Exclude refunds
                        # Check if product's POS category is excluded
                        pos_categ_names = line.product_id.pos_categ_ids.mapped('name')
                        is_excluded = bool(set(pos_categ_names) & excluded_category_names)

                        if not is_excluded:
                            order_total += line.price_subtotal
                            order_items += line.qty

                if order_total != 0 or order_items != 0:
                    hourly_data[hour]['total'] += order_total
                    hourly_data[hour]['orders'] += 1
                    hourly_data[hour]['items'] += order_items

        # Convert to sorted list with formatted hour labels
        hourly_sales = []
        for hour in sorted(hourly_data.keys()):
            data = hourly_data[hour]
            # Format hour as 12-hour with AM/PM
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
                'items': int(data['items']),
            })

        return hourly_sales

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        """Override to separate excluded POS category products from main sales."""
        # Get the standard report data first
        data = super().get_sale_details(
            date_start=date_start,
            date_stop=date_stop,
            config_ids=config_ids,
            session_ids=session_ids,
            **kwargs
        )

        # Products is a list of category dictionaries:
        # [{'name': 'Category Name', 'products': [...], 'total': x, 'qty': y}, ...]
        products = data.get('products', [])

        # Get all POS categories that are marked for exclusion
        excluded_category_names = set(
            self.env['pos.category'].search([
                ('exclude_from_report_turnover', '=', True)
            ]).mapped('name')
        )

        regular_categories = []
        excluded_aggregated = {}  # Dict to aggregate by POS category name
        excluded_total = 0.0

        for category_dict in products:
            category_name = category_dict.get('name', '')

            if category_name in excluded_category_names:
                # This entire category is excluded - aggregate by category name
                for product_line in category_dict.get('products', []):
                    base_amount = product_line.get('base_amount', 0.0)
                    quantity = product_line.get('quantity', 0)

                    if category_name in excluded_aggregated:
                        excluded_aggregated[category_name]['quantity'] += quantity
                        excluded_aggregated[category_name]['base_amount'] += base_amount
                    else:
                        excluded_aggregated[category_name] = {
                            'product_name': category_name,  # Use category name as display name
                            'quantity': quantity,
                            'base_amount': base_amount,
                        }
                    excluded_total += base_amount
            else:
                # Keep this category in regular sales
                regular_categories.append(category_dict)

        # Convert aggregated dict to sorted list
        excluded_products = sorted(excluded_aggregated.values(), key=lambda x: x['product_name'])

        # Recalculate products_info for regular categories only
        all_qty = 0
        all_total = 0
        for category_dict in regular_categories:
            for product in category_dict.get('products', []):
                all_qty += product.get('quantity', 0)
                all_total += product.get('base_amount', 0.0)

        # Adjust the "No Taxes" entry in taxes list to exclude non-revenue items
        # The "No Taxes" entry has tax_amount of 0.0 (no actual tax collected)
        taxes = data.get('taxes', [])
        for tax in taxes:
            if tax.get('tax_amount', -1) == 0.0:
                tax['base_amount'] = tax.get('base_amount', 0.0) - excluded_total
                break

        # Recalculate taxes_info
        taxes_info = data.get('taxes_info', {})
        taxes_info['base_amount'] = taxes_info.get('base_amount', 0.0) - excluded_total

        # Calculate hourly sales breakdown
        hourly_sales = self._get_hourly_sales(
            date_start, date_stop, config_ids, session_ids,
            excluded_category_names, **kwargs
        )

        # Update the data with filtered products and adjusted totals
        data['products'] = regular_categories
        data['products_info'] = {'total': all_total, 'qty': all_qty}
        data['excluded_ops'] = excluded_products
        data['excluded_total'] = excluded_total
        data['taxes'] = taxes
        data['taxes_info'] = taxes_info
        data['hourly_sales'] = hourly_sales

        return data
