import json

import datetime
import frappe
from frappe.utils import flt


@frappe.whitelist(allow_guest=False)
def sales_invoice_sync(data):
    data = json.loads(data)
    frappe.clear_cache(doctype="Sales Invoice")
    logDataInsert(data["data"], data["user_name"], data["ip_address"], data["handset_model"], data["os_version"])
    update_sales_invoice(data["data"],data["user_name"])
    ret_list = sendItem(data["lastSyncDate"])
    return ret_list


def update_sales_invoice(data,served_by):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d")
    from frappe.utils import now
    currDate = now()

    for d in data:

        if int(d.get("DocStatus", "0")) == 0:
            continue

        if d['Invoice_type'] == "si" or d['Invoice_type'] == "sr":

                filters = [["name", "=", d.get("name")]]
                doc_list = frappe.get_all("Sales Invoice", filters=filters)

                # update
                if doc_list != None and len(doc_list) > 0:
                  try:
                    for d2 in doc_list:
                        doc = frappe.get_doc("Sales Invoice", d2.get("name"))

                        if doc.docstatus == 1 and int(d.get("DocStatus", "0")) != 2:
                            continue

                        doc.name = d.get("name", None)
                        # doc.due_date = d.get("posting_date", None)
                        doc.due_date = currDate

                        doc.owner = d.get("owner", None)
                        doc.grand_total = d.get("grand_total", None)
                        doc.paid_amount = d.get("paid_amount", None)
                        doc.outstanding_amount = d.get("outstanding_amount", None)
                        doc.total = d.get("total", None)
                        doc.total_taxes_and_charges = d.get("total_taxes_and_charges", 0)
                        doc.taxes_and_charges = d.get("taxes_and_charges", 0)
                        doc.customer = d.get("party_name", 0)
                        doc.party = d.get("party_name", 0)
                        doc.status = d.get("status", 0)
                        # if doc.status == 'Paid':
                        #     doc.is_pos = 1
                        #     doc.account_for_change_amount = "Other Income - TC"
                        #     doc.additional_discount_percentage = 0
                        #     doc.base_change_amount = d.get("change_amount", 0)
                        #     doc.base_discount_amount = 0
                        #     # doc.change_amount = d.get("change_amount", 0)
                        #     doc.commission_rate = 0
                        #     # doc.customer_group = "All Customer Group"
                        #     doc.date_issuance = currDate
                        #     doc.date_supply = currDate
                        #     doc.is_return = 1
                        #     doc.return_against = d.get("return_against", None)

                        if int(d.get("DocStatus", "0")) == 1:
                            doc.docstatus = 0
                        doc.company = d.get("company", 0)
                        doc.is_return = d.get("is_return", 0)
                        calculate_tax = Taxes_Calculation(d.get("taxes_and_charges", 0))
                        doc.taxes = []
                        doc.append('taxes', calculate_tax)

                        doc.posting_date = d.get("posting_date", 0)
                        # doc.posting_time = d.get("posting_time", 0)
                        doc.transaction_type_name = d.get("transaction_type_name", 0)
                        doc.base_grand_total = d.get("grand_total", None)
                        doc.against_expense_account = "Cost Of Goods Sold I/C Sales - TC"
                        doc.apply_discount_on = "Net Total"
                        doc.base_net_total = "-" + d.get("total", 0)

                        doc.base_rounded_total = 0
                        doc.base_rounding_adjustment = 0
                        doc.base_taxes_and_charges_added = d.get("total_taxes_and_charges", 0)
                        doc.base_taxes_and_charges_deducted = 0
                        doc.base_total = d.get("total", None)
                        doc.base_total_taxes_and_charges = d.get("total_taxes_and_charges", 0)
                        doc.base_write_off_amount = 0
                        doc.selling_price_list = "Standard selling"
                        doc.company = d.get("company", None)
                        doc.conversion_rate = 1
                        doc.credit_to = "Consigned Payable - TC"
                        doc.currency = "AED"
                        doc.price_list_currency = "AED"
                        doc.disable_rounded_total = 1
                        doc.discount_amount = 0
                        doc.doctype = "Sales Invoice"
                        doc.idx = 0
                        doc.ignore_pricing_rule = 0
                        doc.is_opening = "No"
                        doc.total_commission = 0
                        doc.c_form_applicable = "No"
                        doc.is_subcontracted = "No"
                        doc.language = "en"
                        doc.letter_head = "DEMO Letter Head"
                        doc.net_total = d.get("total", None)
                        doc.party_account_currency = "AED"
                        doc.debit_to = "Trade Receivable - TC"
                        # doc.debit_to = "Accrued Rebates Due from Suppliers - TC"
                        # if doc.outstanding_amount == '0':
                        doc.is_paid = 0
                        doc.mode_of_payment = "Cash"
                        doc.cash_bank_account = "Main Safe - TC"
                        doc.base_paid_amount = d.get("paid_amount", None)
                        doc.plc_conversion_rate = 1

                        ###############payment ##################
                        doc.payments = []

                        e = doc.append('payments', {})
                        e.account = "Main Safe - TC"
                        e.amount = d.get("paid_amount", None)
                        e.base_amount = d.get("paid_amount", None)
                        e.default = 1
                        e.docstatus = 1
                        e.doctype = "Sales Invoice Payment"
                        e.idx = 1
                        e.mode_of_payment = "Cash"
                        e.parent = d.get("name", None)
                        e.parentfield = "payments"
                        e.parenttype = "Sales Invoice"
                        e.doctype = "Sales Invoice Payment"
                        e.type = "Cash"

                        if doc.outstanding_amount == "0":
                            doc.status = "Paid"

                        #########################################

                        # else:
                        #     doc.is_paid = 0
                        #     doc.base_paid_amount = "-" + d.get("paid_amount", None)
                        # doc.creation = d.get("creation", currDate)
                        # doc.modified = d.get("modified", currDate)

                        doc.items = []
                        a = 1
                        if d['item'] != None and len(d['item']) > 0:
                            for d9 in d['item']:
                                f = doc.append('items', {})
                                # d = frappe.new_doc("Sales Invoice Item")
                                f.idx = a
                                f.parent = d9['parent']
                                f.item_name = d9['item_name']
                                f.qty = "-" + d9['qty']
                                f.rate = (float(d9['amount']) / float(d9['qty']))
                                f.amount = "-" + d9['amount']
                                f.discount_amount = d9['discount_amount']
                                f.tax_amount = d9['tax_amount']
                                f.tax_rate = d9['tax_rate']
                                f.conversion_factor = 1
                                f.actual_batch_qty = 0
                                a = a + 1
                                f.actual_batch_qty = 0
                                f.actual_qty = 0
                                f.page_break = 0
                                f.doctype = "Sales Invoice Item"
                                f.allow_zero_valuation_rate = 0
                                f.rate_with_margin = 0
                                f.base_amount = "-" + d9['amount']
                                f.base_net_amount = "-" + d9['amount']
                                f.base_net_rate = (float(d9['amount']) / int(d9['qty']))
                                f.base_price_list_rate = d9['rate']
                                f.base_rate = (float(d9['amount']) / int(d9['qty']))
                                f.base_rate_with_margin = d9['rate']
                                f.cost_center = "Main - TC"
                                f.delivered_by_supplier = 0
                                f.delivered_qty = 0
                                f.description = d9['description']
                                f.doctype = "Sales Invoice Item"
                                f.expense_account = "Others - TC"
                                f.parenttype = "Sales Invoice"
                                f.is_fixed_asset = 0
                                f.parentfield = "items"
                                f.gross_profit = "-3"
                                f.has_batch_no = 0
                                f.has_serial_no = 0
                                # d.image = d9['image']
                                f.income_account = "Sales Account - TC"
                                f.is_fixed_asset = 0
                                f.item_code = d9['item_code']
                                f.item_group = d9['item_group']
                                f.item_tax_rate = "{}"
                                f.item_with_tax_amount = 0
                                f.total_weight = 0
                                f.margin_rate_or_amount = 0
                                f.net_amount = "-" + d9['amount']
                                f.net_rate = (float(d9['amount']) / int(d9['qty']))
                                f.parentfield = "items"
                                f.parenttype = "Sales Invoice"
                                f.price_list_rate = d9['rate']
                                f.projected_qty = 0
                                f.rate_with_margin = d9['rate']
                                f.stock_qty = d9['qty']
                                f.actual_qty = 0
                                f.stock_uom = d9['uom']
                                f.tax_amount = 0
                                f.tax_rate = 0
                                f.total_weight = 0
                                f.uom = d9['uom']
                                f.update_stock = 0
                                f.valuation_rate = 0
                                f.warehouse = "My Store - TC"
                                f.weight_per_unit = 0
                                f.__islocal = 1
                                f.__unsaved = 1

                        if (d.get("is_delete", 0) == "1"):
                         doc.delete()
                        else:
                            doc.save()

                            frappe.db.set_value("Sales Invoice Payment", d.get("name"), "parenttype", "Sales Invoice",
                                                update_modified=False)

                            if int(d.get("DocStatus", "0")) == 1:
                                doc.run_method("on_submit")
                                frappe.db.set_value("Sales Invoice", doc.get("name"), "docstatus", 1, update_modified=False)

                            # frappe.rename_doc("Sales Invoice", doc.name, d.get("name", None), ignore_permissions=True)

                            frappe.db.set_value("Sales Invoice", d.get("name"), "modified", d.get("modified"),
                                                update_modified=False)

                        # doc.save()

                        # if int(d.get("DocStatus", "0")) == 1:
                        #     doc.run_method("on_submit")
                        #     frappe.db.set_value("Sales Invoice", doc.get("name"), "docstatus", 1, update_modified=False)
                        #
                        # frappe.db.set_value("Sales Invoice", doc.get("name"), "modified", d.get("modified"),
                        #                     update_modified=False)


                  except Exception, ex:
                     print ex


                else:
                  if d['Invoice_type'] == "sr":
                    ############return invoice##############
                    try:
                        # insert
                        doc = frappe.new_doc("Sales Invoice")
                        if doc.docstatus == 1 and int(d.get("DocStatus", "0")) != 2:
                            continue
                        doc.name = d.get("name", None)
                        doc.due_date = d.get("posting_date", None)
                        # doc.due_date = currDate
                        doc.naming_series = "SR-"

                        doc.owner = d.get("owner", None)
                        doc.grand_total = "-" + d.get("grand_total", 0)
                        doc.paid_amount = "-" + d.get("paid_amount", 0)
                        doc.outstanding_amount = d.get("outstanding_amount", 0)
                        doc.total = "-" + d.get("total", 0)
                        doc.total_taxes_and_charges = "-" + d.get("total_taxes_and_charges", 0)
                        doc.taxes_and_charges = d.get("taxes_and_charges", 0)
                        doc.customer = d.get("party_name", 0)
                        doc.party = d.get("party_name", 0)
                        doc.status = d.get("status", 0)
                        if doc.status == 'Paid':
                            doc.is_pos = 1
                            doc.account_for_change_amount = "Other Income - TC"
                            doc.additional_discount_percentage = 0
                            doc.base_change_amount = d.get("change_amount", 0)
                            doc.base_discount_amount = 0
                            # doc.change_amount = d.get("change_amount", 0)
                            doc.commission_rate = 0
                            # doc.customer_group = "All Customer Group"
                            doc.date_issuance = d.get("posting_date", None)
                            doc.date_supply = d.get("posting_date", None)
                            doc.is_return = 1
                            doc.return_against = d.get("return_against", None)

                        if int(d.get("DocStatus", "0")) == 1:
                            doc.docstatus = 0
                        doc.company = d.get("company", 0)
                        doc.is_return = d.get("is_return", 0)
                        calculate_tax = Taxes_Calculation(d.get("taxes_and_charges", 0))
                        doc.taxes = []
                        doc.append('taxes', calculate_tax)

                        doc.posting_date = d.get("posting_date", 0)
                        doc.set_posting_time = 1
                        doc.posting_time = d.get("posting_time", 0)
                        doc.transaction_type_name = d.get("transaction_type_name", 0)
                        doc.base_grand_total = "-" + d.get("grand_total", None)
                        doc.against_expense_account = "Cost Of Goods Sold I/C Sales - TC"
                        doc.apply_discount_on = "Net Total"
                        doc.base_net_total = "-" + d.get("total", 0)

                        doc.base_rounded_total = 0
                        doc.base_rounding_adjustment = 0
                        doc.base_taxes_and_charges_added = "-"+d.get("total_taxes_and_charges", 0)
                        doc.base_taxes_and_charges_deducted = 0
                        doc.base_total = "-" + d.get("total", None)
                        doc.base_total_taxes_and_charges = "-" + d.get("total_taxes_and_charges", 0)
                        doc.base_write_off_amount = 0
                        doc.selling_price_list = "Standard selling"
                        doc.company = d.get("company", None)
                        doc.conversion_rate = 1
                        doc.credit_to = "Consigned Payable - TC"
                        doc.currency = "AED"
                        doc.price_list_currency = "AED"
                        doc.disable_rounded_total = 1
                        doc.discount_amount = 0
                        doc.doctype = "Sales Invoice"
                        doc.idx = 0
                        doc.ignore_pricing_rule = 0
                        doc.is_opening = "No"
                        doc.total_commission = 0
                        doc.c_form_applicable = "No"
                        doc.is_subcontracted = "No"
                        doc.language = "en"
                        doc.letter_head = "DEMO Letter Head"
                        doc.net_total = "-" + d.get("total", None)
                        doc.party_account_currency = "AED"
                        doc.debit_to = "Trade Receivable - TC"
                        # doc.debit_to = "Accrued Rebates Due from Suppliers - TC"
                        if doc.outstanding_amount == '0':
                            doc.is_paid = 1
                            doc.mode_of_payment = "Cash"
                            doc.cash_bank_account = "Main Safe - TC"
                            doc.base_paid_amount = "-"+d.get("paid_amount", 0)
                            doc.plc_conversion_rate = 1

                            ###############payment ##################
                            doc.payments = []

                            e = doc.append('payments', {})
                            e.account = "Main Safe - TC"
                            e.amount = "-" + d.get("paid_amount", 0)
                            e.base_amount = "-" + d.get("paid_amount", 0)
                            e.default = 1
                            e.docstatus = 1
                            e.doctype = "Sales Invoice Payment"
                            e.idx = 1
                            e.mode_of_payment = "Cash"
                            e.parent = d.get("name", None)
                            e.parentfield = "payments"
                            e.parenttype = "Sales Invoice"
                            e.doctype = "Sales Invoice Payment"
                            e.type = "Cash"





                        #########################################

                        else:
                            doc.is_paid = 0
                            doc.base_paid_amount = 0
                        # doc.creation = d.get("creation", currDate)
                        # doc.modified = d.get("modified", currDate)

                        doc.items = []
                        a = 1
                        if d['item'] != None and len(d['item']) > 0:
                            for d9 in d['item']:
                                f = doc.append('items', {})
                                # d = frappe.new_doc("Sales Invoice Item")
                                f.idx = a
                                f.parent = d9['parent']
                                f.item_name = d9['item_name']
                                f.qty = "-" + d9['qty']
                                f.rate = (float(d9['amount']) / float(d9['qty']))
                                f.amount = "-" + d9['amount']
                                f.discount_amount = d9['discount_amount']
                                f.tax_amount = d9['tax_amount']
                                f.tax_rate = d9['tax_rate']
                                f.conversion_factor = 1
                                f.actual_batch_qty = 0
                                a = a + 1
                                f.actual_batch_qty = 0
                                f.actual_qty = 0
                                f.page_break = 0
                                f.doctype = "Sales Invoice Item"
                                f.allow_zero_valuation_rate = 0
                                f.rate_with_margin = 0
                                f.base_amount = "-"+d9['amount']
                                f.base_net_amount = "-"+d9['amount']
                                f.base_net_rate = (float(d9['amount']) / int(d9['qty']))
                                f.base_price_list_rate = d9['rate']
                                f.base_rate = (float(d9['amount']) / int(d9['qty']))
                                f.base_rate_with_margin = d9['rate']
                                f.cost_center = "Main - TC"
                                f.delivered_by_supplier = 0
                                f.delivered_qty = 0
                                f.description = d9['description']
                                f.doctype = "Sales Invoice Item"
                                f.expense_account = "Others - TC"
                                f.parenttype = "Sales Invoice"
                                f.is_fixed_asset = 0
                                f.parentfield = "items"
                                f.gross_profit = "-3"
                                f.has_batch_no = 0
                                f.has_serial_no = 0
                                # d.image = d9['image']
                                f.income_account = "Sales Account - TC"
                                f.is_fixed_asset = 0
                                f.item_code = d9['item_code']
                                f.item_group = d9['item_group']
                                f.item_tax_rate = "{}"
                                f.item_with_tax_amount = 0
                                f.total_weight = 0
                                f.margin_rate_or_amount = 0
                                f.net_amount = "-" + d9['amount']
                                f.net_rate = (float(d9['amount']) / int(d9['qty']))
                                f.parentfield = "items"
                                f.parenttype = "Sales Invoice"
                                f.price_list_rate = d9['rate']
                                f.projected_qty = 0
                                f.rate_with_margin = d9['rate']
                                f.stock_qty = d9['qty']
                                f.actual_qty = 0
                                f.stock_uom = d9['uom']
                                f.tax_amount = 0
                                f.tax_rate = 0
                                f.total_weight = 0
                                f.uom = d9['uom']
                                f.update_stock = 0
                                f.valuation_rate = 0
                                f.warehouse = "My Store - TC"
                                f.weight_per_unit = 0
                                f.__islocal = 1
                                f.__unsaved = 1

                                # doc_add_item.creation = currDate
                                # doc_add_item.modified = currDate
                                # doc_add_item.save()
                                # frappe.db.set_value("Sales Invoice Item", doc_add_item.get("parent"), "modified",
                                #                     d.get("modified"),
                                #                     update_modified=False)

                        doc.save()

                        frappe.db.set_value("Sales Invoice Payment", d.get("name"), "parenttype", "Sales Invoice",
                                            update_modified=False)

                        if int(d.get("DocStatus", "0")) == 1:
                            doc.run_method("on_submit")
                            frappe.db.set_value("Sales Invoice", doc.get("name"), "docstatus", 1, update_modified=False)

                            update_tax_doscstatus("Sales", doc.name)

                        frappe.rename_doc("Sales Invoice", doc.name, d.get("name", None), ignore_permissions=True)

                        frappe.db.set_value("Sales Invoice", d.get("name"), "creation", d.get("modified"),
                                            update_modified=False)
                        frappe.db.set_value("Sales Invoice", d.get("name"), "modified", d.get("modified"),
                                            update_modified=False)



                    except Exception, ex:
                        print ex

                    #######################################
                  else:
                    try:
                        # insert
                        doc = frappe.new_doc("Sales Invoice")
                        if doc.docstatus == 1 and int(d.get("DocStatus", "0")) != 2:
                            continue
                        doc.name = d.get("name", None)
                        doc.due_date = d.get("posting_date", None)
                        doc.set_posting_time = 1
                        # doc.due_date = currDate

                        doc.owner = d.get("owner", None)
                        doc.grand_total = d.get("grand_total", None)
                        doc.paid_amount = d.get("paid_amount", None)
                        doc.outstanding_amount = d.get("outstanding_amount", None)
                        doc.total = d.get("total", None)
                        doc.total_taxes_and_charges = d.get("total_taxes_and_charges", 0)
                        doc.taxes_and_charges = d.get("taxes_and_charges", 0)
                        doc.customer = d.get("party_name", 0)
                        doc.party = d.get("party_name", 0)
                        doc.status = d.get("status", 0)
                        doc.naming_series = "SI-"
                        # if doc.status == 'Paid':
                        if doc.outstanding_amount == "0":
                            doc.is_pos = 1
                            doc.account_for_change_amount = "Other Income - TC"
                            doc.additional_discount_percentage = 0
                            doc.base_change_amount = flt(d.get("change_amount", 0))
                            doc.base_discount_amount = 0
                            doc.change_amount = flt(d.get("change_amount", 0))
                            doc.commission_rate = 0
                            # doc.customer_group = "All Customer Group"
                            doc.date_issuance = d.get("posting_date", None)
                            doc.date_supply = d.get("posting_date", None)
                            doc.is_return = 0
                            doc.status = "Paid"




                        if int(d.get("DocStatus", "0")) == 1:
                            doc.docstatus = 0
                        doc.company = d.get("company", 0)
                        doc.is_return = d.get("is_return", 0)
                        calculate_tax = Taxes_Calculation(d.get("taxes_and_charges", 0))
                        doc.taxes = []
                        doc.append('taxes', calculate_tax)

                        doc.posting_date = d.get("posting_date", 0)
                        doc.posting_time = d.get("posting_time", 0)
                        doc.transaction_type_name = d.get("transaction_type_name", 0)
                        doc.base_grand_total = d.get("grand_total", None)
                        doc.against_expense_account = "Cost Of Goods Sold I/C Sales - TC"
                        doc.apply_discount_on = "Net Total"
                        doc.base_net_total = d.get("total", 0)

                        doc.base_rounded_total = 0
                        doc.base_rounding_adjustment = 0
                        doc.base_taxes_and_charges_added = d.get("total_taxes_and_charges", 0)
                        doc.base_taxes_and_charges_deducted = 0
                        doc.base_total = d.get("total", None)
                        doc.base_total_taxes_and_charges = d.get("total_taxes_and_charges", 0)
                        doc.base_write_off_amount = 0
                        doc.selling_price_list = "Standard Selling"
                        doc.company = d.get("company", None)
                        doc.conversion_rate = 1
                        doc.credit_to = "Consigned Payable - TC"
                        doc.currency = "AED"
                        doc.price_list_currency = "AED"
                        doc.disable_rounded_total = 1
                        doc.discount_amount = 0
                        doc.doctype = "Sales Invoice"
                        doc.idx = 0
                        doc.ignore_pricing_rule = 0
                        doc.is_opening = "No"
                        doc.total_commission = 0
                        doc.c_form_applicable = "No"
                        doc.is_subcontracted = "No"
                        doc.language = "en"
                        doc.letter_head = "DEMO Letter Head"
                        doc.net_total = d.get("total", None)
                        doc.party_account_currency = "AED"

                        # doc.debit_to = "Accrued Rebates Due from Suppliers - TC"
                        doc.pos_profile = "Standard POS Profile"
                        doc.is_pos = 1
                        doc.debit_to = "Trade Receivable - TC"



                        if doc.paid_amount > '0':
                            # doc.mode_of_payment = "Cash"
                            doc.cash_bank_account = "Main Safe - TC"
                            doc.base_paid_amount = d.get("paid_amount", None)
                            doc.plc_conversion_rate = 1


                        ###############payment ##################
                            doc.payments = []

                            e = doc.append('payments', {})
                            e.account = "Main Safe - TC"
                            e.amount = d.get("paid_amount", None)
                            e.base_amount = d.get("paid_amount", None)
                            e.default = 1
                            e.docstatus = 1
                            e.doctype = "Sales Invoice Payment"
                            e.idx = 1
                            e.mode_of_payment = "Cash"
                            e.parent = d.get("name", None)
                            e.parentfield = "payments"
                            e.parenttype = "Sales Invoice"
                            e.doctype = "Sales Invoice Payment"
                            e.type = "Cash"




                        #########################################



                        else:
                            doc.base_paid_amount = d.get("paid_amount", None)
                            doc.paid_amount =  d.get("paid_amount", None)

                            ###############payment ##################
                            doc.payments = []

                            e = doc.append('payments', {})
                            e.account = "Main Safe - TC"
                            e.amount = 0
                            e.base_amount = 0
                            e.default = 1
                            e.docstatus = 1
                            e.doctype = "Sales Invoice Payment"
                            e.idx = 1
                            e.mode_of_payment = "Cash"
                            e.parent = d.get("name", None)
                            e.parentfield = "payments"
                            e.parenttype = "Sales Invoice"
                            e.doctype = "Sales Invoice Payment"
                            e.type = "Cash"

                        #########################################

                        # doc.mode_of_payment = "Cash"

                        # doc.creation = d.get("creation", currDate)
                        # doc.modified = d.get("modified", currDate)

                        doc.items = []
                        a = 1
                        if d['item'] != None and len(d['item']) > 0:
                             for d9 in d['item']:
                                f = doc.append('items', {})
                                # d = frappe.new_doc("Sales Invoice Item")
                                f.idx = a
                                f.parent = d9['parent']
                                f.item_name = d9['item_name']
                                f.qty = d9['qty']
                                f.rate = (float(d9['amount'])/float(d9['qty']))
                                f.amount = d9['amount']
                                f.discount_amount = d9['discount_amount']
                                f.tax_amount = d9['tax_amount']
                                f.tax_rate = d9['tax_rate']
                                f.conversion_factor = 1
                                f.actual_batch_qty = 0
                                a = a + 1
                                f.actual_batch_qty = 0
                                f.actual_qty = 0
                                f.page_break = 0
                                f.doctype = "Sales Invoice Item"
                                f.allow_zero_valuation_rate = 0
                                f.rate_with_margin = 0
                                f.base_amount = d9['amount']
                                f.base_net_amount = d9['amount']
                                f.base_net_rate = (float(d9['amount'])/float(d9['qty']))
                                f.base_price_list_rate = d9['rate']
                                f.base_rate =(float(d9['amount'])/float(d9['qty']))
                                f.base_rate_with_margin = d9['rate']
                                f.cost_center = "Main - TC"
                                f.delivered_by_supplier = 0
                                f.delivered_qty = 0
                                f.description = d9['description']
                                f.doctype = "Sales Invoice Item"
                                f.expense_account = "Others - TC"
                                f.parenttype = "Sales Invoice"
                                f.is_fixed_asset = 0
                                f.parentfield="items"
                                f.gross_profit = "-3"
                                f.has_batch_no = 0
                                f.has_serial_no = 0
                                # d.image = d9['image']
                                f.income_account = "Sales Account - TC"
                                f.is_fixed_asset = 0
                                f.item_code = d9['item_code']
                                f.item_group = d9['item_group']
                                f.item_tax_rate = "{}"
                                f.item_with_tax_amount = 0
                                f.total_weight = 0
                                f.margin_rate_or_amount = 0
                                f.net_amount = d9['amount']
                                f.net_rate = (float(d9['amount'])/float(d9['qty']))
                                f.parentfield = "items"
                                f.parenttype = "Sales Invoice"
                                f.price_list_rate = d9['rate']
                                f.projected_qty = 0
                                f.rate_with_margin = d9['rate']
                                f.stock_qty = d9['qty']
                                f.actual_qty = 0
                                f.stock_uom = d9['uom']
                                f.tax_amount = 0
                                f.tax_rate = 0
                                f.total_weight = 0
                                f.uom = d9['uom']
                                f.update_stock = 0
                                f.valuation_rate = 0
                                f.warehouse = "My Store - TC"
                                f.weight_per_unit = 0
                                f.__islocal = 1
                                f.__unsaved = 1

                                # doc_add_item.creation = currDate
                                # doc_add_item.modified = currDate
                                # doc_add_item.save()
                                # frappe.db.set_value("Sales Invoice Item", doc_add_item.get("parent"), "modified",
                                #                     d.get("modified"),
                                #                     update_modified=False)

                        doc.save()
                        frappe.db.set_value("Sales Invoice Payment", d.get("name"), "parenttype", "Sales Invoice", update_modified=False)

                        if int(d.get("DocStatus", "0")) == 1:
                            doc.run_method("on_submit")
                            frappe.db.set_value("Sales Invoice", doc.get("name"), "served_by", served_by, update_modified=False)
                            frappe.db.set_value("Sales Invoice", doc.get("name"), "docstatus", 1, update_modified=False)
                            if doc.outstanding_amount == 0:
                                frappe.db.set_value("Sales Invoice", doc.get("name"), "status", "Paid",
                                                    update_modified=False)

                            update_tax_doscstatus("Sales", doc.name)

                        frappe.rename_doc("Sales Invoice", doc.name, d.get("name", None), ignore_permissions=True)

                        # frappe.db.set_value("Sales Invoice", d.get("name"), "paid_amount", d.get("paid_amount", 0),
                        #                     update_modified=False)
                        # frappe.db.set_value("Sales Invoice", d.get("name"), "base_paid_amount", d.get("paid_amount", 0),
                        #                     update_modified=False)
                        # frappe.db.set_value("Sales Invoice", d.get("name"), "outstanding_amount", d.get("outstanding_amount", 0),
                        #                     update_modified=False)
                        frappe.db.set_value("Sales Invoice", d.get("name"), "update_stock",1,update_modified=False)

                        frappe.db.set_value("Sales Invoice", d.get("name"), "creation", d.get("modified"),
                                            update_modified=False)

                        frappe.db.set_value("Sales Invoice", d.get("name"), "modified", d.get("modified"),
                                            update_modified=False)



                    except Exception, ex:
                        print ex

        else:
                filters = [["name", "=", d.get("name")]]
                doc_list_purchase = frappe.get_all("Purchase Invoice", filters=filters)

                # update
                if doc_list_purchase != None and len(doc_list_purchase) > 0:
                  try:
                    for d4 in doc_list_purchase:
                        doc = frappe.get_doc("Purchase Invoice", d4.get("name"))

                        if doc.docstatus == 1 and int(d.get("DocStatus", "0")) != 2:
                            continue

                        doc.name = d.get("name", None)
                        doc.owner = d.get("owner", None)
                        doc.grand_total = d.get("grand_total", None)
                        doc.paid_amount = d.get("paid_amount", None)
                        doc.outstanding_amount = d.get("outstanding_amount", None)
                        doc.total = d.get("total", None)
                        doc.total_taxes_and_charges = d.get("total_taxes_and_charges", 0)
                        doc.taxes_and_charges = d.get("taxes_and_charges", 0)
                        doc.supplier = d.get("party_name", 0)
                        doc.party = d.get("party_name", 0)
                        if doc.outstanding_amount == '0':
                            doc.is_paid = 1
                            doc.mode_of_payment = "Cash"
                            doc.cash_bank_account = "Main Safe - TC"
                            doc.base_paid_amount = d.get("grand_total", None)
                            doc.plc_conversion_rate = 1

                        else:
                            doc.is_paid = 0
                            doc.base_paid_amount = 0

                        doc.status = d.get("status", 0)
                        if int(d.get("DocStatus", "0")) == 1:
                            doc.docstatus = 0
                        doc.company = d.get("company", 0)
                        doc.is_return = d.get("is_return", 0)
                        calculate_tax = Taxes_Calculation(d.get("taxes_and_charges", 0))
                        doc.taxes = []
                        doc.append('taxes', calculate_tax)


                        doc.posting_date = d.get("posting_date", 0)
                        doc.posting_time = d.get("posting_time", 0)
                        doc.transaction_type_name = d.get("transaction_type_name", 0)
                        doc.base_grand_total = d.get("grand_total", None)
                        doc.against_expense_account = "Cost Of Goods Sold I/C Sales - TC"
                        doc.apply_discount_on = "Grand Total"
                        doc.base_net_total = d.get("total", 0)

                        doc.base_rounded_total = 0
                        doc.base_rounding_adjustment = 0
                        doc.base_taxes_and_charges_added = d.get("total_taxes_and_charges", 0)
                        doc.base_taxes_and_charges_deducted = 0
                        doc.base_total = d.get("total", None)
                        doc.base_total_taxes_and_charges = d.get("total_taxes_and_charges", 0)
                        doc.base_write_off_amount = 0
                        doc.buying_price_list = "Standard Buying"
                        doc.company = d.get("company", None)
                        doc.conversion_rate = 1
                        doc.credit_to = "Consigned Payable - TC"
                        doc.currency = "AED"
                        doc.disable_rounded_total = 1
                        doc.discount_amount = 0
                        doc.doctype = "Purchase Invoice"
                        doc.idx = 0
                        doc.ignore_pricing_rule = 0
                        doc.is_opening = "No"
                        doc.total_commission = 0
                        doc.c_form_applicable = "No"
                        doc.is_subcontracted = "No"
                        doc.language = "en"
                        doc.letter_head = "DEMO Letter Head"
                        doc.net_total = d.get("total", None)
                        doc.party_account_currency = "AED"
                        # doc.creation = d.get("creation", currDate)
                        # doc.modified = d.get("modified", currDate)

                        doc.items = []
                        b = 1
                        if d['item'] != None and len(d['item']) > 0:
                            for d6 in d['item']:
                                f = doc.append('items', {})
                                # d = frappe.new_doc("Sales Invoice Item")
                                f.idx = b
                                f.parent = d6['parent']
                                f.item_name = d6['item_name']
                                f.qty = d6['qty']
                                f.rate = flt(d6['rate'])-(flt(d6['discount_amount'])/flt(d6['qty']))
                                f.amount = d6['amount']
                                # d.discount_amount = d6['discount_amount']
                                f.tax_amount = d6['tax_amount']
                                f.tax_rate = d6['tax_rate']
                                f.conversion_factor = 1
                                b = b + 1
                                f.actual_batch_qty = 0
                                f.actual_qty = 0
                                f.base_amount = d6['amount']
                                f.base_net_amount = d6['amount']
                                f.base_net_rate = flt(d6['rate'])-(flt(d6['discount_amount'])/flt(d6['qty']))
                                f.base_price_list_rate = flt(d6['rate'])-(flt(d6['discount_amount'])/flt(d6['qty']))
                                f.base_rate = flt(d6['rate'])-(flt(d6['discount_amount'])/flt(d6['qty']))
                                f.base_rate_with_margin = flt(d6['rate'])-(flt(d6['discount_amount'])/flt(d6['qty']))
                                f.cost_center = "Main - TC"
                                f.delivered_by_supplier = 0
                                f.delivered_qty = 0
                                f.description = d6['description']
                                f.doctype = "Purchase Invoice Item"
                                f.expense_account = "Cost Of Goods Sold I/C Sales - TC"
                                f.gross_profit = "-3"
                                f.has_batch_no = 0
                                f.has_serial_no = 0
                                # d.image = d9['image']
                                f.income_account = "Sales Account - TC"
                                f.is_fixed_asset = 0
                                f.item_code = d6['item_code']
                                f.item_group = d6['item_group']
                                f.item_tax_rate = "{}"
                                f.item_with_tax_amount = 0
                                f.margin_rate_or_amount = 0
                                f.net_amount = d6['amount']
                                f.net_rate = d6['amount']
                                f.parentfield = "items"
                                f.parenttype = "Purchase Invoice"
                                f.price_list_rate = flt(d6['rate'])-(flt(d6['discount_amount'])/flt(d6['qty']))
                                f.projected_qty = 0
                                f.rate_with_margin = flt(d6['rate'])-(flt(d6['discount_amount'])/flt(d6['qty']))
                                f.stock_qty = d6['qty']
                                f.stock_uom = d6['uom']
                                f.tax_amount = 0
                                f.tax_rate = 0
                                f.total_weight = 0
                                f.uom = d6['uom']
                                f.update_stock = 0
                                f.valuation_rate = 0
                                f.warehouse = "My Store - TC"
                                f.weight_per_unit = 0
                                f.__islocal = 1
                                f.__unsaved = 1

                        if (d.get("is_delete", 0) == "1"):
                          doc.delete()
                        else:

                            doc.save()

                            if int(d.get("DocStatus", "0")) == 1:
                                doc.run_method("on_submit")
                                frappe.db.set_value("Purchase Invoice", doc.get("name"), "docstatus", 1, update_modified=False)


                            frappe.db.set_value("Purchase Invoice", doc.get("name"), "modified", d.get("modified"),
                                            update_modified=False)

                  except Exception, ex:
                    print ex



                else:
                 if d['Invoice_type'] == "pr":
                    ############return invoice##############
                    try:
                        # insert

                        doc = frappe.new_doc("Purchase Invoice")
                        if doc.docstatus == 1 and int(d.get("DocStatus", "0")) != 2:
                            continue

                        doc.name = d.get("name", None)
                        doc.owner = d.get("owner", None)
                        doc.grand_total = -flt(d.get("grand_total", 0))
                        doc.paid_amount = -flt(d.get("paid_amount", 0))
                        doc.outstanding_amount = d.get("outstanding_amount", None)
                        doc.total = -flt(d.get("total", None))
                        doc.total_taxes_and_charges = -flt(d.get("total_taxes_and_charges", 0))
                        doc.taxes_and_charges = d.get("taxes_and_charges", 0)
                        doc.supplier = d.get("party_name", 0)
                        doc.party = d.get("party_name", 0)
                        doc.naming_series = "PR-"
                        if doc.outstanding_amount == '0':
                            doc.is_paid = 1
                            doc.mode_of_payment = "Cash"
                            doc.cash_bank_account = "Main Safe - TC"
                            doc.base_paid_amount = -flt(d.get("grand_total", None))
                            doc.plc_conversion_rate = 1
                            doc.is_return = 1
                            doc.return_against = d.get("return_against", None)

                        else:
                            doc.is_paid = 0
                            doc.base_paid_amount = 0

                        doc.status = d.get("status", 0)
                        if int(d.get("DocStatus", "0")) == 1:
                            doc.docstatus = 0
                        doc.company = d.get("company", 0)
                        doc.is_return = d.get("is_return", 0)
                        calculate_tax = Taxes_Calculation(d.get("taxes_and_charges", 0))
                        doc.taxes = []
                        doc.append('taxes', calculate_tax)

                        doc.posting_date = d.get("posting_date", 0)
                        doc.set_posting_time = 1
                        doc.posting_time = d.get("posting_time", 0)
                        doc.transaction_type_name = d.get("transaction_type_name", 0)
                        doc.base_grand_total = -flt(d.get("grand_total", None))
                        doc.against_expense_account = "Cost Of Goods Sold I/C Sales - TC"
                        doc.apply_discount_on = "Grand Total"
                        doc.base_net_total = -flt(d.get("total", 0))

                        doc.base_rounded_total = 0
                        doc.base_rounding_adjustment = 0
                        doc.base_taxes_and_charges_added = -flt(d.get("total_taxes_and_charges", 0))
                        doc.base_taxes_and_charges_deducted = 0
                        doc.base_total = -flt(d.get("total", None))
                        doc.base_total_taxes_and_charges = -flt(d.get("total_taxes_and_charges", 0))
                        doc.base_write_off_amount = 0
                        doc.write_off_amount = 0
                        doc.buying_price_list = "Standard Buying"
                        doc.company = d.get("company", None)
                        doc.conversion_rate = 1
                        doc.credit_to = "Consigned Payable - TC"
                        doc.currency = "AED"
                        doc.disable_rounded_total = 1
                        doc.discount_amount = 0
                        doc.doctype = "Purchase Invoice"
                        doc.idx = 0
                        doc.ignore_pricing_rule = 1
                        doc.is_opening = "No"
                        doc.is_subcontracted = "No"
                        doc.language = "en"
                        doc.letter_head = "DEMO Letter Head"
                        doc.net_total = d.get("total", None)
                        doc.party_account_currency = "AED"
                        doc.price_list_currency = "AED"
                        doc.select_print_heading = "Debit Note"
                        doc.set_posting_time = 1
                        doc.update_stock = 0
                        doc.write_off_account ="Other Payable - TC"
                        doc.write_off_cost_center = "Main - TC"

                        # doc.creation = d.get("creation", currDate)
                        # doc.modified = d.get("modified", currDate)

                        ##################purchase Invoice #############
                        doc.items = []
                        a = 1
                        if d['item'] != None and len(d['item']) > 0:
                            for d9 in d['item']:
                                f = doc.append('items', {})
                                # d = frappe.new_doc("Sales Invoice Item")
                                f.idx = a
                                f.parent = d9['parent']
                                f.item_name = d9['item_name']
                                f.qty = -flt(d9['qty'])
                                f.rate = d9['rate']
                                f.amount = -flt(d9['amount'])
                                # d.discount_amount = d9['discount_amount']
                                f.tax_amount = d9['tax_amount']
                                f.tax_rate = d9['tax_rate']
                                f.conversion_factor = 1
                                a = a + 1
                                f.actual_batch_qty = 0
                                f.actual_qty = 0
                                f.base_amount = -flt(d9['amount'])
                                f.base_net_amount =-flt(d9['amount'])
                                f.base_net_rate = d9['rate']
                                f.base_price_list_rate = d9['rate']
                                f.base_rate = d9['rate']
                                f.base_rate_with_margin = d9['rate']
                                f.cost_center = "Main - TC"
                                f.delivered_by_supplier = 0
                                f.delivered_qty = 0
                                f.description = d9['description']
                                f.doctype = "Purchase Invoice Item"
                                f.docstatus=0
                                f.expense_account = "Cost Of Goods Sold I/C Sales - TC"
                                f.gross_profit = "-3"
                                f.has_batch_no = 0
                                f.has_serial_no = 0
                                # d.image = d9['image']
                                f.income_account = "Sales Account - TC"
                                f.is_fixed_asset = 0
                                f.item_code = d9['item_code']
                                f.item_group = d9['item_group']
                                f.item_tax_rate = "{}"
                                f.item_with_tax_amount = 0
                                f.margin_rate_or_amount = 0
                                f.net_amount = -flt(d9['amount'])
                                f.net_rate = d9['amount']
                                f.parentfield = "items"
                                f.parenttype = "Purchase Invoice"
                                f.price_list_rate = d9['rate']
                                f.projected_qty = 0
                                f.rate_with_margin = d9['rate']
                                f.stock_qty = d9['qty']
                                f.received_qty = -flt(d9['qty'])
                                f.rejected_qty = 0
                                f.rejected_warehouse = "My Store - TC"
                                f.stock_uom = d9['uom']
                                f.tax_amount = d9['tax_amount']
                                f.tax_rate = d9['tax_rate']
                                f.total_weight = 0
                                f.valuation_rate = 0
                                f.uom = d9['uom']
                                f.update_stock = 0
                                f.valuation_rate = 0
                                f.warehouse = "My Store - TC"
                                f.weight_per_unit = 0
                                f.__islocal = 1
                                f.__unsaved = 1

                        #############################################
                        doc.save()

                        if int(d.get("DocStatus", "0")) == 1:
                            doc.run_method("on_submit")
                            frappe.db.set_value("Purchase Invoice", doc.get("name"), "docstatus", 1,
                                                update_modified=False)

                            update_tax_doscstatus("Purchase", doc.name)

                        frappe.rename_doc("Purchase Invoice", doc.name, d.get("name", None), ignore_permissions=True)

                        frappe.db.set_value("Purchase Invoice", doc.get("name"), "creation", d.get("modified"),
                                            update_modified=False)
                        frappe.db.set_value("Purchase Invoice", doc.get("name"), "modified", d.get("modified"),
                                            update_modified=False)


                    except Exception, ex:
                        print ex

                    #######################################
                 else:
                    try:
                    # insert

                        doc = frappe.new_doc("Purchase Invoice")
                        if doc.docstatus == 1 and int(d.get("DocStatus", "0")) != 2:
                            continue

                        doc.name = d.get("name", None)
                        doc.owner = d.get("owner", None)
                        doc.grand_total = d.get("grand_total", None)
                        doc.paid_amount = d.get("paid_amount", 0)
                        doc.outstanding_amount = d.get("outstanding_amount", None)
                        doc.total = d.get("total", None)
                        doc.total_taxes_and_charges = d.get("total_taxes_and_charges", 0)
                        doc.taxes_and_charges = d.get("taxes_and_charges", 0)
                        doc.supplier = d.get("party_name", 0)
                        doc.party = d.get("party_name", 0)
                        doc.naming_series = "PI-"
                        if  doc.outstanding_amount == '0':
                            doc.is_paid = 1
                            doc.mode_of_payment = "Cash"
                            doc.cash_bank_account = "Main Safe - TC"
                            doc.base_paid_amount = d.get("grand_total", None)
                            doc.plc_conversion_rate = 1

                        else:
                            if flt(d.get("paid_amount", 0)) > flt(0):
                                doc.is_paid = 1
                                doc.base_paid_amount = d.get("paid_amount", 0)
                                doc.mode_of_payment = "Cash"
                                doc.cash_bank_account = "Main Safe - TC"
                                doc.plc_conversion_rate = 1
                            else:
                                doc.is_paid = 0
                                doc.base_paid_amount = 0

                        doc.status = d.get("status", 0)
                        if int(d.get("DocStatus", "0")) == 1:
                            doc.docstatus = 0
                        doc.company = d.get("company", 0)
                        doc.is_return = d.get("is_return", 0)
                        calculate_tax = Taxes_Calculation(d.get("taxes_and_charges", 0))
                        doc.taxes = []
                        doc.append('taxes', calculate_tax)

                        doc.posting_date = d.get("posting_date", 0)
                        doc.set_posting_time = 1
                        doc.posting_time = d.get("posting_time", 0)
                        doc.transaction_type_name = d.get("transaction_type_name", 0)
                        doc.base_grand_total = d.get("grand_total", None)
                        doc.against_expense_account = "Cost Of Goods Sold I/C Sales - TC"
                        doc.apply_discount_on = "Grand Total"
                        doc.base_net_total="-"+d.get("total", 0)

                        doc.base_rounded_total = 0
                        doc.base_rounding_adjustment = 0
                        doc.base_taxes_and_charges_added = d.get("total_taxes_and_charges", 0)
                        doc.base_taxes_and_charges_deducted = 0
                        doc.base_total = d.get("total", None)
                        doc.base_total_taxes_and_charges=d.get("total_taxes_and_charges", 0)
                        doc.base_write_off_amount = 0
                        doc.buying_price_list = "Standard Buying"
                        doc.company = d.get("company", None)
                        doc.conversion_rate = 1
                        doc.credit_to = "Consigned Payable - TC"
                        doc.currency = "AED"
                        doc.disable_rounded_total=1
                        doc.discount_amount = 0
                        doc.doctype = "Purchase Invoice"
                        doc.idx = 0
                        doc.ignore_pricing_rule = 0
                        doc.is_opening = "No"
                        doc.is_subcontracted = "No"
                        doc.language = "en"
                        doc.letter_head = "DEMO Letter Head"
                        doc.net_total = d.get("total", None)
                        doc.party_account_currency = "AED"




                        # doc.creation = d.get("creation", currDate)
                        # doc.modified = d.get("modified", currDate)

                        ##################purchase Invoice #############
                        doc.items = []
                        a = 1
                        if d['item'] != None and len(d['item']) > 0:
                              for d9 in d['item']:
                                  f = doc.append('items', {})
                                  # d = frappe.new_doc("Sales Invoice Item")
                                  f.idx = a
                                  f.parent = d9['parent']
                                  f.item_name = d9['item_name']
                                  f.qty = d9['qty']
                                  f.rate = flt(d9['rate'])-(flt(d9['discount_amount'])/flt(d9['qty']))
                                  f.amount = d9['amount']
                                  # d.discount_amount = d9['discount_amount']
                                  f.tax_amount = d9['tax_amount']
                                  f.tax_rate = d9['tax_rate']
                                  f.conversion_factor = 1
                                  a = a + 1
                                  f.actual_batch_qty = 0
                                  f.actual_qty = 0
                                  f.base_amount = d9['amount']
                                  f.base_net_amount = d9['amount']
                                  f.base_net_rate = flt(d9['rate'])-(flt(d9['discount_amount'])/flt(d9['qty']))
                                  f.base_price_list_rate = flt(d9['rate'])-(flt(d9['discount_amount'])/flt(d9['qty']))
                                  f.base_rate = flt(d9['rate'])-(flt(d9['discount_amount'])/flt(d9['qty']))
                                  f.base_rate_with_margin = flt(d9['rate'])-(flt(d9['discount_amount'])/flt(d9['qty']))
                                  f.cost_center = "Main - TC"
                                  f.delivered_by_supplier = 0
                                  f.delivered_qty = 0
                                  f.description = d9['description']
                                  f.doctype = "Purchase Invoice Item"
                                  f.expense_account = "Cost Of Goods Sold I/C Sales - TC"
                                  f.gross_profit = "-3"
                                  f.has_batch_no = 0
                                  f.has_serial_no = 0
                                  # d.image = d9['image']
                                  f.income_account = "Sales Account - TC"
                                  f.is_fixed_asset = 0
                                  f.item_code = d9['item_code']
                                  f.item_group = d9['item_group']
                                  f.item_tax_rate = "{}"
                                  f.item_with_tax_amount = 0
                                  f.margin_rate_or_amount = 0
                                  f.net_amount = d9['amount']
                                  f.net_rate = d9['amount']
                                  f.parentfield = "items"
                                  f.parenttype = "Purchase Invoice"
                                  f.price_list_rate = flt(d9['rate'])-(flt(d9['discount_amount'])/flt(d9['qty']))
                                  f.projected_qty = 0
                                  f.rate_with_margin = flt(d9['rate'])-(flt(d9['discount_amount'])/flt(d9['qty']))
                                  f.stock_qty = d9['qty']
                                  f.stock_uom = d9['uom']
                                  f.tax_amount = 0
                                  f.tax_rate = 0
                                  f.total_weight = 0
                                  f.uom = d9['uom']
                                  f.update_stock = 0
                                  f.valuation_rate = 0
                                  f.warehouse = "My Store - TC"
                                  f.weight_per_unit = 0
                                  f.__islocal = 1
                                  f.__unsaved = 1



                        #############################################
                        doc.save()

                        if int(d.get("DocStatus", "0")) == 1:
                            doc.run_method("on_submit")
                            frappe.db.set_value("Purchase Invoice", doc.get("name"), "docstatus", 1, update_modified=False)
                            update_tax_doscstatus("Purchase", doc.name)

                        frappe.rename_doc("Purchase Invoice", doc.name, d.get("name", None), ignore_permissions=True)

                        if flt(d.get("paid_amount", None)) > flt(d.get("total", 0)):
                            frappe.db.set_value("Purchase Invoice", d.get("name"), "paid_amount", d.get("paid_amount", 0),
                                            update_modified=False)
                            frappe.db.set_value("Purchase Invoice", d.get("name"), "base_paid_amount", d.get("paid_amount", 0),
                                        update_modified=False)

                        frappe.db.set_value("Purchase Invoice", doc.get("name"), "creation", d.get("modified"),
                                            update_modified=False)
                        frappe.db.set_value("Purchase Invoice", doc.get("name"), "modified", d.get("modified"),
                                            update_modified=False)


                    except Exception, ex:
                      print ex



