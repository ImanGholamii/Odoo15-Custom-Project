# -*- coding: utf-8 -*-
{
    'name': "custom_project",

    'summary': """
        This module enhances the functionality of Odoo's Project Management by adding additional features to
        task tracking. It introduces fields to manage "Initially Planned Hours" and "Remaining Time,"
        which are dynamically updated based on task assignments. The module also allows for better management of task 
        responsibilities, providing a clear "Responsible User" field with access control, ensuring only the 
        responsible user can update planned hours. Additionally, it ensures that the allocated hours per user 
        do not exceed the planned hours, helping teams stay within their time estimates.
        This module aims to improve the accuracy and transparency of time management within projects.
        """,

    'description': """
        This module extends the Odoo Project application by introducing enhanced task management features.
        
        Key functionalities include:
         Custom Responsible Assignment: Allows assigning a responsible user to tasks,
         automatically defaulting to the creator and restricting updates to planned hours to the responsible user only.
        Remaining Time Calculation:
         Dynamically calculates and displays the remaining time for tasks.
        Planned Hours Allocation: 
         Automatically distributes planned hours among assigned users and ensures timesheet entries do not exceed
         allocated hours.
        Validation for Timesheets: 
         Implements constraints to prevent users from logging more hours than their allocated time for a task.
        Enhanced User Interface: 
         Adds fields for "Responsible" and "Remaining Time" in the task form view, ensuring a seamless workflow.
        
    """,

    'author': "Iman_Gholami",
    'website': "",

    # Categories can be used to filter modules in modules listing

    'category': 'Project/Management',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'project',
        'hr_timesheet',
    ],

    # always loaded
    'data': [
        'security/project_security.xml',
        'security/ir.model.access.csv',
        'views/project_project_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'custom_project/static/src/css/custom_styles.css',
        ],
    },
    'icon' : '/custom_project/static/description/icon.png',
    'demo': [],
    'installable': True,
    'auto install': False,
    'application': True,
}
