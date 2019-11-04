# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class FinishedGoods(Document):

    def on_submit(self):
        item = frappe.get_doc('Item', {'name': self.item})
        if item.default_warehouse:
            stock_entry = make_stock_entry(item_code=self.item, purpose="Material Receipt", target=item.default_warehouse, qty=self.quantity)
            stock_entry.add_comment("Comment", _("Updated Stock"))