def sendItem(lastSyncDate):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d %H:%M:%S")
    from frappe.utils import now
    currDate = now()

    # filters = [
    #     ["modified", ">", lastSyncDate], ["modified", "<", currDate]
    # ]

    filters = [
        ["docstatus", "!=", 0]
    ]

    fields = ["name",
              "owner",
              "grand_total",
              "paid_amount",
              "return_against",
              "change_amount",
              "outstanding_amount",
              "total",
              "total_taxes_and_charges",
              "taxes_and_charges",
              "total_discount",
              "customer",
              "status",
              "docstatus",
              "company",
              "tax_id",
              "is_return",
              "posting_date",
              "posting_time",
              "transaction_type_name",
              "creation",
              "modified"
              ]

    doc_list = frappe.get_all("Sales Invoice", fields=fields, filters=filters)
    # doc_list = frappe.get_all("Sales Invoice", fields=fields)
    for doc_list_all in doc_list:
        if doc_list_all.is_return > 0:
          doc_list_all.Invoice_type = "sr"

        else:
          doc_list_all.Invoice_type = "si"


        filtersItem = [
                ["parent", "=", doc_list_all.name]
            ]
        fieldsItem = ["parent",
                              "item_name",
                              "qty",
                              "rate",
                              "amount",
                              "discount_amount",
                              "tax_amount",
                              "tax_rate",
                              "DocStatus",
                            ]

        doc_list_all.item = frappe.get_all("Sales Invoice Item", fields=fieldsItem, filters=filtersItem)

    fields1 = ["name",
                   "owner",
                   "grand_total",
                   "paid_amount",
                   "return_against",
                   # "change_amount",
                   "outstanding_amount",
                   "total",
                   "total_taxes_and_charges",
                   "taxes_and_charges",
                   # "total_discount",
                   "supplier",
                   "status",
                   "docstatus",
                   "company",
                   # "tax_id",
                   "is_return",
                   "posting_date",
                   "posting_time",
                   "transaction_type_name",
                    "creation",
                    "modified"

               ]
    doc_list1 = frappe.get_all("Purchase Invoice", fields=fields1, filters=filters)
        # doc_list1 = frappe.get_all("Purchase Invoice", fields=fields1)
    for doc_list_all in doc_list1:
            if doc_list_all.is_return > 0:
                doc_list_all.Invoice_type = "pr"
            else:
                doc_list_all.Invoice_type = "pi"
            filtersItems = [
                ["parent", "=", doc_list_all.name]
            ]
            fieldsItem = ["parent",
                          "item_name",
                          "qty",
                          "rate",
                          "amount",
                          # "discount_amount",
                          "tax_amount",
                          "tax_rate",
                          "DocStatus"
                          ]

            doc_list_all.item = frappe.get_all("Purchase Invoice Item", fields=fieldsItem, filters=filtersItems)
            doc_list.append(doc_list_all)

    status = 0

    if doc_list != None:
        if len(doc_list) > 0:

             if doc_list == None:
               doc_list = doc_list_all
               status = 1
             else:
                 status = 1


    return {
        "data": doc_list,
        # "InvoiceType": InvoiceType,
        "newSyncDate": currDate,
        "status": status
    }


