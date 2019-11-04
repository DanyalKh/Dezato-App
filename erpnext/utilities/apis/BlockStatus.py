import json

import frappe


@frappe.whitelist(allow_guest=True)
def ChangeBlockStatus(data):
    try:
        data = json.loads(data)
        new_status = data["blockstatus"]

        sql = """update `tabDefaultValue` set defvalue = '{0}' where `defkey` = 'blockstatus'""".format(new_status)
        frappe.db.sql(sql)
        frappe.db.commit()

        ret_dict = {"status": 1, "msg": ""}
        if new_status == 1:
            ret_dict["msg"] = "Site has been blocked successfully."
        elif new_status == 0:
            ret_dict["msg"] = "Site has been unblocked successfully."

        ret_val = json.dumps(ret_dict)
        return  ret_val

    except Exception, ex:
        ret_dict = {"status": 0, "msg": ex}
        ret_val = json.dumps(ret_dict)
        return ret_val


@frappe.whitelist(allow_guest=True)
def GetCurrentBlockStatus():
    try:
        ret_dict = {"status": 1, "msg": "Site has been unblocked.", "blockstatus": 0}

        sql = """SELECT defvalue From `tabDefaultValue` where `defkey` = 'blockstatus' limit 1 """
        data = frappe.db.sql(sql, as_dict=1)

        for d in data:
            ret_dict["blockstatus"] = d["defvalue"]
            if d["defvalue"] == str(1):
                ret_dict["msg"] = "Site has been blocked."

        return ret_dict

    except Exception, ex:
        ret_dict = {"status": 0, "msg": ex, "blockstatus": 0}
        return ret_dict
