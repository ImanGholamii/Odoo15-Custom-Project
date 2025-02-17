# Odoo15-Custom-Project
Custom Project Task Module This module extends the default functionality of Odoo's Project Management (Project Module) system by introducing additional features for task and project hour management.

# Custom Project Task Module

This module extends the functionality of the default `project.task` and `project.project` models to enhance project and task management with additional features such as task hour allocation, task planning, and user-specific constraints.

## Features

### 1. **Initially Planned Hours for Tasks**
   - Adds a field `planned_hours` to the `project.task` model to track the initially planned hours for a task.
   - The field is mandatory when creating a new task.
   - A validation error is raised if the total planned hours for tasks in a project exceed the allocated hours.

### 2. **Readonly Planned Hours**
   - A computed field `planned_hours_readonly` determines if the planned hours should be editable based on the task creator. Only the creator can edit this field.

### 3. **Employee Hour Allocations**
   - A new model `project.task.allocation` allows allocating planned hours to specific employees for each task.
   - The allocated hours for each employee are tracked and validated, ensuring that no employee logs more hours than their allocation.

### 4. **Allocated Hours for Employees**
   - A computed field `allocated_hours_current_employee` calculates the total hours allocated to the current logged-in employee for a specific task.
   
### 5. **Total Project Hours**
   - Adds a computed field `total_project_hours` in the task model to display the total allocated hours for the associated project.

### 6. **Project Management Roles**
   - Adds a `technical_director_id` field to the `project.project` model to define the technical director for the project, with validation to ensure it is always set.
   - Only the project manager can create tasks for a project.

### 7. **Timesheet Approval Status**
   - Extends the `account.analytic.line` model to include an `approval_status` field with values `draft`, `approved`, and `rejected` to track the status of timesheet entries.
   - Validates that employees cannot log more hours than their allocated hours for a task.

## Installation

1. Copy this module into your custom `addons` directory in your Odoo instance.
2. Update the app list in Odoo and install the module named `custom_project_task`.

## Configuration

- The `planned_hours` field is added to tasks in projects. You must ensure that the `allocated_hours` is set for the project to avoid exceeding the planned hours.
- Assign employees to tasks and allocate hours using the `project.task.allocation` model.

## Usage

### Creating a Task:
1. When creating a task, the user is required to set the initially planned hours.
2. The system will check if the total planned hours of tasks within the project exceed the allocated project hours.

### Allocating Hours to Employees:
1. Employees can be allocated a certain number of hours for each task.
2. The allocated hours for each employee cannot exceed the task's planned hours.

### Timesheet Logging:
1. Employees can log time against tasks they are allocated to.
2. The total time logged by an employee cannot exceed their allocated hours for the task.

## Models

### `project.task` (Inherited)
- **planned_hours**: Tracks the initially planned hours for a task.
- **planned_hours_readonly**: A computed field that determines if the `planned_hours` field is editable.
- **allocation_ids**: One2many relation to `project.task.allocation` to allocate hours to employees.
- **allocated_hours_current_employee**: A computed field to show the allocated hours for the current employee on the task.
- **total_project_hours**: A computed field that shows the total allocated hours for the project.

### `project.project` (Inherited)
- **user_id**: Defines the project manager.
- **technical_director_id**: Defines the technical director responsible for the project.
- **allocated_hours**: The maximum number of hours that can be allocated for tasks in this project.

### `project.task.allocation`
- **task_id**: A relation to the `project.task` model.
- **employee_id**: A relation to the `res.users` model to assign employees to tasks.
- **allocated_hours**: The number of hours allocated to an employee for the task.

### `account.analytic.line` (Inherited)
- **approval_status**: Tracks the approval status of the timesheet entry.

## Contributing

1. Fork the repository and create a feature branch.
2. Implement your changes and ensure tests pass.
3. Submit a pull request for review.

## License

This module is licensed under the AGPL-3.0 License.
