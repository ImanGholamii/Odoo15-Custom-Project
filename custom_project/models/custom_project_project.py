# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError, UserError
import logging

_logger = logging.getLogger(__name__)


class CustomProjectTask(models.Model):
    _inherit = 'project.task'
    user_id = fields.Many2one('res.users', string='Assigned to', ondelete='set null')

    planned_hours = fields.Float("Initially Planned Hours",
                                 help='Time planned to achieve this task (including its sub-tasks).',
                                 tracking=True)

    planned_hours_readonly = fields.Boolean(compute="_compute_planned_hours_readonly")

    # Mar 03
    child_ids = fields.One2many('project.task', 'parent_id', string="Sub-tasks")

    # end

    # Allocated Hours to Employees
    allocation_ids = fields.One2many(
        'project.task.allocation',
        'task_id',
        string="Employee Allocations",
        help="Distribute the planned hours among the assigned employees."
    )

    allocated_hours_current_employee = fields.Float(
        string="Your Allocated Hours",
        compute="_compute_allocated_hours",
        store=False
    )

    total_project_hours = fields.Float(
        string="Total Project Hours",
        readonly=True,
        compute="_compute_total_project_hours",
        help="Total allocated hours for this project, defined by the Director."
    )

    project_state = fields.Selection(
        related='project_id.state',
        string="Project State",
        readonly=True,
        store=False,
    )

    overtime_request_ids = fields.One2many('overtime.request', 'task_id', string="Overtime Requests")

    # Mar 03
    allocated_hours_total = fields.Float(
        string="Total Allocated Hours",
        compute="_compute_allocated_hours_total",
        store=True
    )
    subtask_hours_total = fields.Float(
        string="Total Subtask Hours",
        compute="_compute_subtask_hours_total",
        store=True
    )
    remaining_hours_for_subtasks = fields.Float(
        string="Remaining Hours for Subtasks",
        compute="_compute_remaining_hours_for_subtasks",
        store=True
    )
    # end
    # Mar 09
    project_id = fields.Many2one('project.project', string='Project')
    user_id = fields.Many2one(
        'res.users', related='project_id.user_id', string='Project Manager', readonly=True)
    technical_director_id = fields.Many2one(
        'res.users', related='project_id.technical_director_id', string='Project Director', readonly=True)
    show_allocation = fields.Boolean(compute='_compute_show_allocation')

    # End
    def _compute_planned_hours_readonly(self):
        for task in self:
            # task.planned_hours_readonly = task.create_uid != self.env.user
            is_admin = self.env.user.has_group("base.group_system")
            task.planned_hours_readonly = not (
                    is_admin or
                    task.create_uid == self.env.user or
                    task.user_id == self.env.user or
                    task.technical_director_id == self.env.user
            )

    @api.model
    def create(self, vals):
        if 'planned_hours' not in vals or not vals['planned_hours']:
            raise ValidationError(
                "Please to define new Tasks, First Set the Task Planned Hours(notebook: Timesheet >> Task Planned Hours)")
        elif 'planned_hours' not in vals or not vals['planned_hours']:
            parent_task = self.browse(vals.get('parent_id'))
            if parent_task:
                vals['planned_hours'] = parent_task.planned_hours

        task = super(CustomProjectTask, self).create(vals)

        if 'project_id' in vals:
            project = self.env['project.project'].browse(vals['project_id'])
            total_task_hours = sum(project.task_ids.mapped('planned_hours'))

            if total_task_hours > project.allocated_hours:
                allocated_hours_int = int(project.allocated_hours)
                allocated_minutes = int((project.allocated_hours - allocated_hours_int) * 60)
                allocated_time_str = f"{allocated_hours_int:02d}:{allocated_minutes:02d}"
                raise ValidationError(
                    f"The total planned hours for tasks in this project exceed the allocated limit of {allocated_time_str} hours."
                )
        if task.subtask_hours_total + task.allocated_hours_total > task.planned_hours:
            raise ValidationError(
                f"Total allocated hours and subtask hours cannot exceed the planned hours for this task!"
            )

        # Mar 05
        return task

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

    @api.depends('project_id')
    def _compute_total_project_hours(self):
        for task in self:
            task.total_project_hours = task.project_id.allocated_hours if task.project_id else 0.0

    @api.constrains('planned_hours', 'child_ids')
    def _check_subtask_hours(self):
        for task in self:
            if task.child_ids:
                total_subtask_hours = sum(task.child_ids.mapped('planned_hours'))
                if total_subtask_hours > task.planned_hours:
                    raise ValidationError(
                        _(f"❌\nThe total planned hours of subtasks cannot exceed the Task Planned Hours of the main task.")
                    )

    def unlink(self):
        """Allow task deletion, bypassing 'mail.followers' restriction"""
        return super(CustomProjectTask, self.with_context(allow_task_delete=True)).unlink()

    @api.depends("allocation_ids.allocated_hours")
    def _compute_allocated_hours_total(self):
        """ Calculation of total allocated_hours """
        for task in self:
            task.allocated_hours_total = sum(task.allocation_ids.mapped("allocated_hours"))

    @api.depends("child_ids.planned_hours")
    def _compute_subtask_hours_total(self):
        """ Calculate the total planned_hours of all subtasksا """
        for task in self:
            task.subtask_hours_total = sum(task.child_ids.mapped("planned_hours"))

    @api.constrains("subtask_hours_total", "allocated_hours_total")
    def _check_task_hours_limit(self):
        """ Checking the limit of total allocated hours and subtasks """
        for task in self:
            if task.subtask_hours_total + task.allocated_hours_total > task.planned_hours:
                raise ValidationError(
                    f"❌\nTotal allocated hours and subtask hours cannot exceed the planned hours for this task!\n"
                )

    def write(self, vals):
        """ Checking restrictions when editing a task """

        res = super().write(vals)
        for task in self:
            if task.subtask_hours_total + task.allocated_hours_total > task.planned_hours:
                raise ValidationError(
                    f"Total allocated hours and subtask hours cannot exceed the planned hours for this task!"
                )
        return res

    @api.depends("planned_hours", "allocated_hours_total", "subtask_hours_total")
    def _compute_remaining_hours_for_subtasks(self):
        """ Calculating the amount of time remaining for subtasks """
        for task in self:
            allocated_and_subtask_hours = task.allocated_hours_total + task.subtask_hours_total
            task.remaining_hours_for_subtasks = max(task.planned_hours - allocated_and_subtask_hours, 0)

    @api.depends('project_id.user_id', 'project_id.technical_director_id')
    def _compute_show_allocation(self):
        for record in self:
            user = self.env.user
            is_admin = user.has_group('base.group_system')

            if (record.project_id.user_id.id == user.id or
                    record.project_id.technical_director_id.id == user.id or
                    is_admin):
                record.show_allocation = True
            else:
                record.show_allocation = False


