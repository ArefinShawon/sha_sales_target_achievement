import base64
import io
import xlrd
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ImportTargetSetWizard(models.TransientModel):
    _name = 'import.target.set.wizard'
    _description = 'Import Sales Target Set Wizard'

    sale_target_id = fields.Many2one("target.setup", string="Target Set", default=lambda self: self._default_st_id())
    import_file = fields.Binary("Upload XLSX")

    @api.model
    def _default_st_id(self):
        return self.env.context.get('active_id') if self.env.context.get('active_model') == 'target.setup' else None

    def import_stl_xlsx_file(self):
        if not self.import_file:
            raise UserError(_("No XLSX file is uploaded! Please upload an XLSX file to import.\n"))

        try:
            inputx = io.BytesIO(base64.decodebytes(self.import_file))
            workbook = xlrd.open_workbook(file_contents=inputx.getvalue())
            sheet = workbook.sheet_by_index(0)
            headers = sheet.row_values(0)

            # Validate headers
            required_columns = ['Target ID', 'Target Amount']
            missing_columns = [col for col in required_columns if col not in headers]
            if missing_columns:
                raise UserError(_("Uploaded file is missing required columns: {}\n").format(", ".join(missing_columns)))

            # Get column indices
            stl_id_index = headers.index('Target ID')
            target_amount_index = headers.index('Target Amount')

            error_messages = []  # To store errors
            successful_updates = 0

            # Iterate through rows
            for row_num in range(1, sheet.nrows):  # Skip the header row
                row = sheet.row_values(row_num)
                stl_id = row[stl_id_index]
                target_amount = row[target_amount_index] if len(row) > target_amount_index else None

                # Validate STL ID
                if not stl_id or not isinstance(stl_id, str):
                    error_messages.append(f"Row {row_num + 1}: Missing or invalid STL ID.\n")
                    continue

                sales_target_line = self.env['sales.target'].search([('name', '=', stl_id)], limit=1)
                if not sales_target_line:
                    error_messages.append(f"Row {row_num + 1}: STL ID '{stl_id}' not found.\n")
                    continue

                # Validate Target Amount
                if target_amount is None or target_amount == '':
                    error_messages.append(f"Row {row_num + 1}: Missing Target Amount value.\n")
                    continue

                try:
                    target_amount = float(target_amount)
                    if target_amount < 0:
                        error_messages.append(f"Row {row_num + 1}: Target Amount cannot be negative.\n")
                        continue
                except ValueError:
                    error_messages.append(f"Row {row_num + 1}: Invalid Target Amount value '{target_amount}'.\n")
                    continue

                # Update Target Amount
                sales_target_line.target_amount = target_amount
                successful_updates += 1

            if error_messages:
                error_message_html = _("Errors detected during import:\n{}").format(
                    "".join([f"{msg}" for msg in error_messages])
                )
                raise UserError(error_message_html)

            if successful_updates == 0:
                raise UserError(_("No valid sales target lines were updated. Please check your file."))

        except Exception as e:
            raise UserError(_("Error processing file: {}".format(e)))
