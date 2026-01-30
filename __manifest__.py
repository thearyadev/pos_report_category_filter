{
    'name': 'POS Report Category Filter',
    'version': '18.0.1.0.1',
    'category': 'Point of Sale',
    'summary': 'Exclude specific POS categories from POS Z-Report sales totals',
    'description': """
        This module allows you to mark POS categories (e.g., Lotto, Bottle Deposits)
        to be excluded from the main sales figures in the POS Z-Report.

        These items will appear in a separate "Payouts & Adjustments" section,
        keeping your actual merchandise sales figures clean and accurate.
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_category_views.xml',
        'views/report_saledetails.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
