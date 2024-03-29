# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import json

import frappe, erpnext
import frappe.defaults
from frappe.utils import cint, flt
from frappe import _, msgprint, throw
from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.controllers.stock_controller import update_gl_entries_after
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.doctype.sales_invoice.pos import update_multi_mode_option

from erpnext.controllers.selling_controller import SellingController
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.doctype.delivery_note.delivery_note import update_billed_amount_based_on_so
from erpnext.projects.doctype.timesheet.timesheet import get_projectwise_timesheet_data
from erpnext.accounts.doctype.asset.depreciation \
    import get_disposal_account_and_cost_center, get_gl_entries_on_asset_disposal
from erpnext.stock.doctype.batch.batch import set_batch_nos
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, get_delivery_note_serial_no
from erpnext.setup.doctype.company.company import update_company_current_month_sales
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center

form_grid_templates = {
    "items": "templates/form_grid/item_grid.html"
}


class SalesInvoice(SellingController):
    def __init__(self, *args, **kwargs):
        super(SalesInvoice, self).__init__(*args, **kwargs)
        self.status_updater = [{
            'source_dt': 'Sales Invoice Item',
            'target_field': 'billed_amt',
            'target_ref_field': 'amount',
            'target_dt': 'Sales Order Item',
            'join_field': 'so_detail',
            'target_parent_dt': 'Sales Order',
            'target_parent_field': 'per_billed',
            'source_field': 'amount',
            'join_field': 'so_detail',
            'percent_join_field': 'sales_order',
            'status_field': 'billing_status',
            'keyword': 'Billed',
            'overflow_type': 'billing'
        }]

    def set_indicator(self):
        """Set indicator for portal"""
        if self.outstanding_amount > 0:
            self.indicator_color = "orange"
            self.indicator_title = _("Unpaid")
        else:
            self.indicator_color = "green"
            self.indicator_title = _("Paid")

    def before_insert(self):
        self.check_actual_qty()

    def validate(self):
        self.validate_rounding_adjustment()
        # if self.update_stock == 1:
        #     self.update_stock_ledger()
        self.set_letter_head()
        super(SalesInvoice, self).validate()
        self.validate_auto_set_posting_time()

        if not self.is_pos:
            self.so_dn_required()

        self.validate_proj_cust()
        self.validate_with_previous_doc()
        self.validate_uom_is_integer("stock_uom", "stock_qty")
        self.validate_uom_is_integer("uom", "qty")
        self.check_close_sales_order("sales_order")
        self.validate_debit_to_acc()
        self.clear_unallocated_advances("Sales Invoice Advance", "advances")
        self.add_remarks()
        self.validate_write_off_account()
        self.validate_account_for_change_amount()
        self.validate_fixed_asset()
        self.set_income_account_for_fixed_assets()

        if cint(self.is_pos):
            self.validate_pos()

        if cint(self.update_stock):
            self.validate_dropship_item()
            self.validate_item_code()
            self.validate_warehouse()
            self.update_current_stock()
            self.validate_delivery_note()

        if not self.is_opening:
            self.is_opening = 'No'

        if self._action != 'submit' and self.update_stock and not self.is_return:
            set_batch_nos(self, 'warehouse', True)

        self.set_against_income_account()
        self.validate_c_form()
        self.validate_time_sheets_are_submitted()
        self.validate_multiple_billing("Delivery Note", "dn_detail", "amount", "items")
        if not self.is_return:
            self.validate_serial_numbers()
        self.update_packing_list()
        self.set_billing_hours_and_amount()
        self.update_timesheet_billing_for_project()
        self.set_status()

        # self.validate_transaction_count()
        self.validate_cost_price()
        self.validate_purchase_invoice()
        # frappe.db.set(self, 'lpo', self.name)

        self.validate_valuation_rate()

    def validate_rounding_adjustment(self):
        if self.is_return == 1:
            return
        import math
        if self.grand_total:

            # point = math.modf(self.grand_total)
            point = math.modf(self.net_total + self.total_taxes_and_charges)
            rounded_adj = point[0]
            rounded_total = flt(0.0)
            # round = False
            if rounded_adj >= 0.75 and rounded_adj < 1:
                rounded_total = 1 - rounded_adj

            elif rounded_adj >= 0.50 and rounded_adj < 0.75:
                rounded_total = 0.75 - rounded_adj

            elif rounded_adj >= 0.25 and rounded_adj < 0.50:
                rounded_total = 0.50 - rounded_adj

            elif rounded_adj >= 0.0 and rounded_adj < 0.25:
                rounded_total = 0.25 - rounded_adj

            # rounding_adjustment = flt(self.rounding_adjustment, 6)
            if self.rounding_adjustment <= flt(rounded_total, 6) and self.rounding_adjustment < 0.25:
                self.rounded_total = self.grand_total + self.rounding_adjustment
                # self.grand_total = self.grand_total + self.rounding_adjustment
                # frappe.db.set(self, 'grand_total', self.grand_total + self.rounding_adjustment)
                # frappe.db.set(self, 'base_grand_total', self.grand_total + self.rounding_adjustment)
            else:
                frappe.throw('Rounding adjustment cannot be greater than {0}'.format(rounded_total))

        frappe.db.commit()

    def validate_cost_price(self):
        if self.transaction_type_name == 'Profit Margin':
            for i in self.items:
                if i.cost_price == None:
                    frappe.throw(_("Cost Price is mandatory"))

    def set_letter_head(self):
        sql = """SELECT `tabPOS Profile`.letter_head FROM `tabUser` JOIN `tabPOS Profile` ON `tabUser`.NAME=`tabPOS Profile`.USER WHERE `tabUser`.NAME='{0}'
""".format(frappe.session.user)
        letter_head = frappe.db.sql(sql, as_dict=1)
        for lh in letter_head:
            if lh.letter_head != None:
                self.letter_head = lh.letter_head
                frappe.db.commit()

    def validate_purchase_invoice(self):
        if (
                self.transaction_type_name == 'Profit Margin' or self.transaction_type_name == 'RCM Supplies') and self.purchase_invoice == None:
            frappe.throw(_("Purchase Invoice is not selected"))

    def validate_transaction_count(self):
        try:
            from frappe import conf
            limits = conf.get("limits")
            item_limit = limits['transaction_limits']['sales_invoice']

            sql = """select count(*) cnt from `tabSales Invoice`"""
            data = frappe.db.sql(sql, as_dict=1)
            if (data):
                d = data[0]
                if (d.cnt > item_limit):
                    frappe.throw("You have reached your max limit. Please contact support")

        except Exception, ex:
            pass

    def before_save(self):
        set_account_for_mode_of_payment(self)

    def on_submit(self):
        self.validate_pos_paid_amount()

        if not self.subscription:
            frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
                                                                                 self.company, self.base_grand_total,
                                                                                 self)

        self.check_prev_docstatus()

        if self.is_return:
            # NOTE status updating bypassed for is_return
            self.status_updater = []

        self.update_status_updater_args()
        self.update_prevdoc_status()
        self.update_billing_status_in_dn()
        self.clear_unallocated_mode_of_payments()

        # Updating stock ledger should always be called after updating prevdoc status,
        # because updating reserved qty in bin depends upon updated delivered qty in SO
        if self.update_stock == 1:
            self.update_stock_ledger()

        # this sequence because outstanding may get -ve
        self.make_gl_entries()

        if not self.is_return:
            self.update_billing_status_for_zero_amount_refdoc("Sales Order")
            self.check_credit_limit()

        self.update_serial_no()

        if not cint(self.is_pos) == 1 and not self.is_return:
            self.update_against_document_in_jv()

        self.update_time_sheet(self.name)

        self.update_current_month_sales()

    def validate_pos_paid_amount(self):
        if len(self.payments) == 0 and self.is_pos:
            frappe.throw(_("At least one mode of payment is required for POS invoice."))

    def before_cancel(self):
        self.update_time_sheet(None)

    def on_cancel(self):
        self.check_close_sales_order("sales_order")

        from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries
        if frappe.db.get_single_value('Accounts Settings', 'unlink_payment_on_cancellation_of_invoice'):
            unlink_ref_doc_from_payment_entries(self)

        if self.is_return:
            # NOTE status updating bypassed for is_return
            self.status_updater = []

        self.update_status_updater_args()
        self.update_prevdoc_status()
        self.update_billing_status_in_dn()

        if not self.is_return:
            self.update_billing_status_for_zero_amount_refdoc("Sales Order")
            self.update_serial_no(in_cancel=True)

        self.validate_c_form_on_cancel()

        # Updating stock ledger should always be called after updating prevdoc status,
        # because updating reserved qty in bin depends upon updated delivered qty in SO
        if self.update_stock == 1:
            self.update_stock_ledger()

        self.make_gl_entries_on_cancel()
        frappe.db.set(self, 'status', 'Cancelled')

        self.update_current_month_sales()

    def update_current_month_sales(self):
        if frappe.flags.in_test:
            update_company_current_month_sales(self.company)
        else:
            frappe.enqueue('erpnext.setup.doctype.company.company.update_company_current_month_sales',
                           company=self.company)

    def update_status_updater_args(self):
        if cint(self.update_stock):
            self.status_updater.extend([{
                'source_dt': 'Sales Invoice Item',
                'target_dt': 'Sales Order Item',
                'target_parent_dt': 'Sales Order',
                'target_parent_field': 'per_delivered',
                'target_field': 'delivered_qty',
                'target_ref_field': 'qty',
                'source_field': 'qty',
                'join_field': 'so_detail',
                'percent_join_field': 'sales_order',
                'status_field': 'delivery_status',
                'keyword': 'Delivered',
                'second_source_dt': 'Delivery Note Item',
                'second_source_field': 'qty',
                'second_join_field': 'so_detail',
                'overflow_type': 'delivery',
                'extra_cond': """ and exists(select name from `tabSales Invoice`
					where name=`tabSales Invoice Item`.parent and update_stock = 1)"""
            },
                {
                    'source_dt': 'Sales Invoice Item',
                    'target_dt': 'Sales Order Item',
                    'join_field': 'so_detail',
                    'target_field': 'returned_qty',
                    'target_parent_dt': 'Sales Order',
                    # 'target_parent_field': 'per_delivered',
                    # 'target_ref_field': 'qty',
                    'source_field': '-1 * qty',
                    # 'percent_join_field': 'sales_order',
                    # 'overflow_type': 'delivery',
                    'extra_cond': """ and exists (select name from `tabSales Invoice` where name=`tabSales Invoice Item`.parent and update_stock=1 and is_return=1)"""
                }
            ])

    def check_credit_limit(self):
        from erpnext.selling.doctype.customer.customer import check_credit_limit

        validate_against_credit_limit = False
        for d in self.get("items"):
            if not (d.sales_order or d.delivery_note):
                validate_against_credit_limit = True
                break
        if validate_against_credit_limit:
            check_credit_limit(self.customer, self.company)

    def set_missing_values(self, for_validate=False):
        pos = self.set_pos_fields(for_validate)

        if not self.debit_to:
            self.debit_to = get_party_account("Customer", self.customer, self.company)
        if not self.due_date and self.customer:
            self.due_date = get_due_date(self.posting_date, "Customer", self.customer)

        super(SalesInvoice, self).set_missing_values(for_validate)

        if pos:
            return {"print_format": pos.get("print_format_for_online")}

    def update_time_sheet(self, sales_invoice):
        for d in self.timesheets:
            if d.time_sheet:
                timesheet = frappe.get_doc("Timesheet", d.time_sheet)
                self.update_time_sheet_detail(timesheet, d, sales_invoice)
                timesheet.calculate_total_amounts()
                timesheet.calculate_percentage_billed()
                timesheet.flags.ignore_validate_update_after_submit = True
                timesheet.set_status()
                timesheet.save()

    def update_time_sheet_detail(self, timesheet, args, sales_invoice):
        for data in timesheet.time_logs:
            if (self.project and args.timesheet_detail == data.name) or \
                    (not self.project and not data.sales_invoice) or \
                    (not sales_invoice and data.sales_invoice == self.name):
                data.sales_invoice = sales_invoice

    def on_update(self):
        if self.update_stock == 1:
            self.check_actual_qty()
        self.set_paid_amount()
        self.set_company_pos_address()
        self.set_served_by()
        self.set_company_vat_number_and_logo()
        self.discount_amount_changes()
        self.calculate_taxrate_taxamount()
        self.update_sales_tax_and_charges()
        self.ship_to_address()
        self.set_total_dicount()
        self.ship_to_name_change()
        self.contact_person_display_ship()
        # frappe.db.set(self, 'lpo', self.name)

    def check_actual_qty(self):

        for i in self.items:
            is_update_stock_check = """SELECT is_stock_item FROM `tabItem` WHERE item_code='{0}' LIMIT 1""".format(
                i.item_code)
            stock_list = frappe.db.sql(is_update_stock_check, as_dict=1)

            for j in stock_list:
                if j.is_stock_item == 1:
                    sql = """select actual_qty from `tabBin` where item_code ='{0}' and warehouse ='{1}' LIMIT 1""".format(
                        i.item_code, i.warehouse)
                    item_list = frappe.db.sql(sql, as_dict=1)

                    if len(item_list) > 0:
                        for a in item_list:
                            if i.qty > a['actual_qty']:
                                frappe.throw(_("1.0 units of {0} needed in {1} to complete this transaction.").format(
                                    i.item_code, i.warehouse))
                    else:
                        frappe.throw(_("Stock is not available in this warehouse"))

    def ship_to_name_change(self):
        if self.ship_to == None:
            ship_to = self.customer
            ship_to_name = self.customer_name
            ship_address = self.address_display
            frappe.db.set(self, 'ship_to', ship_to)
            frappe.db.set(self, 'ship_to_name', ship_to_name)
            frappe.db.set(self, 'ship_address', ship_address)

    def ship_to_address(self):
        ship_add = get_customer_ship_address(self.ship_to)
        frappe.db.set(self, 'ship_address', ship_add)

    def set_company_pos_address(self):
        pos_add = get_company_pos_address()
        frappe.db.set(self, 'company_pos_address', pos_add)

    def set_served_by(self):
        sql = """SELECT full_name FROM tabUser WHERE NAME='{0}' LIMIT 1""".format(self.owner)
        user_list = frappe.db.sql(sql, as_dict=1)
        if (len(user_list) > 0):
            user = user_list[0]
            frappe.db.set(self, 'served_by', user.full_name)

    def set_company_vat_number_and_logo(self):
        sql = """SELECT vat_number, pos_logo FROM tabCompany LIMIT 1"""
        compnay_list = frappe.db.sql(sql, as_dict=1)
        if (len(compnay_list) > 0):
            compnay = compnay_list[0]
            frappe.db.set(self, 'vat_number', compnay.vat_number)
            frappe.db.set(self, 'pos_logo', compnay.pos_logo)

    def set_total_dicount(self):
        try:
            tot_disc = 0
            for i in self.items:
                tot_disc = tot_disc + ((i.price_list_rate - i.rate) * i.qty)

            sub_total = self.net_total + tot_disc
            if self.is_pos > 0:
                frappe.db.set_value("Sales Invoice", self.name, "total_discount", tot_disc, update_modified=False)
                frappe.db.set_value("Sales Invoice", self.name, "sub_total", sub_total, update_modified=False)
            else:
                frappe.db.set(self, 'sub_total', sub_total)
                frappe.db.set(self, 'total_discount', tot_disc)
                frappe.db.commit()

        except Exception, ex:
            print(ex)
            pass

    def discount_amount_changes(self):
        try:
            for i in self.items:
                if i.discount_amount > 0:
                    if self.is_return > 0:
                        rate = i.price_list_rate + (i.discount_amount / i.qty)
                    else:
                        rate = i.price_list_rate - (i.discount_amount / i.qty)

                    amount = rate * i.qty
                    i.rate = rate
                    i.amount = amount
                    frappe.db.set_value("Sales Invoice Item", i.name, "rate", rate, update_modified=False)
                    frappe.db.set_value("Sales Invoice Item", i.name, "amount", amount, update_modified=False)

        except Exception:
            pass

    def set_paid_amount(self):
        paid_amount = 0.0
        base_paid_amount = 0.0
        for data in self.payments:
            data.base_amount = flt(data.amount * self.conversion_rate, self.precision("base_paid_amount"))
            paid_amount += data.amount
            base_paid_amount += data.base_amount

        self.paid_amount = paid_amount
        self.base_paid_amount = base_paid_amount

    def calculate_taxrate_taxamount(self):

        add = frappe.db.sql("SELECT included_in_print_rate FROM `tabSales Taxes and Charges` WHERE parent=%s",
                            self.taxes_and_charges, as_dict=1)

        for d in add:
            if d.included_in_print_rate == 1:
                self.taxrate_taxamount_inculsive()
            else:
                self.taxrate_taxamount_exculsive()

    def taxrate_taxamount_exculsive(self):
        try:
            for allitems in self.items:
                for taxRow in self.taxes:

                    tax_rate = taxRow.rate
                    tax_amount = (allitems.amount * (tax_rate / 100))
                    item_with_tax_amount = allitems.amount + tax_amount
                    if self.docstatus == 0:
                        allitems.tax_rate = tax_rate
                        allitems.tax_amount = tax_amount
                        allitems.item_with_tax_amount = item_with_tax_amount
                        allitems.save()
                    else:
                        frappe.db.set_value("Sales Invoice Item", allitems.name, "tax_rate", tax_rate,
                                            update_modified=False)
                        frappe.db.set_value("Sales Invoice Item", allitems.name, "tax_amount", tax_amount,
                                            update_modified=False)
                        frappe.db.set_value("Sales Invoice Item", allitems.name, "item_with_tax_amount",
                                            item_with_tax_amount, update_modified=False)
        except Exception, ex:
            print ex

    def taxrate_taxamount_inculsive(self):
        try:
            for allitems in self.items:
                for taxRow in self.taxes:

                    tax_rate = taxRow.rate
                    tax_val = ((tax_rate / 100) + 1)
                    z = (allitems.amount / tax_val)
                    tax_amount = allitems.amount - z
                    item_with_tax_amount = allitems.amount + tax_amount
                    if self.docstatus == 0:
                        allitems.tax_rate = tax_rate
                        allitems.tax_amount = tax_amount
                        allitems.item_with_tax_amount = item_with_tax_amount
                        allitems.save()
                    else:
                        frappe.db.set_value("Sales Invoice Item", allitems.name, "tax_rate", tax_rate,
                                            update_modified=False)
                        frappe.db.set_value("Sales Invoice Item", allitems.name, "tax_amount", tax_amount,
                                            update_modified=False)
                        frappe.db.set_value("Sales Invoice Item", allitems.name, "item_with_tax_amount",
                                            item_with_tax_amount, update_modified=False)
        except Exception, ex:
            print ex

    def update_sales_tax_and_charges(self):
        data_dict = {}
        # for i in self.items:
        #     tax_list = [i.tax_rate, i.tax_amount]
        #     data_dict[i.item_code] = tax_list
        # data_dict = json.dumps(data_dict)

        for i in self.items:
            old_tax_amount = 0
            old_tax_list = data_dict.get(i.item_code, None)

            if old_tax_list != None:
                old_tax_amount = old_tax_list[1]

            tax_list = [i.tax_rate, i.tax_amount + old_tax_amount]
            data_dict[i.item_code] = tax_list

        data_dict = json.dumps(data_dict)

        sql = """ UPDATE `tabSales Taxes and Charges` SET item_wise_tax_detail = '{0}' WHERE parent = '{1}'  """.format(
            data_dict, self.name)
        frappe.db.sql(sql)
        frappe.db.commit()

        self.update_tax_breakup()
        self.update_tax_on_items()

    def update_tax_breakup(self):
        doc = frappe.get_doc("Sales Invoice", self.name)
        from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_html
        new_html = get_itemised_tax_breakup_html(doc)
        # frappe.db.set_value("Sales Invoice", doc.name, "other_charges_calculation", new_html, update_modified=False)
        self.other_charges_calculation = new_html
        self.db_update()

    def update_tax_on_items(self):
        filters = [{"parent": self.taxes_and_charges}]
        fields = ["name", "account_head", "rate"]
        doc_list = frappe.get_all("Sales Taxes and Charges", filters=filters, fields=fields)
        for d in doc_list:
            for i in self.items:
                data_dict = {}
                data_dict[d.get("account_head")] = d.get("rate")
                data_dict = json.dumps(data_dict)
                i.item_tax_rate = data_dict
                frappe.db.set_value("Sales Invoice Item", i.name, "item_tax_rate", data_dict, update_modified=False)

    def validate_time_sheets_are_submitted(self):
        for data in self.timesheets:
            if data.time_sheet:
                status = frappe.db.get_value("Timesheet", data.time_sheet, "status")
                if status not in ['Submitted', 'Payslip']:
                    frappe.throw(_("Timesheet {0} is already completed or cancelled").format(data.time_sheet))

    def set_pos_fields(self, for_validate=False):
        """Set retail related fields from POS Profiles"""
        if cint(self.is_pos) != 1:
            return

        from erpnext.stock.get_item_details import get_pos_profile_item_details, get_pos_profile
        if not self.pos_profile:
            pos_profile = get_pos_profile(self.company) or {}
            self.pos_profile = pos_profile.get('name')

        pos = {}
        if self.pos_profile:
            pos = frappe.get_doc('POS Profile', self.pos_profile)

        if not self.get('payments') and not for_validate:
            update_multi_mode_option(self, pos)

        if not self.account_for_change_amount:
            self.account_for_change_amount = frappe.db.get_value('Company', self.company, 'default_cash_account')

        if pos:
            if not for_validate and not self.customer:
                self.customer = pos.customer

            if pos.get('account_for_change_amount'):
                self.account_for_change_amount = pos.get('account_for_change_amount')

            for fieldname in ('territory', 'naming_series', 'currency', 'taxes_and_charges', 'letter_head', 'tc_name',
                              'selling_price_list', 'company', 'select_print_heading', 'cash_bank_account',
                              'write_off_account', 'write_off_cost_center', 'apply_discount_on'):
                if (not for_validate) or (for_validate and not self.get(fieldname)):
                    self.set(fieldname, pos.get(fieldname))

            if not for_validate:
                self.update_stock = cint(pos.get("update_stock"))

            # set pos values in items
            for item in self.get("items"):
                if item.get('item_code'):
                    for fname, val in get_pos_profile_item_details(pos,
                                                                   frappe._dict(item.as_dict()), pos).items():

                        if (not for_validate) or (for_validate and not item.get(fname)):
                            item.set(fname, val)

            # fetch terms
            if self.tc_name and not self.terms:
                self.terms = frappe.db.get_value("Terms and Conditions", self.tc_name, "terms")

            # fetch charges
            if self.taxes_and_charges and not len(self.get("taxes")):
                self.set_taxes()

        return pos

    def get_company_abbr(self):
        return frappe.db.sql("select abbr from tabCompany where name=%s", self.company)[0][0]

    def validate_debit_to_acc(self):
        account = frappe.db.get_value("Account", self.debit_to,
                                      ["account_type", "report_type", "account_currency"], as_dict=True)

        if not account:
            frappe.throw(_("Debit To is required"))

        if account.report_type != "Balance Sheet":
            frappe.throw(_("Debit To account must be a Balance Sheet account"))

        if self.customer and account.account_type != "Receivable":
            frappe.throw(_("Debit To account must be a Receivable account"))

        self.party_account_currency = account.account_currency

    def clear_unallocated_mode_of_payments(self):
        self.set("payments", self.get("payments", {"amount": ["not in", [0, None, ""]]}))

        frappe.db.sql("""delete from `tabSales Invoice Payment` where parent = %s
			and amount = 0""", self.name)

    def validate_with_previous_doc(self):
        super(SalesInvoice, self).validate_with_previous_doc({
            "Sales Order": {
                "ref_dn_field": "sales_order",
                "compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
            },
            "Sales Order Item": {
                "ref_dn_field": "so_detail",
                "compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
                "is_child_table": True,
                "allow_duplicate_prev_row_id": True
            },
            "Delivery Note": {
                "ref_dn_field": "delivery_note",
                "compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
            },
            "Delivery Note Item": {
                "ref_dn_field": "dn_detail",
                "compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
                "is_child_table": True,
                "allow_duplicate_prev_row_id": True
            },
        })

        if cint(frappe.db.get_single_value('Selling Settings', 'maintain_same_sales_rate')) and not self.is_return:
            self.validate_rate_with_reference_doc([
                ["Sales Order", "sales_order", "so_detail"],
                ["Delivery Note", "delivery_note", "dn_detail"]
            ])

    def set_against_income_account(self):
        """Set against account for debit to account"""
        against_acc = []
        for d in self.get('items'):
            if d.income_account not in against_acc:
                against_acc.append(d.income_account)
        self.against_income_account = ','.join(against_acc)

    def add_remarks(self):
        if not self.remarks: self.remarks = 'No Remarks'

    def validate_auto_set_posting_time(self):
        # Don't auto set the posting date and time if invoice is amended
        if self.is_new() and self.amended_from:
            self.set_posting_time = 1

        self.validate_posting_time()

    def so_dn_required(self):
        """check in manage account if sales order / delivery note required or not."""
        dic = {'Sales Order': ['so_required', 'is_pos'], 'Delivery Note': ['dn_required', 'update_stock']}
        for i in dic:
            if frappe.db.get_value('Selling Settings', None, dic[i][0]) == 'Yes':
                for d in self.get('items'):
                    if frappe.db.get_value('Item', d.item_code, 'is_stock_item') == 1 \
                            and not d.get(i.lower().replace(' ', '_')) and not self.get(dic[i][1]):
                        msgprint(_("{0} is mandatory for Item {1}").format(i, d.item_code), raise_exception=1)

    def validate_proj_cust(self):
        """check for does customer belong to same project as entered.."""
        if self.project and self.customer:
            res = frappe.db.sql("""select name from `tabProject`
				where name = %s and (customer = %s or customer is null or customer = '')""",
                                (self.project, self.customer))
            if not res:
                throw(_("Customer {0} does not belong to project {1}").format(self.customer, self.project))

    def validate_pos(self):
        if self.is_return:
            if flt(self.paid_amount) + flt(self.write_off_amount) - flt(self.grand_total) < \
                    1 / (10 ** (self.precision("grand_total") + 1)):
                frappe.throw(_("Paid amount + Write Off Amount can not be greater than Grand Total"))

    def validate_item_code(self):
        for d in self.get('items'):
            if not d.item_code:
                msgprint(_("Item Code required at Row No {0}").format(d.idx), raise_exception=True)

    def validate_warehouse(self):
        super(SalesInvoice, self).validate_warehouse()

        for d in self.get_item_list():
            if not d.warehouse and frappe.db.get_value("Item", d.item_code, "is_stock_item"):
                frappe.throw(_("Warehouse required for stock Item {0}").format(d.item_code))

    def validate_delivery_note(self):
        for d in self.get("items"):
            if d.delivery_note:
                msgprint(_("Stock cannot be updated against Delivery Note {0}").format(d.delivery_note),
                         raise_exception=1)

    def validate_write_off_account(self):
        if flt(self.write_off_amount) and not self.write_off_account:
            self.write_off_account = frappe.db.get_value('Company', self.company, 'write_off_account')

        if flt(self.write_off_amount) and not self.write_off_account:
            msgprint(_("Please enter Write Off Account"), raise_exception=1)

    def validate_account_for_change_amount(self):
        if flt(self.change_amount) and not self.account_for_change_amount:
            msgprint(_("Please enter Account for Change Amount"), raise_exception=1)

    def validate_c_form(self):
        """ Blank C-form no if C-form applicable marked as 'No'"""
        if self.amended_from and self.c_form_applicable == 'No' and self.c_form_no:
            frappe.db.sql("""delete from `tabC-Form Invoice Detail` where invoice_no = %s
					and parent = %s""", (self.amended_from, self.c_form_no))

            frappe.db.set(self, 'c_form_no', '')

    def validate_c_form_on_cancel(self):
        """ Display message if C-Form no exists on cancellation of Sales Invoice"""
        if self.c_form_applicable == 'Yes' and self.c_form_no:
            msgprint(_("Please remove this Invoice {0} from C-Form {1}")
                     .format(self.name, self.c_form_no), raise_exception=1)

    def validate_dropship_item(self):
        for item in self.items:
            if item.sales_order:
                if frappe.db.get_value("Sales Order Item", item.so_detail, "delivered_by_supplier"):
                    frappe.throw(_("Could not update stock, invoice contains drop shipping item."))

    def update_current_stock(self):
        for d in self.get('items'):
            if d.item_code and d.warehouse:
                bin = frappe.db.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s",
                                    (d.item_code, d.warehouse), as_dict=1)
                d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0

        for d in self.get('packed_items'):
            bin = frappe.db.sql(
                "select actual_qty, projected_qty from `tabBin` where item_code =	%s and warehouse = %s",
                (d.item_code, d.warehouse), as_dict=1)
            d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0
            d.projected_qty = bin and flt(bin[0]['projected_qty']) or 0

    def update_packing_list(self):
        if cint(self.update_stock) == 1:
            from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
            make_packing_list(self)
        else:
            self.set('packed_items', [])

    def set_billing_hours_and_amount(self):
        if not self.project:
            for timesheet in self.timesheets:
                ts_doc = frappe.get_doc('Timesheet', timesheet.time_sheet)
                if not timesheet.billing_hours and ts_doc.total_billable_hours:
                    timesheet.billing_hours = ts_doc.total_billable_hours

                if not timesheet.billing_amount and ts_doc.total_billable_amount:
                    timesheet.billing_amount = ts_doc.total_billable_amount

    def update_timesheet_billing_for_project(self):
        if not self.timesheets and self.project:
            self.add_timesheet_data()
        else:
            self.calculate_billing_amount_for_timesheet()

    def add_timesheet_data(self):
        self.set('timesheets', [])
        if self.project:
            for data in get_projectwise_timesheet_data(self.project):
                self.append('timesheets', {
                    'time_sheet': data.parent,
                    'billing_hours': data.billing_hours,
                    'billing_amount': data.billing_amt,
                    'timesheet_detail': data.name
                })

            self.calculate_billing_amount_for_timesheet()

    def calculate_billing_amount_for_timesheet(self):
        total_billing_amount = 0.0
        for data in self.timesheets:
            if data.billing_amount:
                total_billing_amount += data.billing_amount

        self.total_billing_amount = total_billing_amount

    def get_warehouse(self):
        user_pos_profile = frappe.db.sql("""select name, warehouse from `tabPOS Profile`
			where ifnull(user,'') = %s and company = %s""", (frappe.session['user'], self.company))
        warehouse = user_pos_profile[0][1] if user_pos_profile else None

        if not warehouse:
            global_pos_profile = frappe.db.sql("""select name, warehouse from `tabPOS Profile`
				where (user is null or user = '') and company = %s""", self.company)

            if global_pos_profile:
                warehouse = global_pos_profile[0][1]
            elif not user_pos_profile:
                msgprint(_("POS Profile required to make POS Entry"), raise_exception=True)

        return warehouse

    def set_income_account_for_fixed_assets(self):
        disposal_account = depreciation_cost_center = None
        for d in self.get("items"):
            if d.is_fixed_asset:
                if not disposal_account:
                    disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(self.company)

                d.income_account = disposal_account
                if not d.cost_center:
                    d.cost_center = depreciation_cost_center

    def check_prev_docstatus(self):
        for d in self.get('items'):
            if d.sales_order and frappe.db.get_value("Sales Order", d.sales_order, "docstatus") != 1:
                frappe.throw(_("Sales Order {0} is not submitted").format(d.sales_order))

            if d.delivery_note and frappe.db.get_value("Delivery Note", d.delivery_note, "docstatus") != 1:
                throw(_("Delivery Note {0} is not submitted").format(d.delivery_note))

    def make_gl_entries(self, gl_entries=None, repost_future_gle=True, from_repost=False):
        auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)

        if not self.grand_total:
            return

        if not gl_entries:
            gl_entries = self.get_gl_entries()

        if gl_entries:
            from erpnext.accounts.general_ledger import make_gl_entries

            # if POS and amount is written off, updating outstanding amt after posting all gl entries
            update_outstanding = "No" if (cint(self.is_pos) or self.write_off_account) else "Yes"

            make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
                            update_outstanding=update_outstanding, merge_entries=False)

            if update_outstanding == "No":
                from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt
                update_outstanding_amt(self.debit_to, "Customer", self.customer,
                                       self.doctype, self.return_against if cint(self.is_return) else self.name)

            if repost_future_gle and cint(self.update_stock) \
                    and cint(auto_accounting_for_stock):
                items, warehouses = self.get_items_and_warehouses()
                update_gl_entries_after(self.posting_date, self.posting_time, warehouses, items)
        elif self.docstatus == 2 and cint(self.update_stock) \
                and cint(auto_accounting_for_stock):
            from erpnext.accounts.general_ledger import delete_gl_entries
            delete_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

    def get_gl_entries(self, warehouse_account=None):
        from erpnext.accounts.general_ledger import merge_similar_entries

        gl_entries = []

        self.make_customer_gl_entry(gl_entries)

        self.make_tax_gl_entries(gl_entries)

        self.make_item_gl_entries(gl_entries)

        # merge gl entries before adding pos entries
        gl_entries = merge_similar_entries(gl_entries)

        self.make_pos_gl_entries(gl_entries)
        self.make_gle_for_change_amount(gl_entries)

        self.make_write_off_gl_entry(gl_entries)
        self.make_gle_for_rounding_adjustment(gl_entries)

        return gl_entries

    def make_customer_gl_entry(self, gl_entries):
        grand_total = self.rounded_total or self.grand_total
        if self.get("payment_schedule"):
            for d in self.get("payment_schedule"):
                payment_amount_in_company_currency = flt(d.payment_amount * self.conversion_rate,
                                                         d.precision("payment_amount"))

                gl_entries.append(
                    self.get_gl_dict({
                        "account": self.debit_to,
                        "party_type": "Customer",
                        "party": self.customer,
                        "due_date": d.due_date,
                        "against": self.against_income_account,
                        "debit": payment_amount_in_company_currency,
                        "debit_in_account_currency": payment_amount_in_company_currency \
                            if self.party_account_currency == self.company_currency else d.payment_amount,
                        "against_voucher": self.return_against if cint(self.is_return) else self.name,
                        "against_voucher_type": self.doctype
                    }, self.party_account_currency)
                )

        elif grand_total:
            # Didnot use base_grand_total to book rounding loss gle
            grand_total_in_company_currency = flt(grand_total * self.conversion_rate,
                                                  self.precision("grand_total"))

            gl_entries.append(
                self.get_gl_dict({
                    "account": self.debit_to,
                    "party_type": "Customer",
                    "party": self.customer,
                    "against": self.against_income_account,
                    "debit": grand_total_in_company_currency,
                    "debit_in_account_currency": grand_total_in_company_currency \
                        if self.party_account_currency == self.company_currency else grand_total,
                    "against_voucher": self.return_against if cint(self.is_return) else self.name,
                    "against_voucher_type": self.doctype
                }, self.party_account_currency)
            )

    def make_tax_gl_entries(self, gl_entries):
        for tax in self.get("taxes"):
            if flt(tax.base_tax_amount_after_discount_amount):
                account_currency = get_account_currency(tax.account_head)
                gl_entries.append(
                    self.get_gl_dict({
                        "account": tax.account_head,
                        "against": self.customer,
                        "credit": flt(tax.base_tax_amount_after_discount_amount),
                        "credit_in_account_currency": flt(tax.base_tax_amount_after_discount_amount) \
                            if account_currency == self.company_currency else flt(tax.tax_amount_after_discount_amount),
                        "cost_center": tax.cost_center
                    }, account_currency)
                )

    def make_item_gl_entries(self, gl_entries):
        # income account gl entries
        for item in self.get("items"):
            if flt(item.base_net_amount):
                account_currency = get_account_currency(item.income_account)
                gl_entries.append(
                    self.get_gl_dict({
                        "account": item.income_account,
                        "against": self.customer,
                        "credit": item.base_net_amount,
                        "credit_in_account_currency": item.base_net_amount \
                            if account_currency == self.company_currency else item.net_amount,
                        "cost_center": item.cost_center
                    }, account_currency)
                )

                if item.is_fixed_asset:
                    asset = frappe.get_doc("Asset", item.asset)

                    fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(asset, is_sale=True)
                    for gle in fixed_asset_gl_entries:
                        gle["against"] = self.customer
                        gl_entries.append(self.get_gl_dict(gle))

                    asset.db_set("disposal_date", self.posting_date)
                    asset.set_status("Sold" if self.docstatus == 1 else None)

        # expense account gl entries
        if cint(self.update_stock) and \
                erpnext.is_perpetual_inventory_enabled(self.company):
            gl_entries += super(SalesInvoice, self).get_gl_entries()

    def make_pos_gl_entries(self, gl_entries):
        if cint(self.is_pos):
            for payment_mode in self.payments:
                if payment_mode.amount:
                    # POS, make payment entries
                    gl_entries.append(
                        self.get_gl_dict({
                            "account": self.debit_to,
                            "party_type": "Customer",
                            "party": self.customer,
                            "due_date": self.due_date,
                            "against": payment_mode.account,
                            "credit": payment_mode.base_amount,
                            "credit_in_account_currency": payment_mode.base_amount \
                                if self.party_account_currency == self.company_currency \
                                else payment_mode.amount,
                            "against_voucher": self.return_against if cint(self.is_return) else self.name,
                            "against_voucher_type": self.doctype,
                        }, self.party_account_currency)
                    )

                    payment_mode_account_currency = get_account_currency(payment_mode.account)
                    gl_entries.append(
                        self.get_gl_dict({
                            "account": payment_mode.account,
                            "against": self.customer,
                            "debit": payment_mode.base_amount,
                            "debit_in_account_currency": payment_mode.base_amount \
                                if payment_mode_account_currency == self.company_currency \
                                else payment_mode.amount
                        }, payment_mode_account_currency)
                    )

    def make_gle_for_change_amount(self, gl_entries):
        if cint(self.is_pos) and self.change_amount:
            if self.account_for_change_amount:
                gl_entries.append(
                    self.get_gl_dict({
                        "account": self.debit_to,
                        "party_type": "Customer",
                        "party": self.customer,
                        "against": self.account_for_change_amount,
                        "debit": flt(self.base_change_amount),
                        "debit_in_account_currency": flt(self.base_change_amount) \
                            if self.party_account_currency == self.company_currency else flt(self.change_amount),
                        "against_voucher": self.return_against if cint(self.is_return) else self.name,
                        "against_voucher_type": self.doctype
                    }, self.party_account_currency)
                )

                gl_entries.append(
                    self.get_gl_dict({
                        "account": self.account_for_change_amount,
                        "against": self.customer,
                        "credit": self.base_change_amount
                    })
                )
            else:
                frappe.throw(_("Select change amount account"), title="Mandatory Field")

    def make_write_off_gl_entry(self, gl_entries):
        # write off entries, applicable if only pos
        if self.write_off_account and self.write_off_amount:
            write_off_account_currency = get_account_currency(self.write_off_account)
            default_cost_center = frappe.db.get_value('Company', self.company, 'cost_center')

            gl_entries.append(
                self.get_gl_dict({
                    "account": self.debit_to,
                    "party_type": "Customer",
                    "party": self.customer,
                    "against": self.write_off_account,
                    "credit": self.base_write_off_amount,
                    "credit_in_account_currency": self.base_write_off_amount \
                        if self.party_account_currency == self.company_currency else self.write_off_amount,
                    "against_voucher": self.return_against if cint(self.is_return) else self.name,
                    "against_voucher_type": self.doctype
                }, self.party_account_currency)
            )
            gl_entries.append(
                self.get_gl_dict({
                    "account": self.write_off_account,
                    "against": self.customer,
                    "debit": self.base_write_off_amount,
                    "debit_in_account_currency": self.base_write_off_amount \
                        if write_off_account_currency == self.company_currency else self.write_off_amount,
                    "cost_center": self.write_off_cost_center or default_cost_center
                }, write_off_account_currency)
            )

    def make_gle_for_rounding_adjustment(self, gl_entries):
        if self.rounding_adjustment:
            round_off_account, round_off_cost_center = \
                get_round_off_account_and_cost_center(self.company)

            gl_entries.append(
                self.get_gl_dict({
                    "account": round_off_account,
                    "against": self.customer,
                    "credit_in_account_currency": self.rounding_adjustment,
                    "credit": self.base_rounding_adjustment,
                    "cost_center": round_off_cost_center,
                }
                ))

    def update_billing_status_in_dn(self, update_modified=True):
        updated_delivery_notes = []
        for d in self.get("items"):
            if d.dn_detail:
                billed_amt = frappe.db.sql("""select sum(amount) from `tabSales Invoice Item`
					where dn_detail=%s and docstatus=1""", d.dn_detail)
                billed_amt = billed_amt and billed_amt[0][0] or 0
                frappe.db.set_value("Delivery Note Item", d.dn_detail, "billed_amt", billed_amt,
                                    update_modified=update_modified)
                updated_delivery_notes.append(d.delivery_note)
            elif d.so_detail:
                updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

        for dn in set(updated_delivery_notes):
            frappe.get_doc("Delivery Note", dn).update_billing_percentage(update_modified=update_modified)

    def on_recurring(self, reference_doc, subscription_doc):
        for fieldname in ("c_form_applicable", "c_form_no", "write_off_amount"):
            self.set(fieldname, reference_doc.get(fieldname))

        self.due_date = None

    def update_serial_no(self, in_cancel=False):
        """ update Sales Invoice refrence in Serial No """
        invoice = None if (in_cancel or self.is_return) else self.name
        if in_cancel and self.is_return:
            invoice = self.return_against

        for item in self.items:
            if not item.serial_no:
                continue

            for serial_no in item.serial_no.split("\n"):
                if serial_no and frappe.db.exists('Serial No', serial_no):
                    sno = frappe.get_doc('Serial No', serial_no)
                    sno.sales_invoice = invoice
                    sno.db_update()

    def validate_serial_numbers(self):
        """
            validate serial number agains Delivery Note and Sales Invoice
        """
        self.set_serial_no_against_delivery_note()
        self.validate_serial_against_delivery_note()
        self.validate_serial_against_sales_invoice()

    def set_serial_no_against_delivery_note(self):
        for item in self.items:
            if item.serial_no and item.delivery_note and \
                    item.qty != len(get_serial_nos(item.serial_no)):
                item.serial_no = get_delivery_note_serial_no(item.item_code, item.qty, item.delivery_note)

    def validate_serial_against_delivery_note(self):
        """
            validate if the serial numbers in Sales Invoice Items are same as in
            Delivery Note Item
        """

        for item in self.items:
            if not item.delivery_note or not item.dn_detail:
                continue

            serial_nos = frappe.db.get_value("Delivery Note Item", item.dn_detail, "serial_no") or ""
            dn_serial_nos = set(get_serial_nos(serial_nos))

            serial_nos = item.serial_no or ""
            si_serial_nos = set(get_serial_nos(serial_nos))

            if si_serial_nos - dn_serial_nos:
                frappe.throw(_("Serial Numbers in row {0} does not match with Delivery Note".format(item.idx)))

            if item.serial_no and cint(item.qty) != len(si_serial_nos):
                frappe.throw(_("Row {0}: {1} Serial numbers required for Item {2}. You have provided {3}.".format(
                    item.idx, item.qty, item.item_code, len(si_serial_nos))))

    def validate_serial_against_sales_invoice(self):
        """ check if serial number is already used in other sales invoice """
        for item in self.items:
            if not item.serial_no:
                continue

            for serial_no in item.serial_no.split("\n"):
                sales_invoice = frappe.db.get_value("Serial No", serial_no, "sales_invoice")
                if sales_invoice and self.name != sales_invoice:
                    frappe.throw(_("Serial Number: {0} is already referenced in Sales Invoice: {1}".format(
                        serial_no, sales_invoice
                    )))

    def contact_person_display_ship(self):
        sql = """ SELECT * FROM tabContact WHERE `name` like '%-{0}%' """.format(
            self.ship_to)
        add = frappe.db.sql(sql, as_dict=1)
        contact_person_name = ''
        if len(add) > 0:
            for add_value in add:
                if add_value.last_name:
                    contact_person_name = add_value.first_name + " " + add_value.last_name
                else:
                    contact_person_name = add_value.first_name
                # contact_person_name = add_value.first_name + " " + add_value.last_name
                frappe.db.set(self, 'contact_person_ship_to', contact_person_name)
                frappe.db.commit()

    def validate_valuation_rate(self):

        for i in self.items:
            item = frappe.get_doc('Item', i.item_code)
            if item.get('is_stock_item') == 0:
                continue

            last_valuation_rate = frappe.db.sql("""select valuation_rate
                    from `tabStock Ledger Entry`
                    where item_code = %s and warehouse = %s
                    and valuation_rate > 0
                    order by posting_date desc, posting_time desc, name desc limit 1""", (i.item_code, i.warehouse))

            if not last_valuation_rate:
                # Get valuation rate from last sle for the item against any warehouse
                last_valuation_rate = frappe.db.sql("""select valuation_rate
                        from `tabStock Ledger Entry`
                        where item_code = %s and valuation_rate > 0
                        order by posting_date desc, posting_time desc, name desc limit 1""", i.item_code)

            valuation_rate = flt(last_valuation_rate[0][0]) if last_valuation_rate else 0

            if not valuation_rate:
                # If negative stock allowed, and item delivered without any incoming entry,
                # syste does not found any SLE, then take valuation rate from Item
                valuation_rate = frappe.db.get_value("Item", i.item_code, "valuation_rate")

                if not valuation_rate:
                    # try Item Standard rate
                    valuation_rate = frappe.db.get_value("Item", i.item_code, "standard_rate")

                    if not valuation_rate:
                        # try in price list
                        valuation_rate = frappe.db.get_value('Item Price',
                                                             dict(item_code=i.item_code, buying=1,
                                                                  currency=self.currency),
                                                             'price_list_rate')

            if not valuation_rate and cint(erpnext.is_perpetual_inventory_enabled(self.company)):
                frappe.local.message_log = []
                frappe.throw(_(
                    "Valuation rate not found for the Item {0}, which is required to do accounting entries for {1} {2}. "
                    "If the item is transacting as a zero valuation rate item in the {1}, please mention that in the {1} Item table. "
                    "Otherwise, please create an incoming stock transaction for the item or mention valuation rate in the Item record, "
                    "and then try submiting/cancelling this entry").format(i.item_code, self.doctype, self.name))


