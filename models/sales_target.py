from odoo import models, fields, api, _


class SalesTarget(models.Model):
    _name = 'sales.target'
    _description = 'Sales Target'
    _order = 'create_date desc'
    _rec_name = 'target_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Code", readonly=True, default=lambda self: _("Draft"))
    target_name = fields.Char(string='Target Name', related='target_setup_id.sales_target_name', store=True)
    salesperson_id = fields.Many2one('res.users', string="Salesperson", required=True)
    manager_id = fields.Many2one('hr.employee', string="Manager", related='salesperson_id.employee_id.parent_id',
                                 store=True)
    geo_id = fields.Many2one('area.upazila', string="Geo ID", related='salesperson_id.employee_id.upazila_name',
                             store=True)
    company = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    sub_business = fields.Many2many('sub.business', string="Sub Business",
                                    related='salesperson_id.employee_id.business')
    target_amount = fields.Float(string='Target Amount', required=True)
    start_date = fields.Date(string='Start Date', related='target_setup_id.start_date', store=True)
    end_date = fields.Date(string='End Date', related='target_setup_id.end_date', store=True)
    state = fields.Selection(related='target_setup_id.state', string="State")
    target_point = fields.Selection(
        [('so_confirm', 'On Sale Order Confirmed'),
         ('invoice_valid', 'On Invoice Validation'),
         ('invoice_paid', 'On Invoice Paid')],
        string="Target Point", tracking=True, required=True, default='so_confirm', readonly=True)
    target_setup_id = fields.Many2one('target.setup', string="Target Setup ID")
    difference_amount = fields.Float(string="Difference", compute='_compute_difference_amount', store=True)
    achievement_progress = fields.Float(string='Achievement Progress (%)', compute='_compute_achievement', store=True)
    achievement_state = fields.Selection([
        ('progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string="Achievement Status", compute='_compute_achievement', store=True)
    total_sales = fields.Float(string='Total Sales', compute='_compute_total_sales', store=True)
    sale_order_ids = fields.One2many('sale.order', 'sales_target_id', string="Sales Orders",
                                     compute='_compute_sale_orders', store=False)

    @api.model
    def create(self, vals):
        records = super(SalesTarget, self).create(vals)
        for record in records:
            record.name = self.env['ir.sequence'].next_by_code('sales.target')
        return records

    @api.depends('salesperson_id', 'start_date', 'end_date')
    def _compute_sale_orders(self):
        for record in self:
            if record.salesperson_id and record.start_date and record.end_date:
                sales_orders = self.env['sale.order'].search([
                    ('user_id', '=', record.salesperson_id.id),
                    ('date_order', '>=', record.start_date),
                    ('date_order', '<=', record.end_date),
                    ('state', 'in', ['sale', 'done']),
                ])
                record.sale_order_ids = sales_orders
            else:
                record.sale_order_ids = False

    @api.depends('salesperson_id', 'start_date', 'end_date')
    def _compute_total_sales(self):
        for record in self:
            sales_orders = self.env['sale.order'].search([
                ('user_id', '=', record.salesperson_id.id),
                ('date_order', '>=', record.start_date),
                ('date_order', '<=', record.end_date),
                ('state', 'in', ['sale', 'done']),
            ])
            record.total_sales = sum(sales_orders.mapped('amount_total'))

    @api.depends('target_amount', 'total_sales')
    def _compute_difference_amount(self):
        for record in self:
            record.difference_amount = (record.target_amount or 0.0) - (record.total_sales or 0.0)

    @api.depends('total_sales', 'target_amount')
    def _compute_achievement(self):
        for record in self:
            if record.target_amount:
                record.achievement_progress = (record.total_sales / record.target_amount) * 100
            else:
                record.achievement_progress = 0
            current_date = fields.Date.today()
            if record.end_date and current_date <= record.end_date:
                record.achievement_state = 'completed' if record.achievement_progress >= 100 else 'progress'
            elif record.end_date and current_date > record.end_date:
                record.achievement_state = 'completed' if record.achievement_progress >= 100 else 'failed'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sales_target_id = fields.Many2one('sales.target', string="Sales Target")

    @api.model
    def write(self, values):
        res = super(SaleOrder, self).write(values)
        if 'state' in values and values['state'] in ['sale', 'done']:
            for order in self:
                if order.user_id:
                    sales_targets = self.env['sales.target'].search([
                        ('salesperson_id', '=', order.user_id.id),
                        ('start_date', '<=', order.date_order),
                        ('end_date', '>=', order.date_order),
                    ])
                    for target in sales_targets:
                        target._compute_total_sales()

        return res
