# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _
import operator
from erpnext_ebay.vlog import vwrite

class ReadyToShip(object):
    def __init__(self, filters=None):
        self.filters = frappe._dict(filters or {})
        self.selected_date_obj = self.datetime.strptime(self.datetime.today().strftime('%Y-%m-%d'), '%Y-%m-%d')
	self.selected_month = self.datetime.today().strftime('%B')
        # self.selected_date_obj = self.datetime.strptime("2018-04-28", '%Y-%m-%d')
        self.today = str(self.datetime.today())[:10]
        
    def run(self, args):
        vwrite("in vamc 1")
        data = self.get_data()
        max_len = 0
        for d in data:
            if d[3]:
                if len(d[3]) > max_len:
                    max_len = len(d[3])
                vwrite(max_len)
        
        columns = self.get_columns(max_len*5.66)
        return columns, data

    def get_columns(self,max_len):
        """return columns bab on filters"""
        columns = [
            _("Party") + ":Link/Customer:180", 
            _("Party Type") + ":Data:80",
            _("Party Owes Us") + ":Currency/currency:120",
            _("Payment Delay Comments") + ":Data:%s" % max_len,
            _("Reference") + ":Data:180"
        ]
        return columns

    from datetime import timedelta,datetime
    
    def get_data(self):
        data = []
        acc_recv_sql = """ 
        SELECT b.party as party, b.party_type as party_type, (b.debit-b.credit) as party_owes_us, c.payment_delay_comment as payment_delay_comment, b.voucher_no as reference from (select party as party,party_type as party_type,sum(credit) as credit,sum(debit) as debit,voucher_no as voucher_no from `tabGL Entry` group by party,party_type) as b left join `tabCustomer` c on b.party=c.name where b.credit <> b.debit and b.party_type = 'Customer' and b.party NOT IN (select customer from `tabSales Invoice` si where si.status <>'Cancelled' and (si.posting_date) > (NOW() - INTERVAL 30 DAY ) group by customer ) order BY (b.debit-b.credit) desc
        """
        vwrite(acc_recv_sql)
        for acc_recv in frappe.db.sql(acc_recv_sql,as_dict=1):
            data.append([acc_recv.get("party"),acc_recv.get("party_type"),acc_recv.get("party_owes_us"),acc_recv.get("payment_delay_comment"),acc_recv.get("reference")])
        return data
    
def execute(filters=None):
    args = {

    }
    return ReadyToShip(filters).run(args)
    # data = []

    # rows = get_dataget_data()
    # for row in rows:
    #   data.append(row)
    # return columns,data