def get_list_context(context=None):
    from erpnext.controllers.website_list_for_contact import get_list_context
    list_context = get_list_context(context)
    list_context.update({
        'show_sidebar': True,
        'show_search': True,
        'no_breadcrumbs': True,
        'title': _('Invoices'),
    })
    return list_context

# @frappe.whitelist()
# def check_actual_qty(doc):
#     import json
#     self = json.loads(doc)
#
#     for i in self.get('items'):
#         is_update_stock_check = """SELECT is_stock_item FROM `tabItem` WHERE item_code='{0}' LIMIT 1""".format(
#             i.get('item_code'))
#         stock_list = frappe.db.sql(is_update_stock_check, as_dict=1)
#
#         for j in stock_list:
#             if j.is_stock_item == 1:
#                 sql = """select actual_qty from `tabBin` where item_code ='{0}' and warehouse ='{1}' LIMIT 1""".format(
#                     i.get('item_code'), i.get('warehouse'))
#                 item_list = frappe.db.sql(sql, as_dict=1)
#
#                 if len(item_list) > 0:
#                     for a in item_list:
#                         if i.get('qty') > a['actual_qty']:
#                             frappe.throw(_("1.0 units of {0} needed in {1} to complete this transaction.").format(
#                                 i.get('item_code'), i.get('warehouse')))
#                 else:
#                     frappe.throw(_("Stock is not available in this warehouse"))

