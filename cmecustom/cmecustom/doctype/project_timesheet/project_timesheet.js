// Copyright (c) 2026, CME and contributors
// For license information, please see license.txt

frappe.ui.form.on("Project Timesheet", {
	refresh(frm) {
		// Add custom button to fetch employees from a team/department
		if (!frm.doc.docstatus) {
			frm.add_custom_button(__("Fetch Employees"), function () {
				frm.trigger("fetch_employees");
			});
		}
	},

	fetch_employees(frm) {
		// Dialog to select department or fetch all
		let d = new frappe.ui.Dialog({
			title: __("Fetch Employees"),
			fields: [
				{
					fieldname: "department",
					fieldtype: "Link",
					label: __("Department"),
					options: "Department",
				},
				{
					fieldname: "designation",
					fieldtype: "Link",
					label: __("Designation"),
					options: "Designation",
				},
			],
			primary_action_label: __("Fetch"),
			primary_action: function (values) {
				frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Employee",
						filters: {
							status: "Active",
							...(values.department && { department: values.department }),
							...(values.designation && { designation: values.designation }),
						},
						fields: ["name", "employee_name", "designation"],
						limit_page_length: 0,
					},
					callback: function (r) {
						if (r.message) {
							r.message.forEach((emp) => {
								// Check if employee already exists in table
								let exists = frm.doc.project_timesheet_details.some(
									(row) => row.employee === emp.name
								);
								if (!exists) {
									let row = frm.add_child("project_timesheet_details");
									row.employee = emp.name;
									row.employee_name = emp.employee_name;
									row.designation = emp.designation;
									row.checkin = "08:00:00";
									row.checkout = "17:00:00";
									row.break_hours = 1;
								}
							});
							frm.refresh_field("project_timesheet_details");
							frm.trigger("calculate_totals");
						}
					},
				});
				d.hide();
			},
		});
		d.show();
	},

	calculate_totals(frm) {
		let total_working = 0;
		let total_overtime = 0;

		frm.doc.project_timesheet_details.forEach((row) => {
			total_working += flt(row.working_hours);
			total_overtime += flt(row.overtime);
		});

		frm.set_value("total_working_hours", total_working);
		frm.set_value("total_overtime", total_overtime);
	},
});

frappe.ui.form.on("Project Timesheet Details", {
	checkin(frm, cdt, cdn) {
		calculate_row_hours(frm, cdt, cdn);
	},

	checkout(frm, cdt, cdn) {
		calculate_row_hours(frm, cdt, cdn);
	},

	checkin_2(frm, cdt, cdn) {
		calculate_row_hours(frm, cdt, cdn);
	},

	checkout_2(frm, cdt, cdn) {
		calculate_row_hours(frm, cdt, cdn);
	},

	break_hours(frm, cdt, cdn) {
		calculate_row_hours(frm, cdt, cdn);
	},

	project_timesheet_details_remove(frm) {
		frm.trigger("calculate_totals");
	},
});

function calculate_row_hours(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let total_hours = 0;
	const standard_hours = 8;

	// Calculate first shift
	if (row.checkin && row.checkout) {
		let shift1 = time_diff_in_hours(row.checkout, row.checkin);
		if (shift1 > 0) total_hours += shift1;
	}

	// Calculate second shift
	if (row.checkin_2 && row.checkout_2) {
		let checkin2 = row.checkin_2;
		let checkout2 = row.checkout_2;
		// Only calculate if not 00:00:00
		if (checkin2 !== "00:00:00" && checkout2 !== "00:00:00") {
			let shift2 = time_diff_in_hours(checkout2, checkin2);
			if (shift2 > 0) total_hours += shift2;
		}
	}

	// Deduct break hours
	let break_hours = flt(row.break_hours) || 0;
	let net_hours = total_hours - break_hours;
	if (net_hours < 0) net_hours = 0;

	// Set working hours and overtime
	frappe.model.set_value(cdt, cdn, "working_hours", flt(net_hours, 2));

	if (net_hours > standard_hours) {
		frappe.model.set_value(cdt, cdn, "overtime", flt(net_hours - standard_hours, 2));
	} else {
		frappe.model.set_value(cdt, cdn, "overtime", 0);
	}

	frm.trigger("calculate_totals");
}

function time_diff_in_hours(end_time, start_time) {
	// Parse time strings (HH:MM:SS or HH:MM)
	let start = moment(start_time, "HH:mm:ss");
	let end = moment(end_time, "HH:mm:ss");

	let diff = moment.duration(end.diff(start));
	return diff.asHours();
}
