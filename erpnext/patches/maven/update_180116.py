from __future__ import unicode_literals
import frappe


# bench --site erpnext.vm migrate
# bench --site erpnext.vm execute erpnext.patches.maven.update_180116.execute


def create_role_for_readonly():
    try:
        ##create read only role
        role = frappe.new_doc("Role")
        role.role_name = "Client Account Manager"
        role.desk_access = 1
        role.insert()

    except Exception, ex:
        print ex


def doctype_perm_for_readonly():
    try:
        sql = """SELECT DISTINCT parent
    FROM tabDocPerm
    WHERE role in (
    SELECT role
    FROM `tabHas Role`
    WHERE parent in ('mujahid@skylines.ae', 'fas@skylines.ae')
    AND parenttype = 'User'
    AND parentfield = 'roles'
    ORDER BY role
    )
    ORDER BY 1"""

        doctype_list = frappe.db.sql(sql, as_dict=1)

        for d in doctype_list:
            ##add readonly permission
            customPerm = frappe.new_doc("Custom DocPerm")
            customPerm.parent = d.parent
            customPerm.parentfield = "permissions"
            customPerm.parenttype = "DocType"
            customPerm.role = "Client Account Manager"
            customPerm.read = 1
            customPerm.share = 0
            customPerm.export = 0
            customPerm.cancel = 0
            customPerm.create = 0
            customPerm.submit = 0
            customPerm.write = 0
            customPerm.imtport = 0
            customPerm.email = 0
            customPerm.share = 0
            customPerm.report = 0
            customPerm.delete = 0
            customPerm.save()

    except Exception, ex:
        print ex


def perm_on_page_and_report():
    sql = """SELECT DISTINCT parent, parentfield, parenttype
FROM `tabHas Role`
WHERE role in (
SELECT role
FROM `tabHas Role`
WHERE parent in ('mujahid@skylines.ae', 'fas@skylines.ae')
AND parenttype = 'User'
AND parentfield = 'roles'
ORDER BY role
)
AND parenttype in ('Report', 'Page')
ORDER BY parenttype, parent
"""
    data_list = frappe.db.sql(sql, as_dict=1)

    for d in data_list:
        hasRole = frappe.new_doc("Has Role")
        hasRole.parent = d.parent
        hasRole.parentfield = d.parentfield
        hasRole.parenttype = d.parenttype
        hasRole.role = "Client Account Manager"
        hasRole.save()


def create_readonly_user():
    try:
        # ##creating user
        user = frappe.new_doc("User")
        user.email = "cam@skylines.ae"
        user.first_name = "Client Account Manager"
        user.send_welcome_email = 0
        user.user_type = "System User"
        user.full_name = "Client Account Manager"
        user.new_password = "hasGh#hgsa21@vN"
        user.save()
    except Exception, ex:
        pass


def update_readonly_user():
    try:
        user = frappe.get_doc("User", "cam@skylines.ae")

        # ##aassinging role - Client Account Manager
        hasRole = frappe.new_doc("Has Role")
        hasRole.parent = user.name
        hasRole.parentfield = "roles"
        hasRole.parenttype = "User"
        hasRole.role = "Client Account Manager"
        hasRole.save()
    except Exception, ex:
        pass


def update_readonly_user_type():
    try:

        user = frappe.get_doc("User", "cam@skylines.ae")
        ## updating user_type
        user.user_type = "System User"
        user.save()
    except Exception, ex:
        pass

    try:

        ## get list of companies
        company = frappe.get_last_doc("Company")
    except Exception, ex:
        pass

    try:

        ## user permission
        userper = frappe.new_doc("User Permission")
        userper.apply_for_all_roles = 1
        userper.for_value = company.name
        userper.user = user.name
        userper.allow = "Company"
        userper.save()

    except Exception, ex:
        print ex
        pass


def create_qc_user():
    try:
        # ##creating user
        user = frappe.new_doc("User")
        user.email = "qc@skylines.ae"
        user.first_name = "Quality Control"
        user.send_welcome_email = 0
        user.user_type = "System User"
        user.full_name = "Quality Control"
        user.new_password = "btgGh#hgsa21@vN"
        user.save()
    except Exception, ex:
        pass


def update_qc_user():
    try:
        user = frappe.get_doc("User", "qc@skylines.ae")

        # ##aassinging role - Client Account Manager
        hasRole = frappe.new_doc("Has Role")
        hasRole.parent = user.name
        hasRole.parentfield = "roles"
        hasRole.parenttype = "User"
        hasRole.role = "Client Account Manager"
        hasRole.save()
    except Exception, ex:
        pass


def update_qc_user_type():
    try:

        user = frappe.get_doc("User", "qc@skylines.ae")
        ## updating user_type
        user.user_type = "System User"
        user.save()
    except Exception, ex:
        pass

    try:

        ## get list of companies
        company = frappe.get_last_doc("Company")
    except Exception, ex:
        pass

    try:

        ## user permission
        userper = frappe.new_doc("User Permission")
        userper.apply_for_all_roles = 1
        userper.for_value = company.name
        userper.user = user.name
        userper.allow = "Company"
        userper.save()

    except Exception, ex:
        print ex
        pass


def execute():
    create_role_for_readonly()
    doctype_perm_for_readonly()
    perm_on_page_and_report()
    create_readonly_user()
    update_readonly_user()
    update_readonly_user_type()
    create_qc_user()
    update_qc_user()
    update_qc_user_type()