class CustomProjectProject(models.Model):
    _inherit = 'project.project'

    user_id = fields.Many2one(
        'res.users', string='Project Manager',
        default=lambda self: self.env.user,
        tracking=True
    )

    technical_director_id = fields.Many2one(
        'res.users',
        string="Director",
        required=True,
        help="Responsible for defining the project and assigning the Project Manager."
    )

    allocated_hours = fields.Float(
        string="Allocated Hours",
        required=True,
        help="Maximum allowed hours for tasks in this project."
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string="State", default='draft', tracking=True)

    completed_at = fields.Datetime(string="Completed At", readonly=True)

    # warning_message = fields.Html(string="Warning Message", readonly=True)

    def mark_as_completed(self):
        for project in self:

            if project.technical_director_id and self.env.user == project.technical_director_id or self.env.user.has_group(
                    'base.group_system'):
                project.write({
                    'state': 'completed',
                    'completed_at': fields.Datetime.now()
                })
            else:
                raise AccessError("You do not have the permission to mark this project as completed.")

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_completed(self):
        self.write({
            'state': 'completed',
            'completed_at': fields.Datetime.now()
        })

    @api.constrains('technical_director_id')
    def _check_technical_director(self):
        if not self.technical_director_id:
            raise ValidationError("Director is required to create a project.")

    @api.constrains('user_id')
    def _check_project_manager(self):
        for record in self:
            if not record.user_id:
                raise ValidationError(
                    "The Project Manager must be selected by the Director or Administrator.")

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
            # if user and group and user not in group.users:  # Add the User to the group Automatically.
            #     group.users = [(4, user.id)]

        if project.state == 'completed':
            project.completed_at = fields.Datetime.now()

        # Mar 03 >> Force adding admin users and followers_group to all projects
        # admin_group = self.env.ref('base.group_system')
        # admin_users = admin_group.users
        #
        # project.message_subscribe(partner_ids=admin_users.mapped('partner_id').ids)
        
        # Mar 03 >> Force adding followers_group to all projects
        followers_group = self.env.ref('custom_project.group_followers_all_projects', raise_if_not_found=False)
        if followers_group:
            followers_users = followers_group.users
            project.message_subscribe(partner_ids=followers_users.mapped('partner_id').ids)

        # Mar 05 >> Adding Director to Followers
        if vals.get('technical_director_id'):
            project.message_subscribe(partner_ids=[project.technical_director_id.partner_id.id])

        return project
        # end

    # @api.onchange('technical_director_id')
    # def _onchange_technical_director_id(self):
    #     if self.technical_director_id:
    #         self.warning_message = """
    #                         <div style="color: ##101010; font-weight: bold; text-align: center; display: flex;
    #                          justify-content: center; align-items: center; flex-direction: column;">
    #                             <img src="data:image/png;base64,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" alt="information">
    #                             <p>Please be careful.<br>The selected User will be added to
    #                              <span style="color: #460880">Technical Director</span> Groups.</p>
    #                         </div>
    #                     """

    def write(self, vals):
        res = super(CustomProjectProject, self).write(vals)
        if 'technical_director_id' in vals:
            for record in self:
                user = record.env['res.users'].browse(vals['technical_director_id'])
                group = record.env.ref('custom_project.group_technical_director')
                # if user and group and user not in group.users:  # Add the User to the group Automatically.
                #     group.users = [(4, user.id)]

        if 'user_id' in vals:
            for record in self:
                project_manager = record.env['res.users'].browse(vals['user_id'])
                group_manager = record.env.ref('custom_project.group_project_manager')
                if project_manager and group_manager and project_manager not in group_manager.users:
                    group_manager.users = [(4, project_manager.id)]

        # Mar 05
        if 'technical_director_id' in vals:
            for project in self:
                if project.technical_director_id:
                    project.message_subscribe(partner_ids=[project.technical_director_id.partner_id.id])

        return res

    def unlink(self):
        """When deleting a project, we disable the restriction on deleting followers. """
        if not self.env.context.get('deleting_whole_project'):
            for project in self:
                if project.user_id == self.env.user:
                    return super(CustomProjectProject, self).with_context(deleting_whole_project=True,
                                                                          allow_project_delete=True).sudo().unlink()

            return super(CustomProjectProject, self).with_context(deleting_whole_project=True,
                                                                  allow_project_delete=True).unlink()
        return super(CustomProjectProject, self).unlink()


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    approval_status = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='Approval Status',
        default='draft',
    )

    date = fields.Datetime(string="Date and Time", required=True)

    @api.model
    def create(self, vals):
        task_id = vals.get('task_id')
        if task_id:
            task = self.env['project.task'].browse(task_id)

            project = task.project_id
            if project.state == 'completed':
                raise ValidationError("The project is Completed. You cannot log time anymore.")

            if self.env.user not in task.user_ids:
                raise AccessError("You are not assigned to this task.")

            # Checks, Employee is assigned to task or not.
            allocation = task.allocation_ids.filtered(lambda a: a.employee_id == self.env.user)
            if not allocation:
                raise AccessError(f"❌\nYou do not have permissions to add timesheet records."
                                  "\n⚙️"
                                  "\n  |_The user first must be Assigned to the task, then must be added to Notebook >> My Team)")
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
                raise ValidationError(f"Total allocated hours cannot exceed the planned hours for this task!")