@frappe.whitelist()
def calculate_taxrate_taxamount_pos(taxes_and_charges):
    add = frappe.db.sql("SELECT included_in_print_rate FROM `tabSales Taxes and Charges` WHERE parent=%s",
                        taxes_and_charges, as_dict=1)
    t = 0
    for d in add:
        if d.included_in_print_rate == 1:
            t = 1
            return t
        else:
            return t


@frappe.whitelist()
def get_bank_cash_account(mode_of_payment, company):
    account = frappe.db.get_value("Mode of Payment Account",
                                  {"parent": mode_of_payment, "company": company}, "default_account")
    if not account:
        frappe.throw(_("Please set default Cash or Bank account in Mode of Payment {0}")
                     .format(mode_of_payment))
    return {
        "account": account
    }


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
    def set_missing_values(source, target):
        target.ignore_pricing_rule = 1
        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(source_doc, target_doc, source_parent):
        target_doc.qty = flt(source_doc.qty) - flt(source_doc.delivered_qty)
        target_doc.stock_qty = target_doc.qty * flt(source_doc.conversion_factor)

        target_doc.base_amount = target_doc.qty * flt(source_doc.base_rate)
        target_doc.amount = target_doc.qty * flt(source_doc.rate)

    doclist = get_mapped_doc("Sales Invoice", source_name, {
        "Sales Invoice": {
            "doctype": "Delivery Note",
            "validation": {
                "docstatus": ["=", 1]
            }
        },
        "Sales Invoice Item": {
            "doctype": "Delivery Note Item",
            "field_map": {
                "name": "si_detail",
                "parent": "against_sales_invoice",
                "serial_no": "serial_no",
                "sales_order": "against_sales_order",
                "so_detail": "so_detail",
                "cost_center": "cost_center"
            },
            "postprocess": update_item,
            "condition": lambda doc: doc.delivered_by_supplier != 1
        },
        "Sales Taxes and Charges": {
            "doctype": "Sales Taxes and Charges",
            "add_if_empty": True
        },
        "Sales Team": {
            "doctype": "Sales Team",
            "field_map": {
                "incentives": "incentives"
            },
            "add_if_empty": True
        }
    }, target_doc, set_missing_values)

    return doclist


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
    from erpnext.controllers.sales_and_purchase_return import make_return_doc
    return make_return_doc("Sales Invoice", source_name, target_doc)


