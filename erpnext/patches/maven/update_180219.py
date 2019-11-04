from __future__ import unicode_literals
import frappe


# bench --site erpnext.vm migrate
# bench --site erpnext.vm execute erpnext.patches.maven.update_180219.execute


def update_doctype_roles():
    try:
        ##get doctype without
        sql = """SELECT a.parent,a.role FROM tabDocPerm a LEFT JOIN `tabCustom DocPerm` b ON a.role=b.role AND a.parent=b.parent WHERE b.role IS NULL ORDER BY a.parent,a.role"""
        data = frappe.db.sql(sql, as_dict=1)
        for d in data:
            filters = [{"role": d.role}, {"parent": d.parent}]
            doc_list = frappe.get_all("DocPerm", filters=filters)

            for dp in doc_list:
                docPerm = frappe.get_doc("DocPerm", dp["name"])

                # print docPerm
                # print docPerm.share
                # print docPerm.get("print")

                doc = frappe.new_doc("Custom DocPerm")

                #other fields
                doc.set("parent", docPerm.get("parent"))
                doc.set("parentfield", docPerm.get("parentfield"))
                doc.set("parenttype", docPerm.get("parenttype"))
                doc.set("role", docPerm.get("role"))

                #permissions
                doc.set("share", docPerm.get("share"))
                doc.set("export", docPerm.get("export"))
                doc.set("cancel", docPerm.get("cancel"))
                doc.set("user_permission_doctypes", docPerm.get("user_permission_doctypes"))
                doc.set("create", docPerm.get("create"))
                doc.set("submit", docPerm.get("submit"))
                doc.set("write", docPerm.get("write"))
                doc.set("print", docPerm.get("print"))
                doc.set("import", docPerm.get("import"))
                doc.set("permlevel", docPerm.get("permlevel"))
                doc.set("apply_user_permissions", docPerm.get("apply_user_permissions"))
                doc.set("read", docPerm.get("read"))
                doc.set("set_user_permissions", docPerm.get("set_user_permissions"))
                doc.set("report", docPerm.get("report"))
                doc.set("amend", docPerm.get("amend"))
                doc.set("email", docPerm.get("email"))
                doc.set("ifowner", docPerm.get("ifowner"))
                doc.set("delete", docPerm.get("delete"))

                doc.save()


    except Exception, ex:
        print "adss"
        print ex


def execute():
    update_doctype_roles()
