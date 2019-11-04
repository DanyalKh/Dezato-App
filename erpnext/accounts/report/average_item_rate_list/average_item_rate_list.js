// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Average item rate list"] = {
	"filters": [

		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
//		{
//			"fieldname": "item_code",
//			"label": __("Item"),
//			"fieldtype": "Link",
//			"options": "Item",
//		}

	]
}