def set_account_for_mode_of_payment(self):
    for data in self.payments:
        if not data.account:
            data.account = get_bank_cash_account(data.mode_of_payment, self.company).get("account")


def get_company_pos_address():
    pos_add = ""

    sql = """SELECT address_line1,address_line2,city,country,email_id,phone FROM tabAddress WHERE address_type='Shop' AND docstatus=0 AND is_your_company_address = 1 LIMIT 1"""
    add = frappe.db.sql(sql, as_dict=1)
    if (len(add) > 0):
        add = add[0]
        pos_add = """{0} {1}<br/>{2}, {3}<br/>Phone: {4}<br/>Email: {5}""".format(add.address_line1, add.address_line2,
                                                                                  add.city, add.country, add.phone,
                                                                                  add.email_id)

    return pos_add


def get_customer_ship_address(ship_to):
    pos_add = ""

    sql = """SELECT a.address_line1,a.address_line2,a.city,a.pincode,a.country,a.email_id,a.fax,a.phone
FROM tabAddress a
INNER JOIN `tabDynamic Link` dl ON (a.name = dl.parent)
WHERE dl.link_doctype = 'Customer'
AND a.address_type='Billing'
AND a.is_primary_address = 1
AND dl.link_name = '{0}'""".format(ship_to)
    add = frappe.db.sql(sql, as_dict=1)
    if (len(add) > 0):
        add = add[0]

        if add.address_line1 != None:
            pos_add = pos_add + add.address_line1
        if add.address_line2 != None:
            pos_add = pos_add + " " + add.address_line2
        if add.city != None:
            pos_add = pos_add + "<br/>" + add.city
        if add.pincode != None:
            pos_add = pos_add + " " + add.pincode
        if add.country != None:
            pos_add = pos_add + "<br/>" + add.country
        if add.phone != None:
            pos_add = pos_add + "<br/><b>Phone:</b>" + add.phone
        if add.fax != None:
            pos_add = pos_add + "<br/><b>Fax:</b>" + add.fax
        if add.email_id != None:
            pos_add = pos_add + "<br/><b>Email:</b>" + add.email_id

        # pos_add = """{0} {1}<br/>{2} {3}<br/>{4}<br/><b>Phone:</b> {5}<br/><b>Fax:</b>{6}<br/><b>Email:</b> {7}""".format(add.address_line1, add.address_line2,
        #                                                                           add.city,add.pincode,add.country, add.phone,add.fax,
        #                                                                           add.email_id)

    return pos_add
