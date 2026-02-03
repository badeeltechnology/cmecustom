// Copyright (c) 2026, CME and contributors
// For license information, please see license.txt

frappe.query_reports["Project Timesheet Monthly"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			options: get_year_options(),
			default: new Date().getFullYear().toString(),
			reqd: 1
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [
				{ value: "01", label: __("January") },
				{ value: "02", label: __("February") },
				{ value: "03", label: __("March") },
				{ value: "04", label: __("April") },
				{ value: "05", label: __("May") },
				{ value: "06", label: __("June") },
				{ value: "07", label: __("July") },
				{ value: "08", label: __("August") },
				{ value: "09", label: __("September") },
				{ value: "10", label: __("October") },
				{ value: "11", label: __("November") },
				{ value: "12", label: __("December") }
			],
			default: String(new Date().getMonth() + 1).padStart(2, '0'),
			reqd: 1
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project"
		}
	]
};

function get_year_options() {
	let options = [];
	let current_year = new Date().getFullYear();
	for (let i = current_year - 2; i <= current_year + 1; i++) {
		options.push(i.toString());
	}
	return options.join("\n");
}
