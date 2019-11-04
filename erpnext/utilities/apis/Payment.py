import json

import datetime
import frappe
from erpnext.accounts.party import get_party_account


@frappe.whitelist(allow_guest=False)
def itemSync(data):
    data = json.loads(data)
    frappe.clear_cache(doctype="Payment Entry")
    frappe.clear_cache(doctype="Payment Entry Reference")
    logDataInsert(data["data"], data["user_name"], data["ip_address"], data["handset_model"], data["os_version"])
    updateItem(data["data"])
    ret_list = sendItem(data["lastSyncDate"])
    return ret_list


def updateItem(data):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d")
    from frappe.utils import now
    currDate = now()

    for d in data:

        if int(d.get("DocStatus", "0")) == 0:
            continue

        filters = [["name", "=", d.get("name")]]
        doc_list = frappe.get_all("Payment Entry", filters=filters)

        # update
        if doc_list != None and len(doc_list) > 0:
            try:
                for d2 in doc_list:
                    doc = frappe.get_doc("Payment Entry", d2.get("name"))
                    if doc.docstatus == 1 and int(d.get("docStatus", "0")) != 2:
                        continue
                    doc.name = d.get("name", None)
                    doc.party_type = d.get("party_type", None)
                    doc.payment_type = d.get("payment_type", None)
                    doc.mode_of_payment = d.get("mode_of_payment", None)
                    doc.posting_date = d.get("posting_date", None)
                    doc.party = d.get("party", None)
                    doc.paid_amount = d.get("paid_amount", 0)
                    doc.allocate_payment_amount = d.get("paid_amount", 0)
                    doc.base_paid_amount = d.get("paid_amount", 0)
                    doc.base_received_amount = d.get("paid_amount", 0)
                    doc.base_total_allocated_amount = d.get("paid_amount", 0)
                    doc.company = d.get("company", 0)
                    doc.doctype = "Payment Entry"
                    # doc.paid_from = "Accrued Rebates Due from Suppliers - TC"
                    doc.paid_from = "Accrued Rebates Due from Suppliers - TC"
                    doc.paid_from_account_currency = "AED"
                    doc.paid_to = "Main Safe - TC"
                    if int(d.get("docStatus", "0")) == 1:
                        doc.docstatus = 0  # int(d.get("DocStatus", "0"))
                    doc.paid_to_account_currency = "AED"
                    doc.party_balance = d.get("paid_amount", 0)
                    doc.party_name = d.get("party", None)
                    doc.received_amount = d.get("paid_amount", 0)
                    doc.source_exchange_rate = 1
                    doc.target_exchange_rate = 1
                    doc.total_allocated_amount = d.get("paid_amount", 0)
                    doc.items = []
                    b = 1
                    if d['item'] != None and len(d['item']) > 0:
                        f = doc.append('references', {})
                        # d = frappe.new_doc("Sales Invoice Item")
                        f.docstatus = int(d.get("DocStatus", "0"))
                        f.doctype = "Payment Entry Reference"
                        f.due_date = d['item']['due_date']
                        f.exchange_rate = 1
                        f.idx = b
                        b = b + 1
                        f.outstanding_amount = d['item']['outstanding_amount']
                        f.allocated_amount = d.get("paid_amount", 0)
                        f.parentfield = "references"
                        f.parenttype = "Payment Entry"
                        f.reference_doctype = "Sales Invoice"
                        f.reference_name = d['item']["reference_name"]
                        f.total_amount = d['item']['total_amount']

                    # doc.creation = d.get("creation", currDate)
                    # doc.modified = d.get("modified", currDate)
                    if (d.get("is_delete", 0) == "1"):
                       doc.delete()
                    else:
                        doc.save()

                        if int(d.get("DocStatus", "0")) == 1:
                            doc.run_method("on_submit")
                            frappe.db.set_value("Payment Entry", doc.get("name"), "docstatus", 1, update_modified=False)

                        frappe.db.set_value("Payment Entry", doc.get("name"), "modified", d.get("modified"),
                                            update_modified=False)


            except Exception, ex:
                 print ex





        else:
            try:
                # insert
                doc = frappe.new_doc("Payment Entry")
                doc.name = d.get("name", None)
                doc.party_type = d.get("party_type", None)
                doc.payment_type = d.get("payment_type", None)
                doc.mode_of_payment = d.get("mode_of_payment", None)
                doc.posting_date = d.get("posting_date", None)
                doc.party = d.get("party", None)
                doc.company = d.get("company", None)
                if d.get("party_type", None) == "Customer":
                    if doc.payment_type == "Receive":
                        doc.paid_to ="Main Safe - TC"
                        # doc.paid_from ="Trade Receivable - TC"
                        doc.paid_from = get_party_account("Customer", doc.party, doc.company)
                    else:
                        doc.paid_to = get_party_account("Customer", doc.party, doc.company)
                        doc.paid_from = "Main Safe - TC"


                else:
                    if doc.payment_type == "Receive":
                        # doc.paid_to ="Manual Visa & Master Cards - TC"
                        doc.paid_to ="Main Safe - TC"
                        # doc.paid_from ="Trade Receivable - TC"
                        doc.paid_from = get_party_account("Supplier", doc.party, doc.company)

                    else:
                        # doc.paid_to = "Consigned Payable - TC"
                        doc.paid_from = "Main Safe - TC"
                        # doc.paid_from = "Manual Visa & Master Cards - TC"
                        # doc.paid_to = "Accrued Rebates Due from Suppliers - TC"
                        doc.paid_to = get_party_account("Supplier", doc.party, doc.company)


                doc.paid_amount = d.get("paid_amount", 0)
                doc.allocate_payment_amount = d.get("paid_amount", 0)
                doc.base_paid_amount = d.get("paid_amount", 0)
                doc.base_received_amount = d.get("paid_amount", 0)
                doc.base_total_allocated_amount = d.get("paid_amount", 0)
                doc.difference_amount = 0
                doc.doctype = "Payment Entry"
                doc.letter_head = "DEMO Letter Head"
                doc.paid_from_account_balance = d.get("paid_amount", 0)
                doc.paid_from_account_currency = "AED"
                # doc.paid_to = "Main Safe - TC"
                if int(d.get("DocStatus", "0")) == 1:
                    doc.docstatus = 0
                doc.paid_to_account_currency = "AED"
                doc.party_balance = d.get("paid_amount", 0)
                doc.party_name = d.get("party", None)
                doc.received_amount = d.get("paid_amount", 0)
                doc.total_allocated_amount = d.get("paid_amount", 0)
                doc.is_api = 1

                doc.items = []
                b = 1
                if d['item'] != None and len(d['item']) > 0:
                        f = doc.append('references', {})
                        # d = frappe.new_doc("Sales Invoice Item")
                        f.docstatus = int(d.get("DocStatus", "0"))
                        f.doctype = "Payment Entry Reference"
                        f.due_date = d['item']['due_date']
                        f.exchange_rate = 1
                        f.idx = b
                        b = b + 1
                        f.outstanding_amount =d['item']['outstanding_amount']
                        f.allocated_amount = d.get("paid_amount", 0)
                        f.parentfield = "references"
                        f.parenttype = "Payment Entry"
                        f.reference_name = d['item']["reference_name"]
                        if "PI" in f.reference_name:
                            f.reference_doctype = "Purchase Invoice"
                        elif "SI" in f.reference_name:
                            f.reference_doctype = "Sales Invoice"

                        f.total_amount =d['item']['total_amount']


                # doc.creation = d.get("creation", currDate)
                # doc.modified = d.get("modified", currDate)

                doc.save()

                if int(d.get("DocStatus", "0")) == 1:
                    doc.run_method("on_submit")
                    frappe.db.set_value("Payment Entry", doc.get("name"), "docstatus", 1, update_modified=False)

                frappe.rename_doc("Payment Entry", doc.name, d.get("name", None), ignore_permissions=True)

                frappe.db.set_value("Payment Entry", doc.get("name"), "creation", d.get("modified"),
                                    update_modified=False)
                frappe.db.set_value("Payment Entry", doc.get("name"), "modified", d.get("modified"),
                                    update_modified=False)



            except Exception, ex:
                print ex



def sendItem(lastSyncDate):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d %H:%M:%S")
    from frappe.utils import now
    currDate = now()

    # filters = [
    #     ["modified", ">", lastSyncDate], ["modified", "<", currDate]
    # ]
    filters = [
        ["docstatus", "!=", 0]
    ]

    fields = ["name",
              "payment_type",
              "posting_date",
              "party_type",
              "paid_amount",
              "docstatus",
              "party",
              "creation",
              "modified",
              ]
    doc_list = frappe.get_all("Payment Entry", fields=fields, filters=filters)

    for doc_list_lis in doc_list:
        fieldsItem = ["parent",
                      "reference_name",
                      "due_date",
                      "total_amount",
                      "outstanding_amount",
                      "creation",
                      "modified",
                      ]
        filtersItem = [
            ["parent", "=", doc_list_lis.name]
        ]

        doc_list_lis.item = frappe.get_all("Payment Entry Reference", fields=fieldsItem, filters=filtersItem)

    status = 0

    if doc_list != None:
        if len(doc_list) > 0:
            status = 1

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
            doc.api_type = "Payment"
            doc.creation = currDate
            doc.modified = currDate

            doc.save()

    except Exception, ex:
        print ex