# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.financial_statements import (get_period_list, get_columns, get_data)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import get_net_profit_loss
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import flt


def execute(filters=None):
    period_list = get_period_list(filters.from_fiscal_year, filters.to_fiscal_year,
                                  filters.periodicity, filters.accumulated_values, filters.company)

    operation_accounts = {
        "section_name": "Operations",
        "section_footer": _("Net Cash from Operations"),
        "section_header": _("Cash Flow from Operations"),
        "account_types": [
            {"account_type": "Depreciation", "label": _("Depreciation")},
            {"account_type": "Receivable", "label": _("Net Change in Accounts Receivable")},
            {"account_type": "Payable", "label": _("Net Change in Accounts Payable")},
            {"account_type": "Stock", "label": _("Net Change in Inventory")}
        ]
    }

    investing_accounts = {
        "section_name": "Investing",
        "section_footer": _("Net Cash from Investing"),
        "section_header": _("Cash Flow from Investing"),
        "account_types": [
            {"account_type": "Fixed Asset", "label": _("Net Change in Fixed Asset")}
        ]
    }

    financing_accounts = {
        "section_name": "Financing",
        "section_footer": _("Net Cash from Financing"),
        "section_header": _("Cash Flow from Financing"),
        "account_types": [
            {"account_type": "Equity", "label": _("Net Change in Equity")}
        ]
    }

    # combine all cash flow accounts for iteration
    cash_flow_accounts = []
    cash_flow_accounts.append(operation_accounts)
    cash_flow_accounts.append(investing_accounts)
    cash_flow_accounts.append(financing_accounts)

    # compute net profit / loss
    income = get_data(filters.company, "Income", "Credit", period_list,
                      accumulated_values=filters.accumulated_values, ignore_closing_entries=True,
                      ignore_accumulated_values_for_fy=True)
    expense = get_data(filters.company, "Expense", "Debit", period_list,
                       accumulated_values=filters.accumulated_values, ignore_closing_entries=True,
                       ignore_accumulated_values_for_fy=True)

    net_profit_loss = get_net_profit_loss(income, expense, period_list, filters.company)

    data = []
    company_currency = frappe.db.get_value("Company", filters.company, "default_currency")

    for cash_flow_account in cash_flow_accounts:
        section_data = []
        data.append({
            "account_name": cash_flow_account['section_header'],
            "parent_account": None,
            "indent": 0.0,
            "account": cash_flow_account['section_header']
        })

        if len(data) == 1:
            # add first net income in operations section
            if net_profit_loss:
                net_profit_loss.update({
                    "indent": 1,
                    "parent_account": operation_accounts['section_header']
                })
                data.append(net_profit_loss)
                section_data.append(net_profit_loss)

        for account in cash_flow_account['account_types']:
            account_data = get_account_type_based_data(filters.company,
                                                       account['account_type'], period_list, filters.accumulated_values,
                                                       filters)
            account_data.update({
                "account_name": account['label'],
                "account": account['label'],
                "indent": 1,
                "parent_account": cash_flow_account['section_header'],
                "currency": company_currency
            })
            data.append(account_data)
            section_data.append(account_data)

        add_total_row_account(data, section_data, cash_flow_account['section_footer'],
                              period_list, company_currency)

    add_total_row_account(data, data, _("Net Change in Cash"), period_list, company_currency)
    columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

    return columns, data


def get_account_type_based_data(company, account_type, period_list, accumulated_values, filters):
    data = {}
    total = 0
    for period in period_list:
        unapproved_transactions = ""
        if filters != None:
            if filters.get("transaction_type"):
                unapproved_transactions = " UNION select sum(credit) - sum(debit) from `tabGL Entry 2` where company=%(company)s and posting_date >= %(from_date)s and posting_date <= %(to_date)s and voucher_type != 'Period Closing Voucher' and account in ( SELECT name FROM tabAccount WHERE account_type = %(account_type)s )"
        start_date = get_start_date(period, accumulated_values, company)
        gl_sum = frappe.db.sql_list("""
			select sum(credit) - sum(debit)
			from `tabGL Entry`
			where company=%(company)s and posting_date >=%(from_date)s and posting_date <= %(to_date)s 
				and voucher_type != 'Period Closing Voucher'
				and account in ( SELECT name FROM tabAccount WHERE account_type = %(account_type)s )
				{unapproved_transactions}""".format(unapproved_transactions=unapproved_transactions),
                                    {
                                        "company": company,
                                        "from_date": start_date if accumulated_values else period['from_date'],
                                        "to_date": period['to_date'],
                                        "account_type": account_type
                                    }
                                    )

        if gl_sum and gl_sum[0]:
            amount = gl_sum[0]
            if account_type == "Depreciation":
                amount *= -1
        else:
            amount = 0

        total += amount
        data.setdefault(period["key"], amount)

    data["total"] = total
    return data


def get_start_date(period, accumulated_values, company):
    start_date = period["year_start_date"]
    if accumulated_values:
        start_date = get_fiscal_year(period.to_date, company=company)[1]

    return start_date


def add_total_row_account(out, data, label, period_list, currency):
    total_row = {
        "account_name": "'" + _("{0}").format(label) + "'",
        "account": "'" + _("{0}").format(label) + "'",
        "currency": currency
    }
    for row in data:
        if row.get("parent_account"):
            for period in period_list:
                total_row.setdefault(period.key, 0.0)
                total_row[period.key] += row.get(period.key, 0.0)

            total_row.setdefault("total", 0.0)
            total_row["total"] += row["total"]

    out.append(total_row)
    out.append({})
