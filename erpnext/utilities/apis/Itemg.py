import json

import datetime
import frappe


@frappe.whitelist(allow_guest=False)
def itemSync(data):
    ret_list = {}
    data = json.loads(data)
    frappe.clear_cache(doctype="Item Group")
    logDataInsert(data["data"], data["user_name"], data["ip_address"], data["handset_model"], data["os_version"])
    res = updateItem(data["data"])
    ret_list = sendItem(data["lastSyncDate"])

    if res == -1:
        ret_list["status"] = -1

    return ret_list


def updateItem(data):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d")
    from frappe.utils import now
    currDate = now()

    for d in data:
        try:
            filters = [["name", "=", d.get("name")]]
            doc_list = frappe.get_all("Item Group", filters=filters)

            # update

            if doc_list != None and len(doc_list) > 0:
                for d2 in doc_list:
                    doc = frappe.get_doc("Item Group", d2.get("name"))

                    doc.name = d.get("name", None)
                    doc.parent = d.get("parent", None)
                    doc.parent_item_group = d.get("parent_item_group", None)
                    doc.docstatus = int(d.get("docstatus", "0"))
                    doc.is_group = d.get("is_group", 0)
                    doc.item_group_name = d.get("item_group_name", 0)
                    # doc.creation = d.get("creation", currDate)
                    # doc.modified = d.get("modified", currDate)
                    if (d.get("is_delete", 0) == "1"):
                        doc.delete()
                    else:
                        doc.save(ignore_permissions=True)

                        frappe.db.set_value("Item Group", doc.get("name"), "modified", d.get("modified"), update_modified=False)

            else:

                # insert
                doc = frappe.new_doc("Item Group")

                doc.name = d.get("name", None)
                doc.parent = d.get("parent", None)
                doc.parent_item_group = d.get("parent_item_group", None)
                doc.docstatus = int(d.get("docstatus", "0"))
                doc.is_group = d.get("is_group", 0)
                doc.item_group_name = d.get("item_group_name", 0)
                # doc.creation = d.get("creation", currDate)
                # doc.modified = d.get("modified", currDate)

                doc.save(ignore_permissions=True)

                frappe.db.set_value("Item Group", doc.get("name"), "creation", d.get("modified"), update_modified=False)
                frappe.db.set_value("Item Group", doc.get("name"), "modified", d.get("modified"), update_modified=False)

        except Exception, ex:
            return -1
            print ex


def sendItem(lastSyncDate):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d %H:%M:%S")
    from frappe.utils import now
    currDate = now()

    fields = ["name",
              "parent",
              "parent_item_group",
              "item_group_name",
              "docstatus",
              "is_group",
              "creation",
              "modified"
              ]

    filters = [
        ["modified", ">", lastSyncDate], ["modified", "<", currDate]
    ]

    # doc_list = frappe.get_all("Item Group", fields=fields, filters=filters)
    doc_list = frappe.get_all("Item Group", fields=fields)

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
            doc.api_type = "Itemg"
            doc.creation = currDate
            doc.modified = currDate

            doc.save()

    except Exception, ex:
        print ex