import json

# import datetime
import frappe


@frappe.whitelist(allow_guest=False)
def itemSync(data):
    ret_list = {}
    data = json.loads(data)
    frappe.clear_cache(doctype="Customer")
    frappe.clear_cache(doctype="Supplier")
    logDataInsert(data["data"], data["user_name"], data["ip_address"], data["handset_model"], data["os_version"])
    res = updateItem(data["data"])
    ret_list = sendItem(data["lastSyncDate"])
    if res == -1:
        ret_list["status"] = -1

    return ret_list


def updateItem(data):
    from frappe.utils import now
    currDate = now()
    # global ret_list
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d")

    for d in data:
        if (d['party_type'] == "Customer"):

                filters = [["name", "=", d.get("name")]]
                doc_list = frappe.get_all("Customer", filters=filters)

                # update
                if doc_list != None and len(doc_list) > 0:
                 try:
                    for d2 in doc_list:
                        doc = frappe.get_doc("Customer", d2.get("name"))
                        doc.name = d.get("name", None)
                        doc.salutation = d.get("salutation", None)
                        doc.gender = d.get("gender", None)
                        doc.disabled = d.get("disabled", 0)
                        doc.customer_type = d.get("customer_type", None)
                        doc.customer_name = d.get("customer_name", None)
                        doc.tax_id = d.get("tax_id", 0)
                        doc.customer_group = d.get("customer_group", None)
                        doc.territory = d.get("territory", None)
                        doc.mobile_number = d.get("mobile_number", 0)
                        doc.docstatus = int(d.get("docstatus", "0"))
                        # doc_add.is_primary_address = data['address']['is_primary_address']
                        # doc_add.is_shipping_address = data['address']['is_shipping_address']

                        # doc.creation = d.get("creation", currDate)
                        # doc.modified = d.get("modified", currDate)

                        if (d.get("is_delete", 0) == "1"):
                            doc.delete()
                        else:
                            doc.save(ignore_permissions=True)

                            frappe.db.set_value("Customer", doc.get("name"), "modified", d.get("modified"),
                                                update_modified=False)

                        if d['address'] != "None" and len(d['address']) > 0:

                            sql = """SELECT a.name,a.address_line1,a.address_line2,a.city,a.pincode,a.country,a.email_id,a.fax,a.phone
                                       FROM tabAddress a
                                       INNER JOIN `tabDynamic Link` dl ON (a.name = dl.parent)
                                       WHERE dl.link_doctype = 'Customer'
                                       AND dl.link_name = '{0}'""".format(doc_list[0]['name'])
                            add = frappe.db.sql(sql, as_dict=1)
                            doc_list_address = add

                            # update
                            if doc_list_address != None and len(doc_list_address) > 0:
                                for d3 in doc_list_address:
                                    doc_add = frappe.get_doc("Address", d3.get("name"))

                                    doc_add.address_line1 = d['address']['address_line1']
                                    doc_add.address_line2 = d['address']['address_line2']
                                    doc_add.city = d['address']['city']
                                    doc_add.country = d['address']['country']
                                    doc_add.pincode = d['address']['pincode']
                                    doc_add.email_id = d['address']['email_id']
                                    doc_add.phone = d['address']['phone']
                                    doc_add.fax = d['address']['fax']
                                    doc_add.is_primary_address = d['address']['is_primary_address']
                                    doc_add.is_shipping_address = d['address']['is_shipping_address']
                                    # doc_add.is_your_company_address = data['address']['is_your_company_address']
                                    # doc_add.creation = currDate
                                    # doc_add.modified = currDate

                                    doc_add.save()

                                    frappe.db.set_value("Address", doc.get("name"), "modified", d['modified'],
                                                        update_modified=False)



                 except Exception, ex:
                    return -1
                    print ex





                else:
                  try:
                    # insert
                    doc = frappe.new_doc("Customer")

                    doc.name = d.get("name", None)
                    doc.salutation = d.get("salutation", None)
                    doc.gender = d.get("gender", None)
                    doc.customer_type = d.get("customer_type", 0)
                    doc.customer_name = d.get("customer_name", 0)
                    doc.tax_id = d.get("tax_id", 0)
                    doc.disabled = d.get("disabled", 0)
                    doc.customer_group = d.get("customer_group", 0)
                    doc.territory = d.get("territory", 0)
                    doc.mobile_number = d.get("mobile_number", 0)
                    doc.docstatus = int(d.get("docstatus", "0"))
                    # doc_add.is_primary_address = data['address']['is_primary_address']
                    # doc_add.is_shipping_address = data['address']['is_shipping_address']

                    # doc.creation = d.get("creation", currDate)
                    # doc.modified = d.get("modified", currDate)

                    doc.save(ignore_permissions=True)

                    if d.get("creation", currDate) == "null":
                        creation_date = currDate
                    else:
                        creation_date = d.get("modified")

                    frappe.db.set_value("Customer", doc.get("name"), "creation", creation_date, update_modified=False)
                    frappe.db.set_value("Customer", doc.get("name"), "modified", creation_date,
                                        update_modified=False)

                    if d['address'] != "None" and len(d['address']) > 0:
                        doc_address = frappe.new_doc("Address")

                        doc_address.address_line1 = d['address']['address_line1']
                        doc_address.address_line2 = d['address']['address_line2']
                        doc_address.city = d['address']['city']
                        doc_address.country = d['address']['country']
                        doc_address.pincode = d['address']['pincode']
                        doc_address.email_id = d['address']['email_id']
                        doc_address.phone = d['address']['phone']
                        doc_address.fax = d['address']['fax']
                        doc_address.is_primary_address = d['address']['is_primary_address']
                        doc_address.is_shipping_address = d['address']['is_shipping_address']

                        doc_address.address_type = "Billing"
                        doc_address.country = "United Arab Emirates"
                        doc_address.docstatus = 0
                        doc_address.doctype = "Address"
                        doc_address.is_your_company_address = 0
                        doc_address.name = "New Address 1"
                        doc_address.docname = "New Address 1"

                        doc_address.links = []

                        e = doc_address.append('links', {})
                        e.docstatus = 0
                        e.doctype = "Dynamic Link"
                        e.idx = 1
                        e.link_doctype = "Customer"
                        e.link_name = d.get("name", None)
                        e.name = "New Dynamic Link 1"
                        e.parent = "New Address 1"
                        e.parentfield = "links"
                        e.parenttype = "Address"

                        if doc_address.address_line1 != "" and doc_address.city != "":

                            doc_address.save(ignore_permissions=True)

                            if d.get("creation", currDate) == "null":
                                creation_date = currDate
                            else:
                                creation_date = d.get("modified")

                            frappe.db.set_value("Address", doc.get("name"), "creation", creation_date,
                                                update_modified=False)
                            frappe.db.set_value("Address", doc.get("name"), "modified", creation_date,
                                                update_modified=False)


                  except Exception, ex:
                      print ex
                      return -1



        else:

            # for d in data:

                    filters = [["name", "=", d.get("name")]]
                    doc_list = frappe.get_all("Supplier", filters=filters)

                    # update
                    if doc_list != None and len(doc_list) > 0:
                     try:
                        for d2 in doc_list:
                            doc = frappe.get_doc("Supplier", d2.get("name"))

                            doc.name = d.get("name", None)
                            doc.parent = d.get("supplier_type", None)
                            doc.parent_item_group = d.get("country", None)
                            doc.tax_id = d.get("tax_id", 0)
                            doc.supplier_name = d.get("supplier_name", None)
                            doc.mobile_number = d.get("mobile_number", 0)
                            doc.disabled = d.get("disabled", 0)
                            doc.docstatus = int(d.get("docstatus", "0"))
                            # doc_add.is_primary_address = data['address']['is_primary_address']
                            # doc_add.is_shipping_address = data['address']['is_shipping_address']

                            # doc.creation = d.get("creation", currDate)
                            # doc.modified = d.get("modified", currDate)
                            if (d.get("is_delete", 0) == "1"):
                                doc.delete()
                            else:

                                doc.save(ignore_permissions=True)

                                frappe.db.set_value("Supplier", doc.get("name"), "modified", d.get("modified"), update_modified=False)

                            if d['address'] != "None" and len(d['address']) > 0:

                                sql = """SELECT a.name,a.address_line1,a.address_line2,a.city,a.pincode,a.country,a.email_id,a.fax,a.phone
                                           FROM tabAddress a
                                           INNER JOIN `tabDynamic Link` dl ON (a.name = dl.parent)
                                           WHERE dl.link_doctype = 'Supplier'
                                           AND dl.link_name = '{0}'""".format(doc_list[0]['name'])
                                add = frappe.db.sql(sql, as_dict=1)
                                doc_list_address = add

                                # update
                                if doc_list_address != None and len(doc_list_address) > 0:
                                    for d3 in doc_list_address:
                                        doc_add = frappe.get_doc("Address", d3.get("name"))

                                        doc_add.address_line1 = d['address']['address_line1']
                                        doc_add.address_line2 = d['address']['address_line2']
                                        doc_add.city = d['address']['city']
                                        doc_add.country = d['address']['country']
                                        doc_add.pincode = d['address']['pincode']
                                        doc_add.email_id = d['address']['email_id']
                                        doc_add.phone = d['address']['phone']
                                        doc_add.fax = d['address']['fax']
                                        doc_add.is_primary_address = d['address']['is_primary_address']
                                        doc_add.is_shipping_address = d['address']['is_shipping_address']
                                        # doc_add.is_your_company_address = data['address']['is_your_company_address']
                                        # doc_add.creation = currDate
                                        # doc_add.modified = currDate

                                        doc_add.save()

                                        frappe.db.set_value("Address", doc.get("name"), "modified", d['modified'],
                                                            update_modified=False)



                     except Exception, ex:
                       return -1
                       print ex

                    else:
                      try:
                        # insert
                        doc = frappe.new_doc("Supplier")

                        doc.name = d.get("name", None)
                        doc.supplier_type = d.get("supplier_type", None)
                        doc.country = d.get("country", None)
                        doc.tax_id = d.get("tax_id", 0)
                        doc.disabled = d.get("disabled", 0)
                        doc.supplier_name = d.get("supplier_name", None)
                        doc.mobile_number = d.get("mobile_number", None)
                        doc.docstatus = int(d.get("docstatus", "0"))
                        # doc_add.is_primary_address = data['address']['is_primary_address']
                        # doc_add.is_shipping_address = data['address']['is_shipping_address']

                        # doc.creation = d.get("creation", currDate)
                        # doc.modified = d.get("modified", currDate)

                        doc.save(ignore_permissions=True)

                        if d.get("modified", currDate) == "null":
                            creation_date = currDate
                        else:
                            creation_date = d.get("modified")

                        frappe.db.set_value("Supplier", doc.get("name"), "creation", creation_date, update_modified=False)
                        frappe.db.set_value("Supplier", doc.get("name"), "modified", creation_date, update_modified=False)

                        if d['address'] != "None" and len(d['address']) > 0:
                            doc_address = frappe.new_doc("Address")

                            doc_address.address_line1 = d['address']['address_line1']
                            doc_address.address_line2 = d['address']['address_line2']
                            doc_address.city = d['address']['city']
                            doc_address.country = d['address']['country']
                            doc_address.pincode = d['address']['pincode']
                            doc_address.email_id = d['address']['email_id']
                            doc_address.phone = d['address']['phone']
                            doc_address.fax = d['address']['fax']
                            doc_address.is_primary_address = d['address']['is_primary_address']
                            doc_address.is_shipping_address = d['address']['is_shipping_address']

                            doc_address.address_type = "Billing"
                            doc_address.country = "United Arab Emirates"
                            doc_address.docstatus = 0
                            doc_address.doctype = "Address"
                            doc_address.is_your_company_address = 0
                            doc_address.name = "New Address 1"
                            doc_address.docname = "New Address 1"

                            doc_address.links = []

                            e = doc_address.append('links', {})
                            e.docstatus = 0
                            e.doctype = "Dynamic Link"
                            e.idx = 1
                            e.link_doctype = "Supplier"
                            e.link_name = d.get("name", None)
                            e.name = "New Dynamic Link 1"
                            e.parent = "New Address 1"
                            e.parentfield = "links"
                            e.parenttype = "Address"

                            if doc_address.address_line1 != "" and doc_address.city !="":
                                doc_address.save(ignore_permissions=True)

                                if d.get("creation", currDate) == "null":
                                    creation_date = currDate
                                else:
                                    creation_date = d.get("modified")

                                frappe.db.set_value("Address", doc.get("name"), "creation", creation_date,
                                                    update_modified=False)
                                frappe.db.set_value("Address", doc.get("name"), "modified", creation_date,
                                                    update_modified=False)




                      except Exception, ex:
                        return -1
                        print ex


