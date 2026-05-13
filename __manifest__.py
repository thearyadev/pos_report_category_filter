{
    'name': 'POS Report Category Filter',
    'version': '18.0.1.0.1',
    'category': 'Point of Sale',
    'summary': 'Separate POS non-revenue activity from sales and tax reporting',
    'description': """
        This module allows you to mark POS categories (e.g., Lotto payouts, Bottle Deposits)
        as non-revenue clearing activity in POS reports.

        These items appear separately from merchandise sales and tax totals while payment
        and session-control totals continue to show actual cash movement.
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_category_views.xml',
        'views/pos_details_views.xml',
        'views/pos_order_report_views.xml',
        'views/report_saledetails.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
