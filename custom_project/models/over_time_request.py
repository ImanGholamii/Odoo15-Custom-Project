from odoo import models, fields, api, _


class OvertimeRequest(models.Model):
    _name = "overtime.request"
    _description = "Overtime Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('res.users', string="Employee", required=True, tracking=True,
                                  default=lambda self: self.env.user,
                                  readonly=True)
    request_date = fields.Datetime(string="Request Date", default=lambda self: fields.Datetime.now(), required=True,
                                   tracking=True,
                                   readonly=True)
    overtime_hours = fields.Float(string="Overtime Hours", required=True)
    project_id = fields.Many2one('project.project', string="Related Project")
    task_id = fields.Many2one('project.task', string="Related Task", required=True, readonly=True)

    project_manager_id = fields.Many2one('res.users', string="Project Manager")
    technical_director_id = fields.Many2one('res.users', string="Technical Director")

    description = fields.Text(string="Description")

    @api.model
    def create(self, vals):
        current_user = self.env.user.id
        vals['employee_id'] = current_user

        record = super().create(vals)

        if record.project_manager_id and record.project_manager_id.partner_id:
            task_id = vals.get('task_id')
            link_url = f"{self.get_base_url()}/web#id={task_id}&model=project.task&view_type=form"

            email_subject = "Overtime Request Assigned"
            email_body = f"""
                <div style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                    <h2 style="color: #d9534f; text-align: center;">🕖 Overtime Request Notification</h2>
                    <p style="font-size: 14px; color: #333;">This message is from <strong>Odoo System</strong></p>
                    <p style="font-size: 16px; font-weight: bold; color: #0275d8;">An overtime request has been assigned to you for review.</p>
                    <p style="font-size: 14px; color: #333;">Employee: <strong>{record.employee_id.name}</strong></p>
                    <p style="font-size: 14px; color: #333;">Date: <strong>{record.request_date}</strong></p>

                    <p style="text-align: center;">
                        <a href='{link_url}' style="display: inline-block; padding: 10px 20px; background-color: #0275d8; color: white; 
                        text-decoration: none; border-radius: 5px; font-weight: bold;">📂 View Task</a>
                    </p>

                    <hr style="background-color: red; height: 3px; border: none;">

                    <p style="color: #555; font-size: 12px; text-align: center;">
                        This message is <strong>strictly confidential</strong> and intended for you only. If you made these changes, you can ignore this message.
                    </p>

                    <p style="color: #999; font-size: 12px; text-align: center;">
                        © Odoo System | Auto-generated Notification
                    </p>
                </div>
            """

            mail_values = {
                'subject': email_subject,
                'body_html': email_body,
                'email_to': record.project_manager_id.partner_id.email,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

        return record