def sendItem(lastSyncDate):
    # now = datetime.datetime.now()
    # currDate = now.strftime("%Y-%m-%d %H:%M:%S")
    from frappe.utils import now
    currDate = now()

    from frappe.contacts.doctype.address.address import get_default_address


    filters = [
        ["modified", ">", lastSyncDate], ["modified", "<", currDate]
    ]

    fields = ["name",
              "salutation",
              "gender",
              "customer_type",
              "customer_name",
              "tax_id",
              "disabled",
              "customer_group",
              "territory",
              "mobile_number",
              "docstatus",
              # "is_primary_address",
              # "is_shipping_address",
              "creation",
              "modified"
              ]
    # doc_list = frappe.get_all("Customer", fields=fields, filters=filters)
    doc_list = frappe.get_all("Customer", fields=fields)

    # for doc_list_item in doc_list:
    #     doc_list_item.party_type = "Customer"
    #
    #     add_name = get_default_address("Customer", doc_list_item.name)
    #     doc_list_item.is_primary_address = 0
    #     doc_list_item.is_shipping_address = 0
    #     if add_name != None:
    #         add_doc = frappe.get_doc("Address", add_name)
    #         doc_list_item.is_primary_address =  add_doc.is_primary_address
    #         doc_list_item.is_shipping_address = add_doc.is_shipping_address

    for customer_list in doc_list:
        customer_list.party_type = "Customer"
        add_name = get_default_address("Customer", customer_list.name)
        if add_name != None:

           sql = """SELECT a.name,a.address_line1,a.address_line2,a.city,a.pincode,a.country,a.email_id,a.fax,a.phone,is_primary_address,is_shipping_address
           FROM tabAddress a
           INNER JOIN `tabDynamic Link` dl ON (a.name = dl.parent)
           WHERE dl.link_doctype = 'Customer'
           AND dl.link_name = "{0}" """.format(customer_list['name'])
           add = frappe.db.sql(sql, as_dict=1)
           customer_list.address = add[0]




    fields1 = ["name",
               "supplier_type",
               "country",
               "supplier_name",
               "tax_id",
               "mobile_number",
               "docstatus",
               "disabled",
               # "is_primary_address",
               # "is_shipping_address",
               "creation",
               "modified"
               ]
    # doc_list_supplier = frappe.get_all("Supplier", fields=fields1, filters=filters)


    # for doc_list_item in doc_list_supplier:
    #     doc_list_item.party_type = "Supplier"
    #
    #     add_name = get_default_address("Supplier", doc_list_item.name)
    #     doc_list_item.is_primary_address = 0
    #     doc_list_item.is_shipping_address = 0
    #     if add_name != None:
    #         add_doc = frappe.get_doc("Address", add_name)
    #         doc_list_item.is_primary_address =  add_doc.is_primary_address
    #         doc_list_item.is_shipping_address = add_doc.is_shipping_address
    #
    #     doc_list.append(doc_list_item)

    doc_list1 = frappe.get_all("Supplier", fields=fields1)

    for doc_list_supplier in doc_list1:
        doc_list_supplier.party_type = "Supplier"
        add_name = get_default_address("Supplier", doc_list_supplier.name)
        if add_name != None:

           sql = """SELECT a.name,a.address_line1,a.address_line2,a.city,a.pincode,a.country,a.email_id,a.fax,a.phone,is_primary_address,is_shipping_address
           FROM tabAddress a
           INNER JOIN `tabDynamic Link` dl ON (a.name = dl.parent)
           WHERE dl.link_doctype = 'Supplier'
           AND dl.link_name = "{0}" """.format(doc_list_supplier['name'])
           add = frappe.db.sql(sql, as_dict=1)
           doc_list_supplier.address = add[0]

        doc_list.append(doc_list_supplier)



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
            doc.api_type = "Party"
            doc.creation = currDate
            doc.modified = currDate

            doc.save()

    except Exception, ex:
        print ex