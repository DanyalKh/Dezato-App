from __future__ import unicode_literals

import json

import frappe


# bench --site erpnext.vm execute erpnext.patches.maven.update_180227.execute

# for sales correction

def update_sales_line_item_with_old_tax():
    # doc_list = frappe.get_all("Sales Invoice")
    sql0 = """ SELECT name FROM `tabSales Invoice` WHERE creation < '2018-03-29' """
    doc_list = frappe.db.sql(sql0, as_dict=1)
    for d in doc_list:
        doc = frappe.get_doc("Sales Invoice", d.get("name"))
        old_docstatus = doc.status
        item_wise_tax_detail = frappe.get_value("Sales Taxes and Charges", {"parent": doc.name},
                                                "item_wise_tax_detail")
        if item_wise_tax_detail == None:
            continue

        item_wise_tax_detail = json.loads(item_wise_tax_detail)

        for item_code, tax_data in item_wise_tax_detail.items():
            if isinstance(tax_data, list):
                tax_rate, tax_amount = tax_data
            else:
                tax_rate = tax_data
                tax_amount = 0

            sql = """UPDATE `tabSales Invoice Item` SET tax_rate = {0}, tax_amount={1},  item_with_tax_amount = amount + {2} WHERE parent = '{3}' AND item_code = '{4}' """.format(
                tax_rate, tax_amount, tax_amount, doc.name, item_code)
            frappe.db.sql(sql)
            frappe.db.commit()

            # print doc.name, item_code, tax_rate, tax_amount

        # return

def update_sales_line_item_zero():
    sql = """UPDATE `tabSales Invoice Item` SET tax_rate = {0}, tax_amount={1},  item_with_tax_amount = amount + {2} WHERE creation < '2018-03-29' """.format(
        0, 0, 0)
    frappe.db.sql(sql)
    frappe.db.commit()

def update_purchase_line_item_with_old_tax():
    sql0 = """ SELECT name FROM `tabPurchase Invoice` WHERE creation < '2018-03-29' """
    doc_list = frappe.db.sql(sql0, as_dict=1)
    for d in doc_list:
        doc = frappe.get_doc("Purchase Invoice", d.get("name"))
        old_docstatus = doc.status
        item_wise_tax_detail = frappe.get_value("Purchase Taxes and Charges", {"parent": doc.name},
                                                "item_wise_tax_detail")
        if item_wise_tax_detail == None:
            continue

        item_wise_tax_detail = json.loads(item_wise_tax_detail)

        for item_code, tax_data in item_wise_tax_detail.items():
            if isinstance(tax_data, list):
                tax_rate, tax_amount = tax_data
            else:
                tax_rate = tax_data
                tax_amount = 0

            sql = """UPDATE `tabPurchase Invoice Item` SET tax_rate = {0}, tax_amount={1},  item_with_tax_amount = amount + {2} WHERE parent = '{3}' AND item_code = '{4}' """.format(
                tax_rate, tax_amount, tax_amount, doc.name, item_code)
            frappe.db.sql(sql)
            frappe.db.commit()

            # print doc.name, item_code, tax_rate, tax_amount

        # return

def update_purchase_line_item_zero():
    sql = """UPDATE `tabPurchase Invoice Item` SET tax_rate = {0}, tax_amount={1},  item_with_tax_amount = amount + {2} WHERE creation < '2018-03-29' """.format(
        0, 0, 0)
    frappe.db.sql(sql)
    frappe.db.commit()



def execute():
    update_sales_line_item_zero()
    update_sales_line_item_with_old_tax()
    update_purchase_line_item_with_old_tax()
    update_purchase_line_item_zero()


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