def Taxes_Calculation(taxes_name):
    # sql = """SELECT full_name FROM tabUser WHERE NAME='{0}' LIMIT 1""".format(self.owner)
    sql = """SELECT * from `tabSales Taxes and Charges` WHERE parentfield = 'taxes' and parenttype = 'Sales Taxes and Charges Template' 
            and parent='{0}' LIMIT 1""".format(taxes_name)
    Taxes_list = frappe.db.sql(sql, as_dict=1)
    if (len(Taxes_list) > 0):
        taxes = Taxes_list[0]

    return taxes

def update_tax_doscstatus(type, name):
    sql = """UPDATE
`tab{0} Invoice` si
INNER JOIN `tab{0} Invoice Item` sii ON (si.name = sii.parent and si.docstatus = 1)
INNER JOIN `tab{0} Taxes and Charges` stc ON (si.name = stc.parent and si.docstatus = 1)
SET sii.docstatus = 1 , stc.docstatus = 1
WHERE si.name = '{1}' """.format(type, name)

    frappe.db.sql(sql)

def logDataInsert(data,user_name,ip_address,handset_model,os_version):
    from frappe.utils import now
    currDate = now()
    try:
            doc = frappe.new_doc("Log")
            doc.data_json = json.dumps(data)
            doc.user_name = user_name
            doc.ip_address = ip_address
            doc.handset_model = handset_model
            doc.os_version = os_version
            doc.curr_date = currDate
            doc.api_type = "Invoice"
            doc.creation = currDate
            doc.modified = currDate

            doc.save()

    except Exception, ex:
        print ex