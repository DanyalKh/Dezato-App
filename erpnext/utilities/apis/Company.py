import json

import datetime
import frappe


@frappe.whitelist(allow_guest=False)
def itemSync(data):
    ret_list = {}
    data = json.loads(data)
    frappe.clear_cache(doctype="Company")
    frappe.clear_cache(doctype="Address")
    logDataInsert(data["data"], data["user_name"], data["ip_address"], data["handset_model"], data["os_version"])
    updateItem(data["data"])
    res = ret_list = sendItem(data["lastSyncDate"])
    if res == -1:
        ret_list["status"] = -1


    return ret_list


def updateItem(data):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d")
    from frappe.utils import now
    currDate = now()

    try:
            filters = [["name", "=", data['name']]]
            doc_list = frappe.get_all("Company", filters=filters)


            # update
            if doc_list != None and len(doc_list) > 0:
                for d2 in doc_list:
                    doc = frappe.get_doc("Company", d2.get("name"))

                    doc.name = data['name']
                    doc.vat_number = data['vat_number']
                    # doc.pos_logo = data['pos_logo']
                    doc.docstatus = int(data['docstatus'])
                    # doc.creation = d.get("creation", currDate)
                    # doc.modified = d.get("modified", currDate)

                    doc.save()

                    # frappe.db.set_value("Company", doc.get("name"), "modified", d.get("modified"), update_modified=False)

    except Exception, ex:
        return -1
        print ex

    if data['address'] != None and len(data['address']) > 0:
                    try:
                        sql = """SELECT a.name,a.address_line1,a.address_line2,a.city,a.pincode,a.country,a.email_id,a.fax,a.phone
                               FROM tabAddress a
                               INNER JOIN `tabDynamic Link` dl ON (a.name = dl.parent)
                               WHERE dl.link_doctype = 'Company'
                               AND dl.link_name = '{0}'""".format(doc_list[0]['name'])
                        add = frappe.db.sql(sql, as_dict=1)
                        doc_list_address = add

                        # update
                        if doc_list_address != None and len(doc_list_address) > 0:
                            for d3 in doc_list_address:
                                doc_add = frappe.get_doc("Address", d3.get("name"))

                                doc_add.address_line1 = data['address']['address_line1']
                                doc_add.address_line2 = data['address']['address_line2']
                                doc_add.city = data['address']['city']
                                doc_add.country = data['address']['country']
                                doc_add.pincode = data['address']['pincode']
                                doc_add.email_id = data['address']['email_id']
                                doc_add.phone = data['address']['phone']
                                doc_add.fax = data['address']['fax']
                                doc_add.is_primary_address = data['address']['is_primary_address']
                                doc_add.is_shipping_address = data['address']['is_shipping_address']
                                doc_add.is_your_company_address = data['address']['is_your_company_address']
                                # doc_add.creation = currDate
                                # doc_add.modified = currDate

                                doc_add.save()

                                frappe.db.set_value("Address", doc.get("name"), "modified", data['modified'], update_modified=False)

                    except Exception, ex:
                        return -1
                        print ex


def sendItem(lastSyncDate):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d %H:%M:%S")
    from frappe.utils import now
    currDate = now()

    fields =["name",
             "vat_number",
             "pos_logo",
             "docstatus",
             "creation",
             "modified"
    ]

    filters = [
        ["modified", ">", lastSyncDate], ["modified", "<", currDate]
    ]

    # doc_list = frappe.get_all("Company", fields=fields, filters=filters)
    doc_list = frappe.get_all("Company", fields=fields)

    for company_list in doc_list:
       sql = """SELECT a.name,a.address_line1,a.address_line2,a.city,a.pincode,a.country,a.email_id,a.fax,a.phone,is_primary_address,is_shipping_address
       FROM tabAddress a
       INNER JOIN `tabDynamic Link` dl ON (a.name = dl.parent)
       WHERE dl.link_doctype = 'Company'
       AND dl.link_name = "{0}" """.format(company_list['name'])
       add = frappe.db.sql(sql, as_dict=1)
       company_list.address=add[0]

    status = 0

    if doc_list != None:
        if len(doc_list) > 0:
            status = 1
        else:
            status = 0


    return {
        "data": doc_list,
        "newSyncDate": currDate,
        "status": status
    }

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
            doc.api_type = "Company"
            doc.creation = currDate
            doc.modified = currDate

            doc.save()

    except Exception, ex:
        print ex