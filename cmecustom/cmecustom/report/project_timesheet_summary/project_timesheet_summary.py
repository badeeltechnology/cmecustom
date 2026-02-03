# Copyright (c) 2026, CME and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}

	group_by = filters.get("group_by", "Employee")

	columns = get_columns(group_by)
	data = get_data(filters, group_by)
	chart = get_chart(data, group_by)

	return columns, data, None, chart


def format_number(value):
	"""Format number - show decimal only if needed"""
	if value is None or value == 0:
		return 0
	if value == int(value):
		return int(value)
	return round(value, 2)


def get_columns(group_by):
	columns = []

	if group_by == "Employee":
		columns = [
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
			}
		]
	elif group_by == "Project":
		columns = [
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 150
			},
			{
				"label": _("Project Name"),
				"fieldname": "project_name",
				"fieldtype": "Data",
				"width": 200
			}
		]
	elif group_by == "Employee and Project":
		columns = [
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
			}
		]

	# Common columns
	columns.extend([
		{
			"label": _("Total Days"),
			"fieldname": "total_days",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("Working Hours"),
			"fieldname": "working_hours",
			"fieldtype": "Data",
			"width": 100,
			"align": "right"
		},
		{
			"label": _("Overtime"),
			"fieldname": "overtime",
			"fieldtype": "Data",
			"width": 80,
			"align": "right"
		},
		{
			"label": _("Total Hours"),
			"fieldname": "total_hours",
			"fieldtype": "Data",
			"width": 100,
			"align": "right"
		}
	])

	return columns


def get_data(filters, group_by):
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

	if group_by == "Employee":
		data = frappe.db.sql(f"""
			SELECT
				ptd.employee,
				ptd.employee_name,
				ptd.external_worker_name,
				COUNT(DISTINCT pt.date) as total_days,
				SUM(ptd.working_hours) as working_hours,
				SUM(ptd.overtime) as overtime
			FROM `tabProject Timesheet Details` ptd
			INNER JOIN `tabProject Timesheet` pt ON pt.name = ptd.parent
			WHERE {conditions}
			GROUP BY ptd.employee, ptd.employee_name, ptd.external_worker_name
			ORDER BY ptd.employee_name, ptd.external_worker_name
		""", params, as_dict=True)

		result = []
		for row in data:
			working = flt(row.working_hours)
			ot = flt(row.overtime)
			result.append({
				"employee": row.employee,
				"worker_name": row.employee_name or row.external_worker_name,
				"worker_type": "Employee" if row.employee else "External",
				"total_days": row.total_days,
				"working_hours": format_number(working),
				"overtime": format_number(ot),
				"total_hours": format_number(working + ot)
			})
		return result

	elif group_by == "Project":
		data = frappe.db.sql(f"""
			SELECT
				ptd.project,
				p.project_name,
				COUNT(DISTINCT pt.date) as total_days,
				SUM(ptd.working_hours) as working_hours,
				SUM(ptd.overtime) as overtime
			FROM `tabProject Timesheet Details` ptd
			INNER JOIN `tabProject Timesheet` pt ON pt.name = ptd.parent
			LEFT JOIN `tabProject` p ON p.name = ptd.project
			WHERE {conditions}
			GROUP BY ptd.project, p.project_name
			ORDER BY ptd.project
		""", params, as_dict=True)

		result = []
		for row in data:
			working = flt(row.working_hours)
			ot = flt(row.overtime)
			result.append({
				"project": row.project or "(No Project)",
				"project_name": row.project_name or "(No Project)",
				"total_days": row.total_days,
				"working_hours": format_number(working),
				"overtime": format_number(ot),
				"total_hours": format_number(working + ot)
			})
		return result

	elif group_by == "Employee and Project":
		data = frappe.db.sql(f"""
			SELECT
				ptd.employee,
				ptd.employee_name,
				ptd.external_worker_name,
				ptd.project,
				COUNT(DISTINCT pt.date) as total_days,
				SUM(ptd.working_hours) as working_hours,
				SUM(ptd.overtime) as overtime
			FROM `tabProject Timesheet Details` ptd
			INNER JOIN `tabProject Timesheet` pt ON pt.name = ptd.parent
			WHERE {conditions}
			GROUP BY ptd.employee, ptd.employee_name, ptd.external_worker_name, ptd.project
			ORDER BY ptd.employee_name, ptd.external_worker_name, ptd.project
		""", params, as_dict=True)

		result = []
		for row in data:
			working = flt(row.working_hours)
			ot = flt(row.overtime)
			result.append({
				"employee": row.employee,
				"worker_name": row.employee_name or row.external_worker_name,
				"worker_type": "Employee" if row.employee else "External",
				"project": row.project or "(No Project)",
				"total_days": row.total_days,
				"working_hours": format_number(working),
				"overtime": format_number(ot),
				"total_hours": format_number(working + ot)
			})
		return result

	return []


def get_chart(data, group_by):
	if not data:
		return None

	if group_by == "Employee":
		labels = [row.get("worker_name", "Unknown") for row in data[:15]]  # Top 15
		working_hours = [float(row.get("working_hours", 0) or 0) for row in data[:15]]
		overtime = [float(row.get("overtime", 0) or 0) for row in data[:15]]
	elif group_by == "Project":
		labels = [row.get("project", "Unknown") for row in data[:15]]
		working_hours = [float(row.get("working_hours", 0) or 0) for row in data[:15]]
		overtime = [float(row.get("overtime", 0) or 0) for row in data[:15]]
	else:
		return None

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Working Hours"),
					"values": working_hours
				},
				{
					"name": _("Overtime"),
					"values": overtime
				}
			]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#5e64ff", "#ff5858"]
	}
