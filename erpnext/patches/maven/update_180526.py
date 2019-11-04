from __future__ import unicode_literals

import json

import frappe


# bench --site erpnext.vm execute erpnext.patches.maven.update_180227b.execute

def calculate_taxrate_taxamount(doc):
    # print "calculate_taxrate_taxamount"
    add = frappe.db.sql("SELECT included_in_print_rate FROM `tabSales Taxes and Charges` WHERE parent=%s",
                        doc.taxes_and_charges, as_dict=1)

    for d in add:
        if d.included_in_print_rate == 1:
            doc.taxrate_taxamount_inculsive()
        else:
            doc.taxrate_taxamount_exculsive()

    update_sales_tax_and_charges(doc)

def taxrate_taxamount_exculsive(doc):
    try:
        for allitems in doc.items:
            for taxRow in doc.taxes:

                tax_rate = taxRow.rate
                tax_amount = (allitems.amount * (tax_rate / 100))
                item_with_tax_amount = allitems.amount + tax_amount
                if doc.docstatus == 0:
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


def taxrate_taxamount_inculsive(doc):
    try:
        for allitems in doc.items:
            for taxRow in doc.taxes:

                tax_rate = taxRow.rate
                tax_val = ((tax_rate / 100) + 1)
                z = (allitems.amount / tax_val)
                tax_amount = allitems.amount - z
                item_with_tax_amount = allitems.amount + tax_amount
                if doc.docstatus == 0:
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


def update_sales_tax_and_charges(doc):
    data_dict = {}

    # for i in doc.items:
    #     tax_list = [i.tax_rate, i.tax_amount]
    #     data_dict[i.item_code] = tax_list
    # data_dict = json.dumps(data_dict)

    for i in doc.items:
        old_tax_amount = 0
        old_tax_list = data_dict.get(i.item_code, None)

        if old_tax_list != None:
            old_tax_amount = old_tax_list[1]

        tax_list = [i.tax_rate, i.tax_amount + old_tax_amount]
        data_dict[i.item_code] = tax_list

    data_dict = json.dumps(data_dict)

    sql = """ UPDATE `tabSales Taxes and Charges` SET item_wise_tax_detail = '{0}' WHERE parent = '{1}'  """.format(
        data_dict, doc.name)
    frappe.db.sql(sql)
    frappe.db.commit()

    update_tax_breakup(doc)
    update_tax_on_items(doc)


def update_tax_breakup(doc):
    doc = frappe.get_doc("Sales Invoice", doc.name)
    from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_html
    new_html = get_itemised_tax_breakup_html(doc)
    # frappe.db.set_value("Sales Invoice", doc.name, "other_charges_calculation", new_html, update_modified=False)
    doc.other_charges_calculation = new_html
    doc.db_update()
    frappe.db.commit()


def update_tax_on_items(doc):
    filters = [{"parent": doc.taxes_and_charges}]
    fields = ["name", "account_head", "rate"]
    doc_list = frappe.get_all("Sales Taxes and Charges", filters=filters, fields=fields)
    for d in doc_list:
        for i in doc.items:
            data_dict = {}
            data_dict[d.get("account_head")] = d.get("rate")
            data_dict = json.dumps(data_dict)
            i.item_tax_rate = data_dict
            frappe.db.set_value("Sales Invoice Item", i.name, "item_tax_rate", data_dict, update_modified=False)


def pur_update_sale_invoice():
    try:
        ##getting all has rol of role vps user
        #filters=[["name", "=", "SINV-00001"]], fields=['*']
        getSales = frappe.get_all('Sales Invoice', filters=[["name", "=", 'SINV-00004']])

        # getSales = frappe.get_all('Sales Invoice')
        for d in getSales:
            doc = frappe.get_doc("Sales Invoice", d["name"])
            # print d["name"]
            calculate_taxrate_taxamount(doc)

    except Exception, ex:
        print ex.message


def execute():
    pur_update_sale_invoice()
    frappe.db.commit()

if __name__ == '__main__':
    try:
        # cronjob path
        # 30 1 * * * cd /home/demouser/ct-bench &&  /home/demouser/ct-bench/apps/erpnext/erpnext/utilities/cronjob_attendance_log.py >> /home/demouser/ct-bench/logs/cronjob_attendance_log.log 2>&1
        frappe.init("erpnext.vm",
                    "/Users/user/Desktop/SkypFrappeRGS/frappe-bench/sites")
        frappe.connect()

        execute()

    except Exception as e:
        print e
    finally:
        frappe.destroy()

