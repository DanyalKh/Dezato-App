# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Recipe(Document):

	def on_update(self):
		ingredient = self.ingredient[0].get('ingredient')
		unit = self.ingredient[0].get('unit')
		qty = self.ingredient[0].get('quantity')
