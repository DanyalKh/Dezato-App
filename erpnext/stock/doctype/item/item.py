# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import erpnext
import json
import itertools
from frappe import msgprint, _
from frappe.utils import (cstr, flt, cint, getdate, now_datetime, formatdate,
	strip, get_timestamp, random_string)
from frappe.website.website_generator import WebsiteGenerator
from erpnext.setup.doctype.item_group.item_group import invalidate_cache_for, get_parent_item_groups
from frappe.website.render import clear_cache
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow
from erpnext.controllers.item_variant import (get_variant, copy_attributes_to_variant,
	make_variant_item_code, validate_item_variant_attributes, ItemVariantExistsError)

class DuplicateReorderRows(frappe.ValidationError): pass

class Item(WebsiteGenerator):
	website = frappe._dict(
		page_title_field = "item_name",
		condition_field = "show_in_website",
		template = "templates/generators/item.html",
		no_cache = 1
	)

	def onload(self):
		super(Item, self).onload()
		self.set_onload('sle_exists', self.check_if_sle_exists())
		if self.is_fixed_asset:
			asset = frappe.db.get_all("Asset", filters={"item_code": self.name, "docstatus": 1}, limit=1)
			self.set_onload("asset_exists", True if asset else False)

	def autoname(self):
		if frappe.db.get_default("item_naming_by")=="Naming Series":
			if self.variant_of:
				if not self.item_code:
					template_item_name = frappe.db.get_value("Item", self.variant_of, "item_name")
					self.item_code = make_variant_item_code(self.variant_of, template_item_name, self)
			else:
				from frappe.model.naming import make_autoname
				self.item_code = make_autoname(self.naming_series+'.#####')
		elif not self.item_code:
			msgprint(_("Item Code is mandatory because Item is not automatically numbered"), raise_exception=1)

		self.item_code = strip(self.item_code)
		self.name = self.item_code

	def before_insert(self):
		if not self.description:
			self.description = self.item_name

		self.publish_in_hub = 1

	def after_insert(self):
		'''set opening stock and item price'''
		if self.standard_rate:
			self.add_price()

		if self.opening_stock:
			self.set_opening_stock()

	def validate(self):
		super(Item, self).validate()

		if not self.item_name:
			self.item_name = self.item_code

		if not self.description:
			self.description = self.item_name

		self.validate_uom()
		self.add_default_uom_in_conversion_factor_table()
		self.validate_conversion_factor()
		self.validate_item_type()
		self.check_for_active_boms()
		self.fill_customer_code()
		self.check_item_tax()
		self.validate_barcode()
		self.cant_change()
		self.validate_warehouse_for_reorder()
		self.update_item_desc()
		self.synced_with_hub = 0

		self.validate_has_variants()
		self.validate_attributes()
		self.validate_variant_attributes()
		self.validate_website_image()
		self.make_thumbnail()
		self.validate_fixed_asset()
		self.item_check()

		if not self.get("__islocal"):
			self.old_item_group = frappe.db.get_value(self.doctype, self.name, "item_group")
			self.old_website_item_groups = frappe.db.sql_list("""select item_group
				from `tabWebsite Item Group`
				where parentfield='website_item_groups' and parenttype='Item' and parent=%s""", self.name)

	def item_check(self):

		import re
		regex = r"^[A-z0-9= .&]+$"
		if not re.search(regex, self.item_name):
			frappe.throw(_("Special Character Not Allowed In Item name."))
		elif not re.search(regex, self.item_code):
			frappe.throw(_("Special Character Not Allowed In Item Code."))

	def on_update(self):
		invalidate_cache_for_item(self)
		self.validate_name_with_item_group()
		self.update_variants()
		self.update_item_price()
		self.update_template_item()

	def add_price(self, price_list=None):
		'''Add a new price'''
		if not price_list:
			price_list = (frappe.db.get_single_value('Selling Settings', 'selling_price_list')
				or frappe.db.get_value('Price List', _('Standard Selling')))
		if price_list:
			item_price = frappe.get_doc({
				"doctype": "Item Price",
				"price_list": price_list,
				"item_code": self.name,
				"currency": erpnext.get_default_currency(),
				"price_list_rate": self.standard_rate
			})
			item_price.insert()

	def set_opening_stock(self):
		'''set opening stock'''
		if not self.is_stock_item or self.has_serial_no or self.has_batch_no:
			return

		if not self.valuation_rate and self.standard_rate:
			self.valuation_rate = self.standard_rate

		if not self.valuation_rate:
			frappe.throw(_("Valuation Rate is mandatory if Opening Stock entered"))

		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		# default warehouse, or Stores
		default_warehouse = (self.default_warehouse
			or frappe.db.get_single_value('Stock Settings', 'default_warehouse')
			or frappe.db.get_value('Warehouse', {'warehouse_name': _('Stores')}))

		if default_warehouse:
			stock_entry = make_stock_entry(item_code=self.name, target=default_warehouse,
				qty=self.opening_stock, rate=self.valuation_rate)

			stock_entry.add_comment("Comment", _("Opening Stock"))

	def make_route(self):
		if not self.route:
			return cstr(frappe.db.get_value('Item Group', self.item_group,
				'route')) + '/' + self.scrub(self.item_name + '-' + random_string(5))

	def validate_website_image(self):
		"""Validate if the website image is a public file"""
		auto_set_website_image = False
		if not self.website_image and self.image:
			auto_set_website_image = True
			self.website_image = self.image

		if not self.website_image:
			return

		# find if website image url exists as public
		file_doc = frappe.get_all("File", filters={
			"file_url": self.website_image
		}, fields=["name", "is_private"], order_by="is_private asc", limit_page_length=1)


		if file_doc:
			file_doc = file_doc[0]

		if not file_doc:
			if not auto_set_website_image:
				frappe.msgprint(_("Website Image {0} attached to Item {1} cannot be found")
					.format(self.website_image, self.name))

			self.website_image = None

		elif file_doc.is_private:
			if not auto_set_website_image:
				frappe.msgprint(_("Website Image should be a public file or website URL"))

			self.website_image = None

	def make_thumbnail(self):
		"""Make a thumbnail of `website_image`"""
		import requests.exceptions

		if not self.is_new() and self.website_image != frappe.db.get_value(self.doctype, self.name, "website_image"):
			self.thumbnail = None

		if self.website_image and not self.thumbnail:
			file_doc = None

			try:
				file_doc = frappe.get_doc("File", {
					"file_url": self.website_image,
					"attached_to_doctype": "Item",
					"attached_to_name": self.name
				})
			except frappe.DoesNotExistError:
				pass
				# cleanup
				frappe.local.message_log.pop()

			except requests.exceptions.HTTPError:
				frappe.msgprint(_("Warning: Invalid attachment {0}").format(self.website_image))
				self.website_image = None

			except requests.exceptions.SSLError:
				frappe.msgprint(_("Warning: Invalid SSL certificate on attachment {0}").format(self.website_image))
				self.website_image = None

			# for CSV import
			if self.website_image and not file_doc:
				try:
					file_doc = frappe.get_doc({
						"doctype": "File",
						"file_url": self.website_image,
						"attached_to_doctype": "Item",
						"attached_to_name": self.name
					}).insert()

				except IOError:
					self.website_image = None

			if file_doc:
				if not file_doc.thumbnail_url:
					file_doc.make_thumbnail()

				self.thumbnail = file_doc.thumbnail_url

	def validate_fixed_asset(self):
		if self.is_fixed_asset:
			if self.is_stock_item:
				frappe.throw(_("Fixed Asset Item must be a non-stock item."))

			if not self.asset_category:
				frappe.throw(_("Asset Category is mandatory for Fixed Asset item"))

	def get_context(self, context):
		context.show_search=True
		context.search_link = '/product_search'

		context.parents = get_parent_item_groups(self.item_group)

		self.set_variant_context(context)
		self.set_attribute_context(context)
		self.set_disabled_attributes(context)

		return context

	def set_variant_context(self, context):
		if self.has_variants:
			context.no_cache = True

			# load variants
			# also used in set_attribute_context
			context.variants = frappe.get_all("Item",
				filters={"variant_of": self.name, "show_variant_in_website": 1},
				order_by="name asc")

			variant = frappe.form_dict.variant
			if not variant and context.variants:
				# the case when the item is opened for the first time from its list
				variant = context.variants[0]

			if variant:
				context.variant = frappe.get_doc("Item", variant)

				for fieldname in ("website_image", "web_long_description", "description",
					"website_specifications"):
					if context.variant.get(fieldname):
						value = context.variant.get(fieldname)
						if isinstance(value, list):
							value = [d.as_dict() for d in value]

						context[fieldname] = value

		if self.slideshow:
			if context.variant and context.variant.slideshow:
				context.update(get_slideshow(context.variant))
			else:
				context.update(get_slideshow(self))

	def set_attribute_context(self, context):
		if self.has_variants:
			attribute_values_available = {}
			context.attribute_values = {}
			context.selected_attributes = {}

			# load attributes
			for v in context.variants:
				v.attributes = frappe.get_all("Item Variant Attribute",
					fields=["attribute", "attribute_value"], filters={"parent": v.name})

				for attr in v.attributes:
					values = attribute_values_available.setdefault(attr.attribute, [])
					if attr.attribute_value not in values:
						values.append(attr.attribute_value)

					if v.name==context.variant.name:
						context.selected_attributes[attr.attribute] = attr.attribute_value

			# filter attributes, order based on attribute table
			for attr in self.attributes:
				values = context.attribute_values.setdefault(attr.attribute, [])

				if cint(frappe.db.get_value("Item Attribute", attr.attribute, "numeric_values")):
					for val in sorted(attribute_values_available.get(attr.attribute, []), key=flt):
						values.append(val)

				else:
					# get list of values defined (for sequence)
					for attr_value in frappe.db.get_all("Item Attribute Value",
						fields=["attribute_value"], filters={"parent": attr.attribute}, order_by="idx asc"):

						if attr_value.attribute_value in attribute_values_available.get(attr.attribute, []):
							values.append(attr_value.attribute_value)

			context.variant_info = json.dumps(context.variants)

	def set_disabled_attributes(self, context):
		"""Disable selection options of attribute combinations that do not result in a variant"""
		if not self.attributes or not self.has_variants:
			return

		context.disabled_attributes = {}
		attributes = [attr.attribute for attr in self.attributes]

		def find_variant(combination):
			for variant in context.variants:
				if len(variant.attributes) < len(attributes):
					continue

				if "combination" not in variant:
					ref_combination = []

					for attr in variant.attributes:
						idx = attributes.index(attr.attribute)
						ref_combination.insert(idx, attr.attribute_value)

					variant["combination"] = ref_combination

				if not (set(combination) - set(variant["combination"])):
					# check if the combination is a subset of a variant combination
					# eg. [Blue, 0.5] is a possible combination if exists [Blue, Large, 0.5]
					return True

		for i, attr in enumerate(self.attributes):
			if i==0:
				continue

			combination_source = []

			# loop through previous attributes
			for prev_attr in self.attributes[:i]:
				combination_source.append([context.selected_attributes.get(prev_attr.attribute)])

			combination_source.append(context.attribute_values[attr.attribute])

			for combination in itertools.product(*combination_source):
				if not find_variant(combination):
					context.disabled_attributes.setdefault(attr.attribute, []).append(combination[-1])

	def add_default_uom_in_conversion_factor_table(self):
		uom_conv_list = [d.uom for d in self.get("uoms")]
		if self.stock_uom not in uom_conv_list:
			ch = self.append('uoms', {})
			ch.uom = self.stock_uom
			ch.conversion_factor = 1

		to_remove = []
		for d in self.get("uoms"):
			if d.conversion_factor == 1 and d.uom != self.stock_uom:
				to_remove.append(d)

		[self.remove(d) for d in to_remove]

	def update_template_tables(self):
		template = frappe.get_doc("Item", self.variant_of)

		# add item taxes from template
		for d in template.get("taxes"):
			self.append("taxes", {"tax_type": d.tax_type, "tax_rate": d.tax_rate})

		# copy re-order table if empty
		if not self.get("reorder_levels"):
			for d in template.get("reorder_levels"):
				n = {}
				for k in ("warehouse", "warehouse_reorder_level",
					"warehouse_reorder_qty", "material_request_type"):
					n[k] = d.get(k)
				self.append("reorder_levels", n)

	def validate_conversion_factor(self):
		check_list = []
		for d in self.get('uoms'):
			if cstr(d.uom) in check_list:
				frappe.throw(_("Unit of Measure {0} has been entered more than once in Conversion Factor Table").format(d.uom))
			else:
				check_list.append(cstr(d.uom))

			if d.uom and cstr(d.uom) == cstr(self.stock_uom) and flt(d.conversion_factor) != 1:
				frappe.throw(_("Conversion factor for default Unit of Measure must be 1 in row {0}").format(d.idx))

	def validate_item_type(self):
		if self.has_serial_no == 1 and self.is_stock_item == 0:
			msgprint(_("'Has Serial No' can not be 'Yes' for non-stock item"), raise_exception=1)

		if self.has_serial_no == 0 and self.serial_no_series:
			self.serial_no_series = None


	def check_for_active_boms(self):
		if self.default_bom:
			bom_item = frappe.db.get_value("BOM", self.default_bom, "item")
			if bom_item not in (self.name, self.variant_of):
				frappe.throw(_("Default BOM ({0}) must be active for this item or its template").format(bom_item))

	def fill_customer_code(self):
		""" Append all the customer codes and insert into "customer_code" field of item table """
		cust_code=[]
		for d in self.get('customer_items'):
			cust_code.append(d.ref_code)
		self.customer_code=','.join(cust_code)

	def check_item_tax(self):
		"""Check whether Tax Rate is not entered twice for same Tax Type"""
		check_list=[]
		for d in self.get('taxes'):
			if d.tax_type:
				account_type = frappe.db.get_value("Account", d.tax_type, "account_type")

				if account_type not in ['Tax', 'Chargeable', 'Income Account', 'Expense Account']:
					frappe.throw(_("Item Tax Row {0} must have account of type Tax or Income or Expense or Chargeable").format(d.idx))
				else:
					if d.tax_type in check_list:
						frappe.throw(_("{0} entered twice in Item Tax").format(d.tax_type))
					else:
						check_list.append(d.tax_type)

	def validate_barcode(self):
		if self.barcode:
			duplicate = frappe.db.sql("""select name from tabItem where barcode = %s
				and name != %s""", (self.barcode, self.name))
			if duplicate:
				frappe.throw(_("Barcode {0} already used in Item {1}").format(self.barcode, duplicate[0][0]))

	def cant_change(self):
		if not self.get("__islocal"):
			to_check = ("has_serial_no", "is_stock_item",
				"valuation_method", "has_batch_no", "is_fixed_asset")

			vals = frappe.db.get_value("Item", self.name, to_check, as_dict=True)
			if not vals.get('valuation_method') and self.get('valuation_method'):
				vals['valuation_method'] = frappe.db.get_single_value("Stock Settings", "valuation_method") or "FIFO"

			if vals:
				for key in to_check:
					if cstr(self.get(key)) != cstr(vals.get(key)):
						if not self.check_if_linked_document_exists(key):
							break # no linked document, allowed
						else:
							frappe.throw(_("As there are existing transactions against item {0}, you can not change the value of {1}").format(self.name, frappe.bold(self.meta.get_label(key))))

			if vals and not self.is_fixed_asset and self.is_fixed_asset != vals.is_fixed_asset:
				asset = frappe.db.get_all("Asset", filters={"item_code": self.name, "docstatus": 1}, limit=1)
				if asset:
					frappe.throw(_('"Is Fixed Asset" cannot be unchecked, as Asset record exists against the item'))

	def check_if_linked_document_exists(self, key):
		linked_doctypes = ["Delivery Note Item", "Sales Invoice Item", "Purchase Receipt Item",
			"Purchase Invoice Item", "Stock Entry Detail", "Stock Reconciliation Item"]

		# For "Is Stock Item", following doctypes is important
		# because reserved_qty, ordered_qty and requested_qty updated from these doctypes
		if key == "is_stock_item":
			linked_doctypes += ["Sales Order Item", "Purchase Order Item", "Material Request Item"]

		for doctype in linked_doctypes:
			if frappe.db.get_value(doctype, filters={"item_code": self.name, "docstatus": 1}) or \
				frappe.db.get_value("Production Order",
					filters={"production_item": self.name, "docstatus": 1}):
				return True

		for d in self.get("reorder_levels"):
			if d.warehouse_reorder_level and not d.warehouse_reorder_qty:
				frappe.throw(_("Row #{0}: Please set reorder quantity").format(d.idx))

	def validate_warehouse_for_reorder(self):
		warehouse = []
		for i in self.get("reorder_levels"):
			if not i.warehouse_group:
				i.warehouse_group = i.warehouse
			if i.get("warehouse") and i.get("warehouse") not in warehouse:
				warehouse += [i.get("warehouse")]
			else:
				frappe.throw(_("Row {0}: An Reorder entry already exists for this warehouse {1}")
					.format(i.idx, i.warehouse), DuplicateReorderRows)

	def check_if_sle_exists(self):
		sle = frappe.db.sql("""select name from `tabStock Ledger Entry`
			where item_code = %s""", self.name)
		return sle and 'exists' or 'not exists'

	def validate_name_with_item_group(self):
		# causes problem with tree build
		if frappe.db.exists("Item Group", self.name):
			frappe.throw(_("An Item Group exists with same name, please change the item name or rename the item group"))

	def update_item_price(self):
		frappe.db.sql("""update `tabItem Price` set item_name=%s,
			item_description=%s, modified=NOW() where item_code=%s""",
			(self.item_name, self.description, self.name))

	def on_trash(self):
		super(Item, self).on_trash()
		frappe.db.sql("""delete from tabBin where item_code=%s""", self.item_code)
		frappe.db.sql("delete from `tabItem Price` where item_code=%s", self.name)
		for variant_of in frappe.get_all("Item", filters={"variant_of": self.name}):
			frappe.delete_doc("Item", variant_of.name)

	def before_rename(self, old_name, new_name, merge=False):
		if self.item_name==old_name:
			frappe.db.set_value("Item", old_name, "item_name", new_name)

		if merge:
			# Validate properties before merging
			if not frappe.db.exists("Item", new_name):
				frappe.throw(_("Item {0} does not exist").format(new_name))

			field_list = ["stock_uom", "is_stock_item", "has_serial_no", "has_batch_no"]
			new_properties = [cstr(d) for d in frappe.db.get_value("Item", new_name, field_list)]
			if new_properties != [cstr(self.get(fld)) for fld in field_list]:
				frappe.throw(_("To merge, following properties must be same for both items")
					+ ": \n" + ", ".join([self.meta.get_label(fld) for fld in field_list]))

	def after_rename(self, old_name, new_name, merge):
		if self.route:
			invalidate_cache_for_item(self)
			clear_cache(self.route)

		frappe.db.set_value("Item", new_name, "item_code", new_name)

		if merge:
			self.set_last_purchase_rate(new_name)
			self.recalculate_bin_qty(new_name)

		for dt in ("Sales Taxes and Charges", "Purchase Taxes and Charges"):
			for d in frappe.db.sql("""select name, item_wise_tax_detail from `tab{0}`
					where ifnull(item_wise_tax_detail, '') != ''""".format(dt), as_dict=1):

				item_wise_tax_detail = json.loads(d.item_wise_tax_detail)
				if old_name in item_wise_tax_detail:
					item_wise_tax_detail[new_name] = item_wise_tax_detail[old_name]
					item_wise_tax_detail.pop(old_name)

					frappe.db.set_value(dt, d.name, "item_wise_tax_detail",
						json.dumps(item_wise_tax_detail), update_modified=False)

	def set_last_purchase_rate(self, new_name):
		last_purchase_rate = get_last_purchase_details(new_name).get("base_rate", 0)
		frappe.db.set_value("Item", new_name, "last_purchase_rate", last_purchase_rate)

	def recalculate_bin_qty(self, new_name):
		from erpnext.stock.stock_balance import repost_stock
		frappe.db.auto_commit_on_many_writes = 1
		existing_allow_negative_stock = frappe.db.get_value("Stock Settings", None, "allow_negative_stock")
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

		repost_stock_for_warehouses = frappe.db.sql_list("""select distinct warehouse
			from tabBin where item_code=%s""", new_name)

		# Delete all existing bins to avoid duplicate bins for the same item and warehouse
		frappe.db.sql("delete from `tabBin` where item_code=%s", new_name)

		for warehouse in repost_stock_for_warehouses:
			repost_stock(new_name, warehouse)

		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", existing_allow_negative_stock)
		frappe.db.auto_commit_on_many_writes = 0

	def copy_specification_from_item_group(self):
		self.set("website_specifications", [])
		if self.item_group:
			for label, desc in frappe.db.get_values("Item Website Specification",
				{"parent": self.item_group}, ["label", "description"]):
					row = self.append("website_specifications")
					row.label = label
					row.description = desc

	def update_item_desc(self):
		if frappe.db.get_value('BOM',self.name, 'description') != self.description:
			frappe.db.sql("""update `tabBOM` set description = %s where item = %s and docstatus < 2""",(self.description, self.name))
			frappe.db.sql("""update `tabBOM Item` set description = %s where
				item_code = %s and docstatus < 2""",(self.description, self.name))
			frappe.db.sql("""update `tabBOM Explosion Item` set description = %s where
				item_code = %s and docstatus < 2""",(self.description, self.name))

	def update_template_item(self):
		"""Set Show in Website for Template Item if True for its Variant"""
		if self.variant_of and self.show_in_website:
			self.show_variant_in_website = 1
			self.show_in_website = 0

		if self.show_variant_in_website:
			# show template
			template_item = frappe.get_doc("Item", self.variant_of)

			if not template_item.show_in_website:
				template_item.show_in_website = 1
				template_item.flags.dont_update_variants = True
				template_item.flags.ignore_permissions = True
				template_item.save()

	def update_variants(self):
			if self.flags.dont_update_variants:
				return
			if self.has_variants:
				updated = []
				variants = frappe.db.get_all("Item", fields=["item_code"], filters={"variant_of": self.name })
				for d in variants:
					variant = frappe.get_doc("Item", d)
					copy_attributes_to_variant(self, variant)
					variant.save()
					updated.append(d.item_code)
				if updated:
					frappe.msgprint(_("Item Variants {0} updated").format(", ".join(updated)))

	def validate_has_variants(self):
		if not self.has_variants and frappe.db.get_value("Item", self.name, "has_variants"):
			if frappe.db.exists("Item", {"variant_of": self.name}):
				frappe.throw(_("Item has variants."))

	def validate_uom(self):
		if not self.get("__islocal"):
			check_stock_uom_with_bin(self.name, self.stock_uom)
		if self.has_variants:
			for d in frappe.db.get_all("Item", filters= {"variant_of": self.name}):
				check_stock_uom_with_bin(d.name, self.stock_uom)
		if self.variant_of:
			template_uom = frappe.db.get_value("Item", self.variant_of, "stock_uom")
			if template_uom != self.stock_uom:
				frappe.throw(_("Default Unit of Measure for Variant '{0}' must be same as in Template '{1}'")
					.format(self.stock_uom, template_uom))

	def validate_attributes(self):
		if (self.has_variants or self.variant_of) and self.variant_based_on=='Item Attribute':
			attributes = []
			if not self.attributes:
				frappe.throw(_("Attribute table is mandatory"))
			for d in self.attributes:
				if d.attribute in attributes:
					frappe.throw(_("Attribute {0} selected multiple times in Attributes Table".format(d.attribute)))
				else:
					attributes.append(d.attribute)

	def validate_variant_attributes(self):
		if self.variant_of and self.variant_based_on=='Item Attribute':
			args = {}
			for d in self.attributes:
				if not d.attribute_value:
					frappe.throw(_("Please specify Attribute Value for attribute {0}").format(d.attribute))
				args[d.attribute] = d.attribute_value

			variant = get_variant(self.variant_of, args, self.name)
			if variant:
				frappe.throw(_("Item variant {0} exists with same attributes")
					.format(variant), ItemVariantExistsError)

			validate_item_variant_attributes(self, args)

