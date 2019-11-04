import frappe
from frappe.utils import cstr


def for_gle_2(doc, method):
    if doc.docstatus == 0:
        doc.make_gl_entries()
        tmp = frappe.db.sql("""select modified, docstatus from `tab{0}`
        					where name = %s for update""".format(doc.doctype), doc.name, as_dict=True)

        if not tmp:
            frappe.throw(_("Record does not exist"))
        else:
            tmp = tmp[0]

        modified = cstr(tmp.modified)

        doc.modified = modified
