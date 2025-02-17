from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError


class CustomProjectTask(models.Model):
    _inherit = 'project.task'

    planned_hours = fields.Float("Initially Planned Hours",
                                 help='Time planned to achieve this task (including its sub-tasks).',
                                 tracking=True)

    def _compute_planned_hours_readonly(self):
        for task in self:
            task.planned_hours_readonly = task.create_uid != self.env.user

    planned_hours_readonly = fields.Boolean(compute="_compute_planned_hours_readonly")

    @api.model
    def create(self, vals):
        if 'planned_hours' not in vals or not vals['planned_hours']:
            raise ValidationError(
                "Please to define new Tasks, First Set the Initially Planned Hours(notebook: Timesheet >> Initially Planned Hours)")

        task = super(CustomProjectTask, self).create(vals)

        if 'project_id' in vals:
            project = self.env['project.project'].browse(vals['project_id'])
            # total_task_hours = sum(task.planned_hours for task in project.task_ids)
            total_task_hours = sum(project.task_ids.mapped('planned_hours'))
            # new_task_hours = vals.get('planned_hours', 0)
            # if total_task_hours + new_task_hours > project.allocated_hours:
            print(f"total_task_hours: {total_task_hours}\nallocated_hours:{project.allocated_hours}")

            if total_task_hours > project.allocated_hours:
                allocated_hours_int = int(project.allocated_hours)
                allocated_minutes = int((project.allocated_hours - allocated_hours_int) * 60)
                allocated_time_str = f"{allocated_hours_int:02d}:{allocated_minutes:02d}"
                raise ValidationError(
                    f"The total planned hours for tasks in this project exceed the allocated limit of {allocated_time_str} hours."
                )
        return task

    # After Meeting
    # Allocated Hours to Employees
    allocation_ids = fields.One2many(
        'project.task.allocation',
        'task_id',
        string="Employee Allocations",
        help="Distribute the planned hours among the assigned employees."
    )

    # 4 Feb

    allocated_hours_current_employee = fields.Float(
        string="Your Allocated Hours",
        compute="_compute_allocated_hours",
        store=False
    )

    @api.depends('allocation_ids.allocated_hours', 'allocation_ids.employee_id')
    def _compute_allocated_hours(self):
        user = self.env.user
        employee = self.env['res.users'].search([('user_ids', '=', user.id)], limit=1)

        for task in self:
            if employee:
                allocation = task.allocation_ids.filtered(lambda a: a.employee_id == employee)
                task.allocated_hours_current_employee = sum(allocation.mapped('allocated_hours'))
            else:
                task.allocated_hours_current_employee = 0.0

    # Feb 17
    total_project_hours = fields.Float(
        string="Total Project Hours",
        readonly=True,
        compute="_compute_total_project_hours",
        help="Total allocated hours for this project, defined by the Technical Director."
    )

    @api.depends('project_id')
    def _compute_total_project_hours(self):
        for task in self:
            task.total_project_hours = task.project_id.allocated_hours if task.project_id else 0.0