def get_timeline_data(doctype, name):
	'''returns timeline data based on stock ledger entry'''
	out = {}
	items = dict(frappe.db.sql('''select posting_date, count(*)
		from `tabStock Ledger Entry` where item_code=%s
			and posting_date > date_sub(curdate(), interval 1 year)
			group by posting_date''', name))

	for date, count in items.iteritems():
		timestamp = get_timestamp(date)
		out.update({ timestamp: count })

	return out

def validate_end_of_life(item_code, end_of_life=None, disabled=None, verbose=1):
	if (not end_of_life) or (disabled is None):
		end_of_life, disabled = frappe.db.get_value("Item", item_code, ["end_of_life", "disabled"])

	if end_of_life and end_of_life!="0000-00-00" and getdate(end_of_life) <= now_datetime().date():
		msg = _("Item {0} has reached its end of life on {1}").format(item_code, formatdate(end_of_life))
		_msgprint(msg, verbose)

	if disabled:
		_msgprint(_("Item {0} is disabled").format(item_code), verbose)

def validate_is_stock_item(item_code, is_stock_item=None, verbose=1):
	if not is_stock_item:
		is_stock_item = frappe.db.get_value("Item", item_code, "is_stock_item")

	if is_stock_item != 1:
		msg = _("Item {0} is not a stock Item").format(item_code)

		_msgprint(msg, verbose)

