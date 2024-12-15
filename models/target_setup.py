import base64
import io
from email.policy import default

import xlsxwriter

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class TargetSetup(models.Model):
    _name = 'target.setup'
    _description = 'Set Sales Target for Sales Person'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char(string="Name", readonly=True, default=lambda self: _("Draft"))
    sales_target_name = fields.Char(string="Sales Target")
    company = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    sub_business = fields.Many2one(
        'sub.business',
        string="Sub Business",
    )
    start_date = fields.Date(string="Start Date", tracking=True, required=True)
    end_date = fields.Date(string="End Date", tracking=True, required=True)
    target_unit = fields.Selection(
        [('value', 'Total Amount'), ('product_value', 'Product Wise Amount'), ('qty', 'Product Wise Quantity')],
        required=True, string="Target Unit", default='value')
    sales_target_ids = fields.One2many('sales.target', 'target_setup_id')
    target_point = fields.Selection(
        [('so_confirm', 'On Sale Order Confirmed'),
         ('invoice_valid', 'On Invoice Validation'),
         ('invoice_paid', 'On Invoice Paid')],
        string="Target Point", tracking=True, required=True, default='so_confirm')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'), ('open', 'Open'), ('close', 'Lock'), ('cancel', 'Cancel')],
        default='draft', string="State", tracking=True)

    @api.model
    def create(self, vals):
        records = super(TargetSetup, self).create(vals)
        for record in records:
            record.name = self.env['ir.sequence'].next_by_code('target.setup')
        return records

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise UserError("Start date cannot be after end date")

    def action_target_export(self):
        if not self.sales_target_ids:
            raise UserError("There are no sales target lines to export.")
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Sales Target')
        header_format = workbook.add_format({
            'bold': True,
            'valign': 'vcenter',
            'bg_color': '#D3D3D3',
            'font_name': 'Arial',
            'font_size': 10
        })
        cell_format = workbook.add_format({
            'font_name': 'Arial',
            'valign': 'vcenter',
            'font_size': 10
        })
        headers = ['Target ID', 'Company', 'Business', 'Target Setup Code', 'Geo ID', 'Geo Name', 'Salesperson',
                   'Manager', 'Start Date',
                   'End Date', 'Target Unit', 'Target Point', 'Target Amount']
        col_widths = [len(header) for header in headers]
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)
        row = 1
        for line in self.sales_target_ids:
            data = [
                line.name or '',
                line.company.name or '',
                line.sub_business.name or '',
                line.target_setup_id.name or '',
                line.geo_id.upazila_code or '',
                line.geo_id.upazila_name or '',
                line.salesperson_id.name or '',
                line.manager_id.name or '',
                self.start_date.strftime('%Y-%m-%d') if self.start_date else '',
                self.end_date.strftime('%Y-%m-%d') if self.end_date else '',
                dict(self._fields['target_unit'].selection).get(self.target_unit, ''),
                dict(self._fields['target_point'].selection).get(self.target_point, ''),
            ]
            for col_num, cell_value in enumerate(data):
                worksheet.write(row, col_num, cell_value, cell_format)
                col_widths[col_num] = max(col_widths[col_num], len(str(cell_value)))
            row += 1
        for col_num, col_width in enumerate(col_widths):
            worksheet.set_column(col_num, col_num, col_width + 2)
        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()
        export_file = base64.b64encode(file_data)
        attachment = self.env['ir.attachment'].create({
            'name': f'Target_Setup_{self.name}.xlsx',
            'type': 'binary',
            'datas': export_file,
            'store_fname': f'Sales_Target_{self.name}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_target_import(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Import Sales Target Lines",
            "res_model": "import.target.set.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_sale_target_id": self.id},
        }
