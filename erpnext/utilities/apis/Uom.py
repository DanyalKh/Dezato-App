import json

import datetime
import frappe

# ret_list = {}
@frappe.whitelist(allow_guest=False)
def itemSync(data):
    ret_list = {}
    data = json.loads(data)
    frappe.clear_cache(doctype="UOM")
    logDataInsert(data["data"], data["user_name"], data["ip_address"], data["handset_model"], data["os_version"])
    res = updateItem(data["data"])
    ret_list = sendItem(data["lastSyncDate"])
    if res == -1:
        ret_list["status"] = -1

    return ret_list


def updateItem(data):
    # global ret_list
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d")
    from frappe.utils import now
    currDate = now()

    for d in data:
        try:
            filters = [["name", "=", d.get("name")]]
            doc_list = frappe.get_all("UOM", filters=filters)

            # update
            if doc_list != None and len(doc_list) > 0:
                for d2 in doc_list:
                    doc = frappe.get_doc("UOM", d2.get("name"))

                    doc.name = d.get("name", None)
                    doc.uom_name = d.get("uom_name",None)
                    doc.must_be_whole_number = d.get("must_be_whole_number", 0)
                    doc.docstatus = int(d.get("docstatus", "0"))
                    # doc.creation = d.get("creation", currDate)
                    # doc.modified = d.get("modified", currDate)
                    if (d.get("is_delete", 0) == "1"):
                        doc.delete()
                    else:

                     doc.save()
                     frappe.db.set_value("UOM", doc.get("name"), "modified", d.get("modified"), update_modified=False)

            else:

                # insert
                doc = frappe.new_doc("UOM")

                doc.name = d.get("name", None)
                doc.uom_name = d.get("uom_name")
                doc.must_be_whole_number = d.get("must_be_whole_number", 0)
                # doc.creation = d.get("creation", currDate)
                # doc.modified = d.get("modified", currDate)

                doc.save()

                frappe.db.set_value("UOM", d.get("name"), "creation", doc.get("modified"), update_modified=False)
                frappe.db.set_value("UOM", d.get("name"), "modified", doc.get("modified"), update_modified=False)

        except Exception, ex:
            return -1
            print ex


def sendItem(lastSyncDate):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d")
    # currDate = now.strftime("%Y-%m-%d %H:%M:%S")
    from frappe.utils import now
    currDate = now()

    fields = ["name",
              "uom_name",
              "must_be_whole_number",
              "docstatus",
              "creation",
              "modified"
              ]

    filters = [
        ["modified", ">", lastSyncDate], ["modified", "<", currDate]
    ]

    # doc_list = frappe.get_all("UOM", fields=fields, filters=filters)
    doc_list = frappe.get_all("UOM", fields=fields)

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
            doc.api_type = "Uom"
            doc.creation = currDate
            doc.modified = currDate

            doc.save()

    except Exception, ex:
        print ex