def validate_cancelled_item(item_code, docstatus=None, verbose=1):
	if docstatus is None:
		docstatus = frappe.db.get_value("Item", item_code, "docstatus")

	if docstatus == 2:
		msg = _("Item {0} is cancelled").format(item_code)
		_msgprint(msg, verbose)

def _msgprint(msg, verbose):
	if verbose:
		msgprint(msg, raise_exception=True)
	else:
		raise frappe.ValidationError(msg)


def get_last_purchase_details(item_code, doc_name=None, conversion_rate=1.0):
	"""returns last purchase details in stock uom"""
	# get last purchase order item details
	last_purchase_order = frappe.db.sql("""\
		select po.name, po.transaction_date, po.conversion_rate,
			po_item.conversion_factor, po_item.base_price_list_rate,
			po_item.discount_percentage, po_item.base_rate
		from `tabPurchase Order` po, `tabPurchase Order Item` po_item
		where po.docstatus = 1 and po_item.item_code = %s and po.name != %s and
			po.name = po_item.parent
		order by po.transaction_date desc, po.name desc
		limit 1""", (item_code, cstr(doc_name)), as_dict=1)

	# get last purchase receipt item details
	last_purchase_receipt = frappe.db.sql("""\
		select pr.name, pr.posting_date, pr.posting_time, pr.conversion_rate,
			pr_item.conversion_factor, pr_item.base_price_list_rate, pr_item.discount_percentage,
			pr_item.base_rate
		from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
		where pr.docstatus = 1 and pr_item.item_code = %s and pr.name != %s and
			pr.name = pr_item.parent
		order by pr.posting_date desc, pr.posting_time desc, pr.name desc
		limit 1""", (item_code, cstr(doc_name)), as_dict=1)

	purchase_order_date = getdate(last_purchase_order and last_purchase_order[0].transaction_date \
		or "1900-01-01")
	purchase_receipt_date = getdate(last_purchase_receipt and \
		last_purchase_receipt[0].posting_date or "1900-01-01")

	if (purchase_order_date > purchase_receipt_date) or \
			(last_purchase_order and not last_purchase_receipt):
		# use purchase order
		last_purchase = last_purchase_order[0]
		purchase_date = purchase_order_date

	elif (purchase_receipt_date > purchase_order_date) or \
			(last_purchase_receipt and not last_purchase_order):
		# use purchase receipt
		last_purchase = last_purchase_receipt[0]
		purchase_date = purchase_receipt_date

	else:
		return frappe._dict()

	conversion_factor = flt(last_purchase.conversion_factor)
	out = frappe._dict({
		"base_price_list_rate": flt(last_purchase.base_price_list_rate) / conversion_factor,
		"base_rate": flt(last_purchase.base_rate) / conversion_factor,
		"discount_percentage": flt(last_purchase.discount_percentage),
		"purchase_date": purchase_date
	})

	conversion_rate = flt(conversion_rate) or 1.0
	out.update({
		"price_list_rate": out.base_price_list_rate / conversion_rate,
		"rate": out.base_rate / conversion_rate,
		"base_rate": out.base_rate
	})

	return out

