# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _
import operator
from erpnext.vlog import vwrite

class SalesSummary(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		if "selected_date" in self.filters:
			self.selected_date = self.filters.get("selected_date")
			self.selected_date_obj = self.datetime.strptime(self.selected_date, '%Y-%m-%d')
		else:
			self.selected_date = self.datetime.today().strftime('%Y-%m-%d')
			self.selected_date_obj = self.datetime.strptime(self.datetime.today().strftime('%Y-%m-%d'), '%Y-%m-%d')
	def run(self, args):
		columns = self.get_columns()
		data = self.get_data()
		return columns, data

	def get_columns(self):
		"""return columns based on filters"""
		columns = [
			_("Item Group") + ":Data:90", 
			_("Channel") + ":Data:80", 
			_("Assisted Leads(yesterday)") + ":Int:100",
			_("Qty(yesterday)") + ":Int:100",
			_("Amount(yesterday)") + ":Currency/currency:100", 
			_("Assisted Leads(this week)") + ":Int:100",
			_("Qty(this week)") + ":Int:100",
			_("Amount(this week)") + ":Currency/currency:100", 
			_("Assisted Leads(this month)") + ":Int:100",
			_("Qty(this month)") + ":Int:100",
			_("Amount(this month)") + ":Currency/currency:100",
		]
		return columns

	def prepare_conditions(self):
		conditions = [""]
		if "sales_type" in self.filters:
			if self.filters.get("sales_type")=="GROSS":
				conditions.append(""" si.is_return = 0""")
			elif self.filters.get("sales_type")=="CREDIT NOTES":
				conditions.append(""" si.is_return = 1""")
		return " and ".join(conditions)
	from datetime import timedelta,datetime
	def week_range(self,date):
		"""Find the first/last day of the week for the given day.
		Assuming weeks start on Sunday and end on Saturday.
		Returns a tuple of ``(start_date, end_date)``.
		"""
		# isocalendar calculates the year, week of the year, and day of the week.
		# dow is Mon = 1, Sat = 6, Sun = 7
		year, week, dow = date.isocalendar()
		# Find the first day of the week.
		if dow == 7:
			# Since we want to start with Sunday, let's test for that condition.
			start_date = date
		else:
			# Otherwise, subtract `dow` number days to get the first day
			start_date = date - self.timedelta(dow)
		# Now, add 6 for the last day of the week (i.e., count up to Saturday)
		end_date = start_date + self.timedelta(6)
		return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
	def get_data(self):
		today_data = []
		week_data = []
		month_data = []
		item_groups_array = []
		conditions = self.prepare_conditions()
		
		today_data_res = frappe.db.sql("""
		select 
		sum(sii.qty),sum(sii.amount), sii.item_group, si.sales_channel
		from `tabSales Invoice` as si inner join
		`tabSales Invoice Item` as sii on  sii.parent=si.name 
		where (DAY(si.posting_date) = DAY('{0}') and MONTH(si.posting_date) = MONTH('{1}') and YEAR(si.posting_date) = YEAR('{2}')) and si.status not in ('Cancelled','Draft') and si.docstatus=1 and si.company='Usedyetnew' 
		{3}
		group by sii.item_group,si.sales_channel
		""".format(self.selected_date,self.selected_date,self.selected_date,conditions))
		for qty,amount,item_group,sales_channel in today_data_res:
			data_row = []
			item_group = "%s (%s)" % (str(item_group),str(sales_channel))
			data_row = data_row + [item_group,qty,amount]
			today_data.append(data_row)
			item_groups_array.append(item_group)
		if "selected_date" in self.filters:
			selected_year,selected_month,selected_day = self.filters.get("selected_date").split('-')
			weekstartdate = self.week_range(self.selected_date_obj)[0]
			weekenddate = self.week_range(self.selected_date_obj)[1]
		else:
			weekstartdate = self.week_range(self.datetime.today())[0]
			weekenddate = self.week_range(self.datetime.today())[1]
		week_data_res = frappe.db.sql("""
		select 
		sum(sii.qty),sum(sii.amount), sii.item_group, si.sales_channel
		from `tabSales Invoice` as si inner join
		`tabSales Invoice Item` as sii on sii.parent=si.name
		where si.posting_date >= '{0}' and si.posting_date <= '{1}' and si.status not in ('Cancelled','Draft') and si.docstatus=1 and si.company='Usedyetnew' 
		{2}
		group by sii.item_group,si.sales_channel
		""".format(weekstartdate,weekenddate,conditions))
		for qty,amount,item_group,sales_channel in week_data_res:
			data_row = []
			item_group = "%s (%s)" % (str(item_group),str(sales_channel))
			data_row = data_row + [item_group,qty,amount]
			week_data.append(data_row)
			item_groups_array.append(item_group)
		
		month_data_res = frappe.db.sql("""
		select 
		sum(sii.qty),sum(sii.amount), sii.item_group, si.sales_channel
		from `tabSales Invoice` as si inner join
		`tabSales Invoice Item` as sii on sii.parent=si.name
		where (MONTH(si.posting_date) = MONTH('{0}') and YEAR(si.posting_date) = YEAR('{1}')) and si.status not in ('Cancelled','Draft') and si.docstatus=1 and si.company='Usedyetnew' and si.posting_date <= '{2}'
		{3}
		group by sii.item_group,si.sales_channel
		""".format(self.selected_date,self.selected_date,self.selected_date,conditions))
		for qty,amount,item_group,sales_channel in month_data_res:
			data_row = []
			item_group = "%s (%s)" % (str(item_group),str(sales_channel))
			data_row = data_row + [item_group,qty,amount]
			month_data.append(data_row)
			item_groups_array.append(item_group)

		data = []
		total_t_qty = 0
		total_w_qty = 0
		total_m_qty = 0
		total_t_amt = 0
		total_w_amt = 0
		total_m_amt = 0
		distinct_item_groups = sorted(set(item_groups_array))
		i=0
		for item_group in distinct_item_groups:
			t_d_temp = []
			for t_d in today_data:
				if item_group in t_d:
					t_d_temp = t_d_temp+[t_d[1]]+[t_d[2]]
					total_t_qty = total_t_qty+t_d[1]
					total_t_amt = total_t_amt+t_d[2]
			if not len(t_d_temp):
				t_d_temp = t_d_temp+[0]+[0]
			w_d_temp = []
			for w_d in week_data:
				if item_group in w_d:
					w_d_temp = w_d_temp+[w_d[1]]+[w_d[2]]
					total_w_qty = total_w_qty+w_d[1]
					total_w_amt = total_w_amt+w_d[2]
			if not len(w_d_temp):
				w_d_temp = w_d_temp+[0]+[0]
			m_d_temp = []
			for m_d in month_data:
				if item_group in m_d:
					m_d_temp = m_d_temp+[m_d[1]]+[m_d[2]]
					total_m_qty = total_m_qty+m_d[1]
					total_m_amt = total_m_amt+m_d[2]
			if not len(m_d_temp):
				m_d_temp = m_d_temp+[0]+[0]
			sales_channel = item_group[item_group.find("(")+1:item_group.find(")")]
			item_group = item_group[0:item_group.find("(")]

			assisted_daily_res = frappe.db.sql("""
			select distinct si.name,a.phone,a.email_id,si.customer_address,sii.item_group from `tabSales Invoice` si
			inner join `tabSales Invoice Item` sii on sii.parent=si.name
			inner join `tabAddress` a on a.name=si.customer_address
			inner join `tabLead` l on ((REPLACE(l.mobile_no," ","")=REPLACE(a.phone," ","")) or (REPLACE(l.phone," ","")=REPLACE(a.phone," ","")) or (REPLACE(l.email_id," ","")=REPLACE(a.email_id," ","")))
			where sii.item_group = '{0}' and si.sales_channel='{1}' and (DAY(si.posting_date) = DAY(NOW()) and MONTH(si.posting_date) = MONTH(NOW()) and YEAR(si.posting_date) = YEAR(NOW())) and si.status not in ('Cancelled','Draft') and si.docstatus=1 and si.company='Usedyetnew' and (l.mobile_no is not NULL or l.phone is not NULL or l.email_id is not NULL) {2}
			""".format(item_group,sales_channel,conditions))

			assisted_weekly_res = frappe.db.sql("""
			select distinct si.name,a.phone,a.email_id,si.customer_address,sii.item_group from `tabSales Invoice` si
			inner join `tabSales Invoice Item` sii on sii.parent=si.name
			inner join `tabAddress` a on a.name=si.customer_address
			inner join `tabLead` l on ((REPLACE(l.mobile_no," ","")=REPLACE(a.phone," ","")) or (REPLACE(l.phone," ","")=REPLACE(a.phone," ","")) or (REPLACE(l.email_id," ","")=REPLACE(a.email_id," ","")))
			where sii.item_group = '{0}' and si.sales_channel='{1}' and si.posting_date >= '{2}' and si.status not in ('Cancelled','Draft') and si.docstatus=1 and si.company='Usedyetnew' and (l.mobile_no is not NULL or l.phone is not NULL or l.email_id is not NULL) {3}
			""".format(item_group,sales_channel,weekstartdate,conditions))

			assisted_monthly_res = frappe.db.sql("""
			select distinct si.name,l.mobile_no,l.phone,l.email_id from `tabSales Invoice` si
			inner join `tabSales Invoice Item` sii on sii.parent=si.name
			inner join `tabAddress` a on a.name=si.customer_address
			inner join `tabLead` l on ((REPLACE(l.mobile_no," ","")=REPLACE(a.phone," ","")) or (REPLACE(l.phone," ","")=REPLACE(a.phone," ","")) or (REPLACE(l.email_id," ","")=REPLACE(a.email_id," ","")))
			where sii.item_group = '{0}' and si.sales_channel='{1}' and (MONTH(si.posting_date) = MONTH(NOW()) and YEAR(si.posting_date) = YEAR(NOW())) and si.status not in ('Cancelled','Draft') and si.docstatus=1 and si.company='Usedyetnew'
			 and ((l.mobile_no is not NULL and l.mobile_no!='') or (l.phone is not NULL and l.phone!='') or (l.email_id is not NULL and l.email_id!='') ) 
			 {2}
			""".format(item_group,sales_channel,conditions))
			
			data.append([item_group]+[sales_channel]+[len(assisted_daily_res)]+t_d_temp+[len(assisted_weekly_res)]+w_d_temp+[len(assisted_monthly_res)]+m_d_temp)
		# data.append(["<b>Total</b>",total_t_qty,total_t_amt,total_w_qty,total_w_amt,total_m_qty,total_m_amt])
		return data

def execute(filters=None):
	args = {

	}
	return SalesSummary(filters).run(args)
	# data = []

	# rows = get_dataget_data()
	# for row in rows:
	# 	data.append(row)
	# return columns,data