class MailFollowers(models.Model):
    _inherit = "mail.followers"

    # @api.model
    def unlink(self):
        """Avoid deleting Admin members and 'Followers of all Projects' members from project followers
        (except when deleting a task or a project)"""
        print("🔴 Delete followers: ", self.mapped('partner_id').ids)

        # If the deletion operation is performed on a project or task, no special review is required.
        if self.env.context.get('allow_task_delete') or self.env.context.get('allow_project_delete'):
            return super(MailFollowers, self).unlink()

        # Get admin group
        admin_group = self.env.ref('base.group_system')

        # Get Group of 'Followers of all Projects'
        followers_group = self.env.ref('custom_project.group_followers_all_projects', raise_if_not_found=False)

        for follower in self:
            user = follower.partner_id.user_ids[:1]  # Get the first user associated with this partner

            # Prevent manual deletion of members of two groups (but allow deletion if the entire project is deleted)
            if (
                    user
                    and (user.has_group('base.group_system') or (followers_group and user in followers_group.users))
                    and not self.env.context.get('deleting_whole_project')
            ):
                raise UserError(
                    _("❌\nYou cannot remove an admin or a 'Followers of all Projects' member from project followers.🚫"))
        # Mar 06

        # This code will remove the user from current task followers section

        partners_to_remove = self.mapped('partner_id')
        current_user = self.env.user

        _logger.info(
            "📌 partners_to_remove: %s | 🔍 Removed by: %s (ID: %s)",
            partners_to_remove.ids,
            current_user.name,
            current_user.id
        )

        task_id_to_remove_from = self.env.context.get('task_id')

        if not task_id_to_remove_from:
            if self.res_model == 'project.task':
                task_id_to_remove_from = self.res_id

        print(f"✅ Final amount >> task_id_to_remove_from: {task_id_to_remove_from}")

        if not task_id_to_remove_from:
            _logger.warning("Task ID not found!")
        else:
            task_to_modify = self.env['project.task'].browse(task_id_to_remove_from)
            print(f"task_to_modify: {task_to_modify}")

            if task_to_modify.exists():
                print(f"📌 Task {task_to_modify.id} Has users: {task_to_modify.user_ids.ids}")
                users_to_remove = task_to_modify.user_ids.filtered(
                    lambda user: user.partner_id in self.mapped('partner_id'))

                if users_to_remove:
                    task_to_modify.write({'user_ids': [(3, user.id) for user in users_to_remove]})
                    print(f"✅ Users {users_to_remove.ids} from Task {task_to_modify.id} Deleted!")
            else:
                print("📌 ❌ The requested task was not found!")

        # End
        return super(MailFollowers, self).unlink()

    # Mar 09
    @api.model
    def create(self, vals):
        follower = super(MailFollowers, self).create(vals)

        # Check if this follower is related to a task.
        if follower.res_model == 'project.task':
            task = self.env['project.task'].browse(follower.res_id)
            partner = follower.partner_id

            # If this follower has an Odoo user, add him to user_ids
            if partner.user_ids:
                task.write({'user_ids': [(4, partner.user_ids[0].id)]})

        return follower

    def write(self, vals):
        res = super(MailFollowers, self).write(vals)

        for follower in self:
            if follower.res_model == 'project.task':
                task = self.env['project.task'].browse(follower.res_id)
                partner = follower.partner_id

                if partner.user_ids:
                    task.write({'user_ids': [(4, partner.user_ids[0].id)]})

        return res
    # End


class ProjectDeleteWizard(models.TransientModel):
    """ To get Delete Project accesses """
    _inherit = "project.delete.wizard"


class AccountAnalyticAccountInherit(models.Model):
    """ To get Delete Project accesses """
    _inherit = 'account.analytic.account'