def invalidate_cache_for_item(doc):
	invalidate_cache_for(doc, doc.item_group)

	website_item_groups = list(set((doc.get("old_website_item_groups") or [])
		+ [d.item_group for d in doc.get({"doctype":"Website Item Group"}) if d.item_group]))

	for item_group in website_item_groups:
		invalidate_cache_for(doc, item_group)

	if doc.get("old_item_group") and doc.get("old_item_group") != doc.item_group:
		invalidate_cache_for(doc, doc.old_item_group)

def check_stock_uom_with_bin(item, stock_uom):
	if stock_uom == frappe.db.get_value("Item", item, "stock_uom"):
		return

	matched=True
	ref_uom = frappe.db.get_value("Stock Ledger Entry",
		{"item_code": item}, "stock_uom")

	if ref_uom:
		if cstr(ref_uom) != cstr(stock_uom):
			matched = False
	else:
		bin_list = frappe.db.sql("select * from tabBin where item_code=%s", item, as_dict=1)
		for bin in bin_list:
			if (bin.reserved_qty > 0 or bin.ordered_qty > 0 or bin.indented_qty > 0 \
				or bin.planned_qty > 0) and cstr(bin.stock_uom) != cstr(stock_uom):
					matched = False
					break

		if matched and bin_list:
			frappe.db.sql("""update tabBin set stock_uom=%s where item_code=%s""", (stock_uom, item))

	if not matched:
		frappe.throw(_("Default Unit of Measure for Item {0} cannot be changed directly because you have already made some transaction(s) with another UOM. You will need to create a new Item to use a different Default UOM.").format(item))

