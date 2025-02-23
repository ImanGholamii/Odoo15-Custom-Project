# -*- coding: utf-8 -*-
{
    'name': "custom_project",

    'summary': """
        This module enhances the functionality of Odoo's Project Management by adding additional features to
        task tracking, time allocation, and role-based access control.
        It introduces fields to manage "Initially Planned Hours" and "Remaining Time,"
        which are dynamically updated based on task assignments. The module also allows for better management of task 
        responsibilities, providing a clear "Responsible User" field with access control, ensuring only the 
        responsible user can update planned hours. Additionally, it ensures that the allocated hours per user 
        do not exceed the planned hours, helping teams stay within their time estimates.
        These enhancements improve transparency, efficiency, and accountability in project workflows.
        """,

    'description': """
        This module extends the Odoo Project application with advanced task and project management features,
         ensuring better time tracking, task delegation, and role-based access control.

        #### **Key Features:**
        ✅ **Enhanced Task Responsibility Management**  
           - Assigns a responsible user for each task, defaulting to the creator.  
           - Restricts planned hours modifications to the assigned responsible user.  
           
        ✅ **Time Management and Allocation**  
           - Introduces "Initially Planned Hours" for accurate time estimation.  
           - Implements "Remaining Time" calculation, updating dynamically based on task progress.  
           - Ensures that the sum of all assigned users’ allocated hours does not exceed planned task hours.  
        
        ✅ **Project-Level Time Control**  
           - Defines a maximum "Allocated Hours" limit for projects.  
           - Prevents tasks from exceeding the project’s allocated time.  
        
        ✅ **Access and Role Management**  
           - Introduces the role of "Technical Director" responsible for project approval.  
           - Allows only the Technical Director or an admin to assign a Project Manager.  
           - Restricts project state changes (Draft → In Progress → Completed) based on user roles.  
        
        ✅ **Validation & Constraints**  
           - Blocks users from logging more hours than their assigned task allocation.  
           - Ensures that a Technical Director is assigned before creating a project.  
           - Restricts task creation permissions to the Project Manager.  
        
        ✅ **UI/UX Improvements**  
           - Adds fields for "Responsible User," "Allocated Hours," and "Project State" to project and task views.  
           - Provides a seamless interface for tracking time, responsibilities, and project status.
        
        This module helps teams manage their projects with greater accuracy, reducing time mismanagement and enhancing project oversight.

        
    """,

    'author': "Iman_Gholami",
    'website': "https://github.com/ImanGholamii/Odoo15-Custom-Project",

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
    'icon': '/custom_project/static/description/icon.png',
    'demo': [],
    'installable': True,
    'auto install': False,
    'application': True,
}
