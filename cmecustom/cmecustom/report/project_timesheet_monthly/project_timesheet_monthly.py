# Copyright (c) 2026, CME and contributors
# For license information, please see license.txt

import calendar

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate


def execute(filters=None):
	if not filters:
		filters = {}

	# Get the month and year from filters
	month = filters.get("month")
	year = filters.get("year")
	project = filters.get("project")
	company = filters.get("company")

	if not month or not year:
		frappe.throw(_("Please select Month and Year"))

	# Get first and last day of month
	first_day = getdate(f"{year}-{month}-01")
	last_day = get_last_day(first_day)
	num_days = last_day.day

	# Build columns - Employee + each day of month
	columns = get_columns(num_days, first_day)

	# Get data
	data = get_data(first_day, last_day, num_days, project, company)

	# Get chart
	chart = get_chart(data, num_days)

	return columns, data, None, chart


def format_number(value):
	"""Format number - show decimal only if needed"""
	if value is None or value == 0:
		return ""
	if value == int(value):
		return int(value)
	return round(value, 1)


def get_columns(num_days, first_day):
	columns = [
		{"label": _("Employee/Worker"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
		{
			"label": _("Employee ID"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
	]

	# Add column for each day with day name
	day_names_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
	for day in range(1, num_days + 1):
		date = add_days(first_day, day - 1)
		day_name = day_names_short[date.weekday()]
		columns.append(
			{
				"label": f"{day_name}<br>{day}",
				"fieldname": f"day_{day}",
				"fieldtype": "Data",
				"width": 45,
				"align": "center",
			}
		)

	# Total columns
	columns.extend(
		[
			{
				"label": _("Total Hours"),
				"fieldname": "total_hours",
				"fieldtype": "Data",
				"width": 100,
				"align": "right",
			},
			{
				"label": _("Total OT"),
				"fieldname": "total_overtime",
				"fieldtype": "Data",
				"width": 80,
				"align": "right",
			},
		]
	)

	return columns


def get_data(first_day, last_day, num_days, project=None, company=None):
	# Build conditions
	conditions = "pt.docstatus = 1 AND pt.date BETWEEN %(first_day)s AND %(last_day)s"
	params = {"first_day": first_day, "last_day": last_day}

	if project:
		conditions += " AND ptd.project = %(project)s"
		params["project"] = project

	if company:
		conditions += " AND pt.company = %(company)s"
		params["company"] = company

	# Get all timesheet details for the month
	entries = frappe.db.sql(
		f"""
		SELECT
			ptd.employee,
			ptd.employee_name,
			ptd.external_worker_name,
			pt.date,
			SUM(ptd.working_hours) as working_hours,
			SUM(ptd.overtime) as overtime
		FROM `tabProject Timesheet Details` ptd
		INNER JOIN `tabProject Timesheet` pt ON pt.name = ptd.parent
		WHERE {conditions}
		GROUP BY ptd.employee, ptd.employee_name, ptd.external_worker_name, pt.date
		ORDER BY ptd.employee_name, ptd.external_worker_name, pt.date
	""",
		params,
		as_dict=True,
	)

	# Organize data by employee/worker
	employee_data = {}
	for entry in entries:
		# Key is employee or external worker name
		if entry.employee:
			key = entry.employee
			name = entry.employee_name
		else:
			key = f"ext_{entry.external_worker_name}"
			name = f"[External] {entry.external_worker_name}"

		if key not in employee_data:
			employee_data[key] = {
				"employee": entry.employee,
				"employee_name": name,
				"days": {},
				"total_hours": 0,
				"total_overtime": 0,
			}

		day_num = getdate(entry.date).day
		employee_data[key]["days"][day_num] = flt(entry.working_hours)
		employee_data[key]["total_hours"] += flt(entry.working_hours)
		employee_data[key]["total_overtime"] += flt(entry.overtime)

	# Convert to list format
	data = []
	for _key, emp in employee_data.items():
		row = {
			"employee": emp["employee"],
			"employee_name": emp["employee_name"],
			"total_hours": format_number(emp["total_hours"]),
			"total_overtime": format_number(emp["total_overtime"]),
		}
		# Add day columns
		for day in range(1, num_days + 1):
			row[f"day_{day}"] = format_number(emp["days"].get(day, 0))

		data.append(row)

	return data


def get_chart(data, num_days):
	if not data:
		return None

	# Aggregate hours per day
	daily_totals = [0] * num_days
	for row in data:
		for day in range(1, num_days + 1):
			val = row.get(f"day_{day}", 0)
			if val:
				daily_totals[day - 1] += float(val) if val else 0

	return {
		"data": {
			"labels": [str(d) for d in range(1, num_days + 1)],
			"datasets": [{"name": _("Total Hours"), "values": daily_totals}],
		},
		"type": "bar",
		"height": 200,
	}
