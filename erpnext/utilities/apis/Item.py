import json

import datetime
import frappe

# ret_list = {}
@frappe.whitelist(allow_guest=False)
def itemSync(data):
    ret_list = {}
    data = json.loads(data)
    frappe.clear_cache(doctype="Item")
    logDataInsert(data["data"], data["user_name"], data["ip_address"], data["handset_model"], data["os_version"])
    res = updateItem(data["data"])
    ret_list = sendItem(data["lastSyncDate"])
    if res == -1:
        ret_list["status"] = -1

    return ret_list


def updateItem(data):
    # return -1
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d")
    # currDate = now.strftime("%Y-%m-%d")
    from frappe.utils import now
    currDate = now()

    for d in data:
        try:
            filters = [["name", "=", d.get("item_code")]]
            doc_list = frappe.get_all("Item", filters=filters)

            # update
            if doc_list != None and len(doc_list) > 0:
                for d2 in doc_list:
                    doc = frappe.get_doc("Item", d2.get("name"))
                    if d.get("item_code"):
                        doc.name = d.get("item_code", None)
                    else:
                        doc.name = d.get("name", None)

                    doc.item_code = d.get("item_code", None)
                    doc.item_name = d.get("item_name", None)
                    doc.barcode = d.get("barcode", None)
                    doc.standard_rate = d.get("standard_rate", 0)
                    doc.valuation_rate = d.get("valuation_rate", 0)
                    doc.item_group = d.get("item_group", None)
                    doc.stock_uom = d.get("stock_uom", None)
                    doc.docstatus = int(d.get("docstatus", "0"))
                    doc.disabled = d.get("disabled", 0)
                    doc.brand = d.get("brand", None)
                    doc.is_purchase_item = d.get("is_purchase_item", 1)
                    doc.is_sales_item = d.get("is_sales_item", 1)
                    # doc.creation = d.get("creation", currDate)
                    # doc.modified = d.get("modified", currDate)
                    if (d.get("is_delete", 0) == "1"):
                        doc.delete()
                    else:
                     doc.save()

                     frappe.db.set_value("Item", doc.get("name"), "modified", d.get("modified"), update_modified=False)

            else:

                # insert
                doc = frappe.new_doc("Item")

                doc.name = d.get("name", None)
                doc.item_code = d.get("item_code", None)
                doc.item_name = d.get("item_name", None)
                doc.barcode = d.get("barcode", None)
                doc.standard_rate = d.get("standard_rate", 0)
                doc.valuation_rate = d.get("valuation_rate", 0)
                doc.item_group = d.get("item_group", None)
                doc.stock_uom = d.get("stock_uom", None)
                doc.docstatus = int(d.get("docstatus", "0"))
                doc.disabled = d.get("disabled", 0)
                doc.brand = d.get("brand", None)
                doc.is_purchase_item = d.get("is_purchase_item", 1)
                doc.is_sales_item = d.get("is_sales_item", 1)
                # doc.creation = d.get("creation", currDate)
                # doc.modified = d.get("modified", currDate)

                doc.save()

                frappe.db.set_value("Item", doc.get("name"), "creation", d.get("creation"), update_modified=False)
                frappe.db.set_value("Item", doc.get("name"), "modified", d.get("modified"), update_modified=False)

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
              "item_code",
              "item_name",
              "barcode",
              "standard_rate",
              "valuation_rate",
              "item_group",
              "stock_uom",
              "docstatus",
              "disabled",
              "brand",
              "is_purchase_item",
              "is_sales_item",
              "creation",
              "modified"]

    filters = [
        ["modified", ">", lastSyncDate], ["modified", "<", currDate]
    ]

    # doc_list = frappe.get_all("Item", fields=fields, filters=filters)
    doc_list = frappe.get_all("Item", fields=fields)

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
            doc.api_type = "Item"
            doc.creation = currDate
            doc.modified = currDate

            doc.save()

    except Exception, ex:
        print ex