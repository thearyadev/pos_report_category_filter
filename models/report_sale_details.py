from odoo import models, api, _


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

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
        taxes = data.get('taxes', [])
        for tax in taxes:
            if tax.get('name') == _('No Taxes'):
                tax['base_amount'] = tax.get('base_amount', 0.0) - excluded_total
                break

        # Recalculate taxes_info
        taxes_info = data.get('taxes_info', {})
        taxes_info['base_amount'] = taxes_info.get('base_amount', 0.0) - excluded_total

        # Adjust total_paid in currency
        currency = data.get('currency', {})
        original_total_paid = currency.get('total_paid', 0.0)
        currency['total_paid'] = original_total_paid - excluded_total

        # Adjust payments totals
        payments = data.get('payments', [])
        # Find the cash payment method and adjust its total
        # Non-revenue items are typically handled in cash
        for payment in payments:
            if payment.get('cash', False):
                payment['total'] = payment.get('total', 0.0) - excluded_total
                if 'final_count' in payment:
                    payment['final_count'] = payment.get('final_count', 0.0) - excluded_total
                break

        # Update the data with filtered products and adjusted totals
        data['products'] = regular_categories
        data['products_info'] = {'total': all_total, 'qty': all_qty}
        data['excluded_ops'] = excluded_products
        data['excluded_total'] = excluded_total
        data['taxes'] = taxes
        data['taxes_info'] = taxes_info
        data['currency'] = currency
        data['payments'] = payments

        return data
