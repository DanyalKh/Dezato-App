# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import get_tax_accounts
import numpy

def execute(filters=None):
	return _execute(filters)

def _execute(filters=None):
	columns = []
	columns=get_columns()

	item_list = get_items(filters)

	item_code = None
	stock_qty = 0
	data = []
	average_rate = []
	average_total = 0
	from collections import defaultdict
	e = defaultdict(list)
	row = []
	count = 0
	for d in item_list:
		# row = [d.item_code, d.item_name, d.item_group, d.posting_date, d.due_date, d.supplier, d.base_net_rate]

		# if d.item_code not in e:
		# 	e[d.item_code].append(row)
			# print(d.item_code)

		if item_code != d.item_code:
			average_rate = []
			stock_qty = 0
			average_total = 0

		average_total += d.base_net_rate
		stock_qty += d.stock_qty
		average_rate.append(d.base_net_rate)

		if item_code != d.item_code:
			# if count != 0:
				average = average_total / len(average_rate)
				row = [d.item_code, d.item_name, d.item_group, d.posting_date, d.due_date, d.supplier, stock_qty,
					   d.base_net_rate, average]
				data.append(row)
				print (stock_qty)
				print(len(average_rate))
				print(average_total)
		item_code = d.item_code
		# if d.item_code in e:
		# 	e[d.item_code].append(average_total)
		# 	e[d.item_code].append(stock_qty)
		# 	e[d.item_code].append(average_rate)
		count =1

	print (stock_qty)
	print(len(average_rate))
	print(average_total)


		# 	# stock_uom, purchase_order, purchase_receipt, invoice, d.supplier_name,

			# result.append(row)
	# print(e.iteritems())

	# for v in e.iteritems():
	# 	print(v)
		# for i in v:
			# print(i)
		# row = [d.item_code, d.item_name, d.item_group, d.posting_date, d.due_date, d.supplier, d.stock_qty, d.base_net_rate, average]
	# print(row)
	# average_ = sum(average) / len(average_rate)
	# data =[average_, base_net_amount]
	# 	data.append(v)
	return columns, data

def get_conditions(filters):
	conditions = ""

	for opts in (
		("item_code", " and `tabPurchase Invoice Item`.item_code = %(item_code)s"),
		("from_date", " and `tabPurchase Invoice`.posting_date>=%(from_date)s"),
		("to_date", " and `tabPurchase Invoice`.posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]

	return conditions


def get_purchase_receipts_against_purchase_order(item_list):
	po_pr_map = frappe._dict()
	po_item_rows = list(set([d.po_detail for d in item_list]))

	if po_item_rows:
		purchase_receipts = frappe.db.sql("""
			select parent, purchase_order_item
			from `tabPurchase Receipt Item`
			where docstatus=1 and purchase_order_item in (%s)
			group by purchase_order_item, parent
		""" % (', '.join(['%s']*len(po_item_rows))), tuple(po_item_rows), as_dict=1)

		for pr in purchase_receipts:
			po_pr_map.setdefault(pr.po_detail, []).append(pr.parent)

	return po_pr_map

def get_items(filters):
	conditions = get_conditions(filters)
	# match_conditions = frappe.build_match_conditions("Purchase Invoice")

	# if match_conditions:
	# 	match_conditions = " and {0} ".format(match_conditions)

	# if additional_query_columns:
	# 	additional_query_columns = ', ' + ', '.join(additional_query_columns)

	return frappe.db.sql("""
		select
			`tabPurchase Invoice Item`.`name`, `tabPurchase Invoice Item`.`parent`,
			`tabPurchase Invoice`.posting_date,`tabPurchase Invoice`.due_date, `tabPurchase Invoice`.credit_to, `tabPurchase Invoice`.company,
			`tabPurchase Invoice`.supplier, `tabPurchase Invoice`.remarks, `tabPurchase Invoice`.base_net_total, `tabPurchase Invoice Item`.`item_code`,
			`tabPurchase Invoice Item`.`item_name`, `tabPurchase Invoice Item`.`item_group`,
			`tabPurchase Invoice Item`.`project`, `tabPurchase Invoice Item`.`purchase_order`,
			`tabPurchase Invoice Item`.`purchase_receipt`, `tabPurchase Invoice Item`.`po_detail`,
			`tabPurchase Invoice Item`.`expense_account`, `tabPurchase Invoice Item`.`stock_qty`,
			`tabPurchase Invoice Item`.`stock_uom`, `tabPurchase Invoice Item`.`base_net_rate`,
			`tabPurchase Invoice Item`.`base_net_amount`,
			`tabPurchase Invoice`.supplier_name, `tabPurchase Invoice`.mode_of_payment
		from `tabPurchase Invoice`, `tabPurchase Invoice Item`
		where `tabPurchase Invoice`.name = `tabPurchase Invoice Item`.`parent` and
		`tabPurchase Invoice`.docstatus = 1 {0}
		order by `tabPurchase Invoice`.posting_date desc, `tabPurchase Invoice Item`.item_code desc
	""".format(conditions), filters, as_dict=1)


def get_columns():
	columns = [
		_("Item Code") + ":Link/Item:120", _("Item Name") + "::120",
		_("Item Group") + ":Link/Item Group:100",
		# _("Invoice") + ":Link/Purchase Invoice:120",
		_("Posting Date") + ":Date:120", _("Due Date") + ":Date:100", _("Supplier") + ":Link/Supplier:120",
		# "Supplier Name::120"
	]

	columns += [
		  # _("Purchase Order") + ":Link/Purchase Order:140",
		# _("Purchase Receipt") + ":Link/Purchase Receipt:140",
		_("Stock Qty") + ":Float:120",
		# _("Stock UOM") + "::100",
		_("Rate") + ":Currency/currency:120",_("Average Rate") + ":Currency/currency:120"
		# , _("Amount") + ":Currency/currency:120"
	]

	return columns


