from __future__ import unicode_literals
import frappe

# bench --site erpnext.vm execute erpnext.patches.maven.update_181001.execute

def update_docs():
    list = ['Sales Invoice', 'Purchase Invoice', 'Journal Entry', 'Expense Claim', 'Payment Entry',
            'Period Closing Voucher']
    for li in list:
        doc_list = frappe.get_list(li, filters={'docstatus': 0})
        for d in doc_list:
            try:
                doc_obj = frappe.get_doc(li, d.name)
                doc_obj.save()
            except Exception, ex:
                print (li, d.name, ex.message)

    frappe.db.commit()


def execute():
    update_docs()
    print "Done"


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
