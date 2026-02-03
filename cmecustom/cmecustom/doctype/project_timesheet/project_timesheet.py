# Copyright (c) 2026, CME and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, time_diff_in_hours, get_time


class ProjectTimesheet(Document):
	def validate(self):
		self.validate_employee_or_external()
		self.validate_duplicate_employee()
		self.calculate_hours()
		self.calculate_totals()

	def before_submit(self):
		# Clear old timesheet links (important for amended documents)
		for row in self.project_timesheet_details:
			if row.timesheet:
				# Check if the linked timesheet is cancelled
				ts_status = frappe.db.get_value("Timesheet", row.timesheet, "docstatus")
				if ts_status == 2:  # Cancelled
					row.timesheet = None

	def on_submit(self):
		self.create_employee_timesheets()

	def on_cancel(self):
		self.cancel_employee_timesheets()

	def validate_employee_or_external(self):
		"""Either employee or external_worker_name must be filled"""
		for row in self.project_timesheet_details:
			if not row.employee and not row.external_worker_name:
				frappe.throw(
					_("Row {0}: Either Employee or External Worker Name is required").format(row.idx)
				)
			if row.employee and row.external_worker_name:
				frappe.throw(
					_("Row {0}: Please select either Employee or External Worker Name, not both").format(row.idx)
				)

	def validate_duplicate_employee(self):
		"""Check for overlapping times for same employee within the document"""
		# Check for overlapping times within the same document
		self.check_internal_time_overlaps()

		# Check for overlapping times across different Project Timesheets
		self.check_time_overlaps()

	def check_internal_time_overlaps(self):
		"""Check for overlapping times for the same employee within this document"""
		rows_by_employee = {}

		# Group rows by employee
		for row in self.project_timesheet_details:
			if row.employee:
				if row.employee not in rows_by_employee:
					rows_by_employee[row.employee] = []
				rows_by_employee[row.employee].append(row)

		# Check for overlaps within each employee's entries
		overlap_errors = []
		for employee, rows in rows_by_employee.items():
			if len(rows) < 2:
				continue

			for i, row1 in enumerate(rows):
				for row2 in rows[i + 1:]:
					# Check first shift overlap
					if row1.checkin and row1.checkout and row2.checkin and row2.checkout:
						if self.times_overlap(row1.checkin, row1.checkout, row2.checkin, row2.checkout):
							overlap_errors.append({
								"employee": row1.employee_name or row1.employee,
								"row1_idx": row1.idx,
								"row1_time": f"{row1.checkin} - {row1.checkout}",
								"row1_project": row1.project or "No Project",
								"row2_idx": row2.idx,
								"row2_time": f"{row2.checkin} - {row2.checkout}",
								"row2_project": row2.project or "No Project"
							})

		if overlap_errors:
			error_msg = _("<b>Error: Overlapping times for same employee!</b><br><br>")
			for e in overlap_errors:
				error_msg += _(
					"<b>{0}:</b><br>"
					"&nbsp;&nbsp;Row {1}: {2} ({3})<br>"
					"&nbsp;&nbsp;Row {4}: {5} ({6})<br>"
					"&nbsp;&nbsp;These times overlap!<br><br>"
				).format(
					e["employee"],
					e["row1_idx"],
					e["row1_time"],
					e["row1_project"],
					e["row2_idx"],
					e["row2_time"],
					e["row2_project"]
				)
			frappe.throw(error_msg, title=_("Time Overlap Error"))

	def check_time_overlaps(self):
		"""Warn if employee has overlapping time entries on the same date"""
		overlap_warnings = []

		for row in self.project_timesheet_details:
			if not row.employee or not row.checkin or not row.checkout:
				continue

			# Get other timesheet entries for this employee on the same date
			existing_entries = frappe.db.sql("""
				SELECT
					pt.name as timesheet_name,
					ptd.checkin,
					ptd.checkout,
					ptd.checkin_2,
					ptd.checkout_2,
					ptd.project
				FROM `tabProject Timesheet` pt
				INNER JOIN `tabProject Timesheet Details` ptd ON ptd.parent = pt.name
				WHERE pt.date = %s
				AND pt.docstatus = 1
				AND pt.name != %s
				AND ptd.employee = %s
			""", (self.date, self.name, row.employee), as_dict=True)

			for entry in existing_entries:
				# Check overlap for first shift
				if self.times_overlap(row.checkin, row.checkout, entry.checkin, entry.checkout):
					overlap_warnings.append({
						"employee": row.employee_name or row.employee,
						"row_idx": row.idx,
						"current_time": f"{row.checkin} - {row.checkout}",
						"current_project": row.project or "No Project",
						"existing_timesheet": entry.timesheet_name,
						"existing_time": f"{entry.checkin} - {entry.checkout}",
						"existing_project": entry.project or "No Project"
					})

				# Check overlap with second shift of existing entry
				if entry.checkin_2 and entry.checkout_2:
					checkin_2 = get_time(entry.checkin_2)
					checkout_2 = get_time(entry.checkout_2)
					if not (checkin_2.hour == 0 and checkin_2.minute == 0 and
							checkout_2.hour == 0 and checkout_2.minute == 0):
						if self.times_overlap(row.checkin, row.checkout, entry.checkin_2, entry.checkout_2):
							overlap_warnings.append({
								"employee": row.employee_name or row.employee,
								"row_idx": row.idx,
								"current_time": f"{row.checkin} - {row.checkout}",
								"current_project": row.project or "No Project",
								"existing_timesheet": entry.timesheet_name,
								"existing_time": f"{entry.checkin_2} - {entry.checkout_2}",
								"existing_project": entry.project or "No Project"
							})

				# Check current second shift overlap if exists
				if row.checkin_2 and row.checkout_2:
					checkin_2 = get_time(row.checkin_2)
					checkout_2 = get_time(row.checkout_2)
					if not (checkin_2.hour == 0 and checkin_2.minute == 0 and
							checkout_2.hour == 0 and checkout_2.minute == 0):
						if self.times_overlap(row.checkin_2, row.checkout_2, entry.checkin, entry.checkout):
							overlap_warnings.append({
								"employee": row.employee_name or row.employee,
								"row_idx": row.idx,
								"current_time": f"{row.checkin_2} - {row.checkout_2}",
								"current_project": row.project or "No Project",
								"existing_timesheet": entry.timesheet_name,
								"existing_time": f"{entry.checkin} - {entry.checkout}",
								"existing_project": entry.project or "No Project"
							})

		# Show warning message if overlaps found
		if overlap_warnings:
			warning_msg = _("<b>Warning: Overlapping time entries detected!</b><br><br>")
			for w in overlap_warnings:
				warning_msg += _(
					"<b>Row {0} - {1}:</b><br>"
					"&nbsp;&nbsp;Current: {2} ({3})<br>"
					"&nbsp;&nbsp;Overlaps with {4}: {5} ({6})<br><br>"
				).format(
					w["row_idx"],
					w["employee"],
					w["current_time"],
					w["current_project"],
					w["existing_timesheet"],
					w["existing_time"],
					w["existing_project"]
				)
			frappe.msgprint(warning_msg, title=_("Time Overlap Warning"), indicator="orange")

	def times_overlap(self, start1, end1, start2, end2):
		"""Check if two time periods overlap"""
		start1 = get_time(start1)
		end1 = get_time(end1)
		start2 = get_time(start2)
		end2 = get_time(end2)

		# Two periods overlap if one starts before the other ends
		return start1 < end2 and start2 < end1

	def calculate_hours(self):
		"""Calculate working hours and overtime for each row"""
		standard_hours = 8  # Standard working hours per day

		for row in self.project_timesheet_details:
			total_hours = 0

			# Calculate first shift hours
			if row.checkin and row.checkout:
				shift1_hours = time_diff_in_hours(row.checkout, row.checkin)
				if shift1_hours > 0:
					total_hours += shift1_hours

			# Calculate second shift hours (if exists)
			if row.checkin_2 and row.checkout_2:
				checkin_2 = get_time(row.checkin_2)
				checkout_2 = get_time(row.checkout_2)
				# Only calculate if times are not 00:00:00
				if not (checkin_2.hour == 0 and checkin_2.minute == 0 and
						checkout_2.hour == 0 and checkout_2.minute == 0):
					shift2_hours = time_diff_in_hours(row.checkout_2, row.checkin_2)
					if shift2_hours > 0:
						total_hours += shift2_hours

			# Deduct break hours
			break_hours = flt(row.break_hours) or 0
			net_hours = total_hours - break_hours

			if net_hours < 0:
				net_hours = 0

			# Calculate working hours and overtime
			if net_hours <= standard_hours:
				row.working_hours = flt(net_hours, 2)
				row.overtime = 0
			else:
				row.working_hours = flt(net_hours, 2)
				row.overtime = flt(net_hours - standard_hours, 2)

	def calculate_totals(self):
		"""Calculate total working hours and overtime"""
		self.total_working_hours = sum(flt(row.working_hours) for row in self.project_timesheet_details)
		self.total_overtime = sum(flt(row.overtime) for row in self.project_timesheet_details)

	def create_employee_timesheets(self):
		"""Create ERPNext Timesheet for each employee on submit"""
		from datetime import timedelta

		for row in self.project_timesheet_details:
			if row.working_hours <= 0:
				continue

			# Determine employee for timesheet
			is_external = False
			if row.employee:
				employee = row.employee
				worker_name = row.employee_name
			elif row.external_worker_name:
				# Use "External" employee for external workers
				external_emp = frappe.db.get_value("Employee", {"employee_name": "External"}, "name")
				if not external_emp:
					frappe.throw(_("Employee 'External' not found. Please create an Employee with name 'External' for external worker timesheets."))
				employee = external_emp
				worker_name = row.external_worker_name
				is_external = True
			else:
				continue

			timesheet = frappe.new_doc("Timesheet")
			timesheet.employee = employee
			timesheet.company = self.company

			# Calculate from_time and to_time based on checkin/checkout
			from_time = frappe.utils.get_datetime(f"{self.date} {row.checkin}")
			to_time = frappe.utils.get_datetime(f"{self.date} {row.checkout}")

			# Calculate regular hours (up to 8 hours)
			regular_hours = min(flt(row.working_hours), 8)
			overtime_hours = flt(row.overtime)

			# Build description with worker name
			if is_external:
				base_desc = f"External Worker: {worker_name} | Project Timesheet {self.name}"
			else:
				base_desc = f"{worker_name} | Project Timesheet {self.name}"

			# Add time log for regular hours
			regular_end_time = from_time + timedelta(hours=regular_hours + flt(row.break_hours))
			timesheet.append("time_logs", {
				"activity_type": self.get_activity_type("Regular"),
				"from_time": from_time,
				"to_time": regular_end_time,
				"hours": regular_hours,
				"project": row.project,
				"description": f"Regular hours: {base_desc}"
			})

			# Add separate time log for overtime if exists
			if overtime_hours > 0:
				timesheet.append("time_logs", {
					"activity_type": self.get_activity_type("Overtime"),
					"from_time": regular_end_time,
					"to_time": to_time,
					"hours": overtime_hours,
					"project": row.project,
					"description": f"Overtime: {base_desc}"
				})

			timesheet.flags.ignore_validate = True
			timesheet.insert(ignore_permissions=True)
			timesheet.submit()

			# Link timesheet to the row for reference
			frappe.db.set_value("Project Timesheet Details", row.name, "timesheet", timesheet.name)

		frappe.msgprint(_("Employee Timesheets created successfully"), indicator="green")

	def cancel_employee_timesheets(self):
		"""Cancel linked ERPNext Timesheets on cancel"""
		for row in self.project_timesheet_details:
			# Use the stored timesheet link
			if row.timesheet and frappe.db.exists("Timesheet", row.timesheet):
				ts_doc = frappe.get_doc("Timesheet", row.timesheet)
				if ts_doc.docstatus == 1:
					ts_doc.cancel()
					frappe.db.set_value("Project Timesheet Details", row.name, "timesheet", None)

		frappe.msgprint(_("Linked Employee Timesheets cancelled"), indicator="orange")

	def get_activity_type(self, activity_name):
		"""Get or create activity type"""
		if not frappe.db.exists("Activity Type", activity_name):
			activity = frappe.new_doc("Activity Type")
			activity.activity_type = activity_name
			activity.insert(ignore_permissions=True)
		return activity_name
