# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _
import frappe


def get_company_pos_address_ar():
    pos_add = ""

    sql = """SELECT address_line1,address_line2,city,country,email_id,phone FROM tabAddress WHERE address_type='Shop' AND docstatus=0 AND is_your_company_address = 1 LIMIT 1"""
    add = frappe.db.sql(sql, as_dict=1)
    if (len(add) > 0):
        add = add[0]
        pos_add = """{0} {1}<br/>{2}, {3}<br/>Phone: {4}<br/>Email: {5}""".format(add.address_line1, add.address_line2,
                                                                                  add.city, add.country, add.phone,
                                                                                  add.email_id)

    return pos_add


def company_to_address():
    sales_doc = frappe.get_all('Sales Invoice', fields=['*'])

    for all in sales_doc:
        pos_add_ar = get_company_pos_address_ar()
        if len(pos_add_ar) != 0:
            frappe.db.set_value("Sales Invoice", all.name, "company_pos_address", pos_add_ar, update_modified=False)
            frappe.db.commit()

    Quotation = frappe.get_all('Quotation', fields=['*'])

    for all in Quotation:
        pos_add_ar = get_company_pos_address_ar()
        if len(pos_add_ar) != 0:
            frappe.db.set_value("Quotation", all.name, "company_pos_address", pos_add_ar,
                                update_modified=False)
        frappe.db.commit()

    sales_order = frappe.get_all('Sales Order', fields=['*'])

    for all in sales_order:
        pos_add_ar = get_company_pos_address_ar()
        if len(pos_add_ar) != 0:
            frappe.db.set_value("Sales Order", all.name, "company_pos_address", pos_add_ar,
                                update_modified=False)
        frappe.db.commit()


def execute():
    company_to_address()


if __name__ == '__main__':
    try:
        # cronjob path
        # 30 1   * cd /home/demouser/ct-bench &&  /home/demouser/ct-bench/apps/erpnext/erpnext/utilities/cronjob_attendance_log.py >> /home/demouser/ct-bench/logs/cronjob_attendance_log.log 2>&1
        frappe.init("erpnext.vm",
                    "/Users/user/Desktop/SkypFrappeRGS/frappe-bench/sites")
        frappe.connect()

        execute()

    except Exception as e:
        print e
    finally:
        frappe.destroy()
