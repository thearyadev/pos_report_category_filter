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
        # Also handle "Not Categorized" if needed
        uncategorized_label = _('Not Categorized')

        regular_categories = []
        excluded_products = []  # Flat list of all excluded product lines
        excluded_total = 0.0

        for category_dict in products:
            category_name = category_dict.get('name', '')

            if category_name in excluded_category_names:
                # This entire category is excluded - add all its products to excluded list
                for product_line in category_dict.get('products', []):
                    excluded_products.append(product_line)
                    excluded_total += product_line.get('base_amount', 0.0)
            else:
                # Keep this category in regular sales
                regular_categories.append(category_dict)

        # Recalculate products_info for regular categories only
        all_qty = 0
        all_total = 0
        for category_dict in regular_categories:
            for product in category_dict.get('products', []):
                all_qty += product.get('quantity', 0)
                all_total += product.get('base_amount', 0.0)

        # Update the data with filtered products
        data['products'] = regular_categories
        data['products_info'] = {'total': all_total, 'qty': all_qty}
        data['excluded_ops'] = excluded_products
        data['excluded_total'] = excluded_total

        return data