class CustomProjectProject(models.Model):
    _inherit = 'project.project'

    user_id = fields.Many2one(
        'res.users', string='Project Manager',
        default=lambda self: self.env.user,
        tracking=True
    )

    technical_director_id = fields.Many2one(
        'res.users',
        string="Technical Director",
        required=True,
        help="Responsible for defining the project and assigning the Project Manager."
    )

    allocated_hours = fields.Float(
        string="Allocated Hours",
        required=True,
        help="Maximum allowed hours for tasks in this project."
    )

    @api.constrains('technical_director_id')
    def _check_technical_director(self):
        if not self.technical_director_id:
            raise ValidationError("Technical Director is required to create a project.")

    @api.constrains('user_id')
    def _check_project_manager(self):
        for record in self:
            if not record.user_id:
                raise ValidationError(
                    "The Project Manager must be selected by the Technical Director or Administrator.")

    @api.model
    def create(self, vals):
        if 'project_id' in vals:
            project = self.env['project.project'].browse(vals['project_id'])
            if project.user_id.id != self.env.user.id:
                raise AccessError("Only the Project Manager can create tasks for this project.")

        project = super(CustomProjectProject, self).create(vals)
        if 'technical_director_id' in vals:
            user = self.env['res.users'].browse(vals['technical_director_id'])
            group = self.env.ref('custom_project.group_technical_director')
            if user and group and user not in group.users:
                group.users = [(4, user.id)]

        return project

    def write(self, vals):
        res = super(CustomProjectProject, self).write(vals)
        if 'technical_director_id' in vals:
            for record in self:
                user = record.env['res.users'].browse(vals['technical_director_id'])
                group = record.env.ref('custom_project.group_technical_director')
                if user and group and user not in group.users:
                    group.users = [(4, user.id)]

        if 'user_id' in vals:
            for record in self:
                project_manager = record.env['res.users'].browse(vals['user_id'])
                group_manager = record.env.ref('custom_project.group_project_manager')
                if project_manager and group_manager and project_manager not in group_manager.users:
                    group_manager.users = [(4, project_manager.id)]

        return res


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    approval_status = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='Approval Status',
        default='draft',
    )

    @api.model
    def create(self, vals):
        task_id = vals.get('task_id')
        if task_id:
            task = self.env['project.task'].browse(task_id)
            if self.env.user not in task.user_ids:
                raise AccessError("You are not assigned to this task.")

            # After Meeting
            # Check an Employee is assigned to task or not
            allocation = task.allocation_ids.filtered(lambda a: a.employee_id == self.env.user)
            if not allocation:
                raise AccessError("You are not allocated to log time for this task.")
            # Calculate the total timesheet hours recorded for this user on this task.
            timesheet_lines = self.search([
                ('task_id', '=', task_id),
                ('user_id', '=', self.env.user.id)
            ])
            total_logged = sum(timesheet_lines.mapped('unit_amount'))
            new_hours = vals.get('unit_amount', 0)
            if total_logged + new_hours > allocation.allocated_hours:
                raise ValidationError("You cannot log more time than allocated for this task.")

        return super(AccountAnalyticLine, self).create(vals)

    def write(self, vals):
        task_id = vals.get('task_id')
        if task_id:
            task = self.env['project.task'].browse(task_id)
            if self.env.user not in task.user_ids:
                raise AccessError("You are not assigned to this task. So couldn't edit this Task.")

        # After Meeting
        for line in self:
            task = line.task_id
            if task:
                allocation = task.allocation_ids.filtered(lambda a: a.employee_id == self.env.user)
                if not allocation:
                    raise AccessError("You are not allocated to log time for this task.")
                # Calculate the total timesheet hours recorded except for this line (if the value changes)
                other_lines = self.search([
                    ('id', '!=', line.id),
                    ('task_id', '=', task.id),
                    ('user_id', '=', self.env.user.id)
                ])
                total_logged = sum(other_lines.mapped('unit_amount'))
                new_amount = vals.get('unit_amount', line.unit_amount)
                if total_logged + new_amount > allocation.allocated_hours:
                    raise ValidationError("The updated time exceeds your allocated hours for this task.")

        return super(AccountAnalyticLine, self).write(vals)

    date = fields.Datetime(string="Date and Time", required=True)


# After Meeting

class ProjectTaskAllocation(models.Model):
    _name = 'project.task.allocation'
    _description = 'Allocation of Planned Hours per Employee for a Task'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'res.users',
        string='Employee',
        required=True,
        help="Employee assigned to this task allocation."
    )
    allocated_hours = fields.Float(
        string="Allocated Hours",
        required=True,
        help="Maximum hours this employee is allowed to log for the task.",
        widget="float_time"
    )

    _sql_constraints = [
        # Preventing duplicate assignment of an employee to a task
        ('unique_employee_per_task', 'unique(task_id, employee_id)',
         'Each employee can have only one allocation per task.')
    ]

    @api.constrains('allocated_hours')
    def _check_allocated_hours(self):
        for record in self:
            total_allocated = sum(record.task_id.allocation_ids.mapped('allocated_hours'))
            if total_allocated > record.task_id.planned_hours:
                raise ValidationError("Total allocated hours cannot exceed the planned hours for this task!")
