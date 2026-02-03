# Copyright (c) 2026, CME and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def format_number(value):
	"""Format number - show decimal only if needed"""
	if value is None or value == 0:
		return 0
	if value == int(value):
		return int(value)
	return round(value, 2)


def get_columns():
	return [
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Project Timesheet"),
			"fieldname": "project_timesheet",
			"fieldtype": "Link",
			"options": "Project Timesheet",
			"width": 150
		},
		{
			"label": _("Employee ID"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120
		},
		{
			"label": _("Employee/Worker Name"),
			"fieldname": "worker_name",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"label": _("Type"),
			"fieldname": "worker_type",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120
		},
		{
			"label": _("Check In"),
			"fieldname": "checkin",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Check Out"),
			"fieldname": "checkout",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Check In 2"),
			"fieldname": "checkin_2",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Check Out 2"),
			"fieldname": "checkout_2",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Break Hrs"),
			"fieldname": "break_hours",
			"fieldtype": "Data",
			"width": 70,
			"align": "right"
		},
		{
			"label": _("Working Hrs"),
			"fieldname": "working_hours",
			"fieldtype": "Data",
			"width": 90,
			"align": "right"
		},
		{
			"label": _("Overtime"),
			"fieldname": "overtime",
			"fieldtype": "Data",
			"width": 70,
			"align": "right"
		},
		{
			"label": _("ERPNext Timesheet"),
			"fieldname": "timesheet",
			"fieldtype": "Link",
			"options": "Timesheet",
			"width": 130
		},
		{
			"label": _("Remarks"),
			"fieldname": "remarks",
			"fieldtype": "Data",
			"width": 150
		}
	]


def format_time(time_val):
	"""Format time - show only hours and minutes"""
	if not time_val:
		return ""
	time_str = str(time_val)
	# Remove seconds if present
	if len(time_str) > 5:
		return time_str[:5]
	return time_str


def get_data(filters):
	conditions = "pt.docstatus = 1"
	params = {}

	if filters.get("from_date"):
		conditions += " AND pt.date >= %(from_date)s"
		params["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions += " AND pt.date <= %(to_date)s"
		params["to_date"] = filters.get("to_date")

	if filters.get("company"):
		conditions += " AND pt.company = %(company)s"
		params["company"] = filters.get("company")

	if filters.get("project"):
		conditions += " AND ptd.project = %(project)s"
		params["project"] = filters.get("project")

	if filters.get("employee"):
		conditions += " AND ptd.employee = %(employee)s"
		params["employee"] = filters.get("employee")

	data = frappe.db.sql(f"""
		SELECT
			pt.date,
			pt.name as project_timesheet,
			ptd.employee,
			ptd.employee_name,
			ptd.external_worker_name,
			ptd.project,
			ptd.checkin,
			ptd.checkout,
			ptd.checkin_2,
			ptd.checkout_2,
			ptd.break_hours,
			ptd.working_hours,
			ptd.overtime,
			ptd.timesheet,
			ptd.remarks
		FROM `tabProject Timesheet Details` ptd
		INNER JOIN `tabProject Timesheet` pt ON pt.name = ptd.parent
		WHERE {conditions}
		ORDER BY pt.date DESC, ptd.employee_name, ptd.external_worker_name
	""", params, as_dict=True)

	# Format data
	result = []
	for row in data:
		result.append({
			"date": row.date,
			"project_timesheet": row.project_timesheet,
			"employee": row.employee,
			"worker_name": row.employee_name or row.external_worker_name,
			"worker_type": "Employee" if row.employee else "External",
			"project": row.project,
			"checkin": format_time(row.checkin),
			"checkout": format_time(row.checkout),
			"checkin_2": format_time(row.checkin_2),
			"checkout_2": format_time(row.checkout_2),
			"break_hours": format_number(row.break_hours),
			"working_hours": format_number(row.working_hours),
			"overtime": format_number(row.overtime),
			"timesheet": row.timesheet,
			"remarks": row.remarks
		})

	return result
