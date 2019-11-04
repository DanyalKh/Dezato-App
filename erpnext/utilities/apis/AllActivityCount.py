import json

import datetime
import frappe


@frappe.whitelist(allow_guest=False)
def itemSync(data):
    ret_list = {}
    data = json.loads(data)
    # frappe.clear_cache(doctype="Item Group")
    ret_list = sendItem(data["StartDate"],data['EndDate'])
    return ret_list


def sendItem(StartDate,EndDate):
    from frappe.utils import now

    doc_list = []
    doctype_name = ["UOM","Territory","Payment Entry","Customer","Supplier","Item Group","Item","Sales Invoice","Purchase Invoice","Company"]

    for doctype_name_list in doctype_name:
      if doctype_name_list == 'Sales Invoice':
          filters = [
              ["creation", ">", StartDate], ["creation", "<", EndDate],["is_return","=",0]
          ]

          doc_list_all_insertion = frappe.get_all(doctype_name_list, filters=filters)

          filters1 = [
              ["modified", ">", StartDate], ["modified", "<", EndDate],["is_return","=",0]
          ]

          doc_list_all_update = frappe.get_all(doctype_name_list, filters=filters1)

          inner_doc_list = {}
          doc_list2 = len(doc_list_all_insertion)
          doc_list3 = len(doc_list_all_update)
          inner_doc_list = {
              'Type': doctype_name_list,
              'Insertion': doc_list2,
              'Updation': doc_list3
          }

          doc_list.append(inner_doc_list)


          filters2 = [
              ["creation", ">", StartDate], ["creation", "<", EndDate], ["is_return", "=", 1]
          ]

          doc_list_all_insertion = frappe.get_all(doctype_name_list, filters=filters2)

          inner_doc_list = {}
          doc_list2 = len(doc_list_all_insertion)
          inner_doc_list = {
              'Type': "Sales Return",
              'Insertion': doc_list2,
              'Updation': 0
          }

          doc_list.append(inner_doc_list)

      if doctype_name_list == 'Purchase Invoice':

          filters = [
              ["creation", ">", StartDate], ["creation", "<", EndDate], ["is_return", "=", 0]
          ]

          doc_list_all_insertion = frappe.get_all(doctype_name_list, filters=filters)

          filters1 = [
              ["modified", ">", StartDate], ["modified", "<", EndDate], ["is_return", "=", 0]
          ]

          doc_list_all_update = frappe.get_all(doctype_name_list, filters=filters1)

          inner_doc_list = {}
          doc_list2 = len(doc_list_all_insertion)
          doc_list3 = len(doc_list_all_update)
          inner_doc_list = {
              'Type': doctype_name_list,
              'Insertion': doc_list2,
              'Updation': doc_list3
          }

          doc_list.append(inner_doc_list)

          filters2 = [
              ["creation", ">", StartDate], ["creation", "<", EndDate], ["is_return", "=", 1]
          ]

          doc_list_all_insertion = frappe.get_all(doctype_name_list, filters=filters2)

          inner_doc_list = {}
          doc_list2 = len(doc_list_all_insertion)
          inner_doc_list = {
              'Type': "Purchase Return",
              'Insertion': doc_list2,
              'Updation': 0
          }

          doc_list.append(inner_doc_list)

      if doctype_name_list == 'Payment Entry':

          filters = [
              ["creation", ">", StartDate], ["creation", "<", EndDate], ["payment_type", "=", "Pay"]
          ]

          doc_list_all_insertion = frappe.get_all(doctype_name_list, filters=filters)

          inner_doc_list = {}
          doc_list2 = len(doc_list_all_insertion)
          doc_list3 = 0
          inner_doc_list = {
              'Type': "Pay",
              'Insertion': doc_list2,
              'Updation': doc_list3
          }

          doc_list.append(inner_doc_list)

          filters2 = [
              ["creation", ">", StartDate], ["creation", "<", EndDate], ["payment_type", "=", "Receive"]
          ]

          doc_list_all_insertion = frappe.get_all(doctype_name_list, filters=filters2)

          inner_doc_list = {}
          doc_list2 = len(doc_list_all_insertion)
          inner_doc_list = {
              'Type': "Receive",
              'Insertion': doc_list2,
              'Updation': 0
          }

          doc_list.append(inner_doc_list)



      else:

        filters = [
            ["creation", ">", StartDate], ["creation", "<", EndDate]
        ]

        doc_list_all_insertion = frappe.get_all(doctype_name_list, filters=filters)

        filters1 = [
            ["modified", ">", StartDate], ["modified", "<", EndDate]
        ]

        doc_list_all_update = frappe.get_all(doctype_name_list, filters=filters1)

        inner_doc_list={}
        doc_list2= len(doc_list_all_insertion)
        doc_list3= len(doc_list_all_update)
        inner_doc_list = {
            'Type':doctype_name_list,
            'Insertion':doc_list2,
            'Updation':doc_list3
        }

        doc_list.append(inner_doc_list)







    return {
        "data": doc_list
    }


