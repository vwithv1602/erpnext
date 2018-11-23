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
        self.weekstartdate = self.week_range(self.selected_date_obj)[0]
        self.weekenddate = self.week_range(self.selected_date_obj)[1]
        
    def run(self, args):
        data = self.get_data()
        columns = self.get_columns()
        return columns, data
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
		end_date = start_date + self.timedelta(7)
		return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    def get_columns(self):
        """return columns bab on filters"""
        columns = [
            _("Employee") + ":Data:250",
            _("Daily") + ":Data:70",
            _("Weekly") + ":Data:70",
            _(self.selected_month) + ":Data:70"
        ]
        return columns

    from datetime import timedelta,datetime
    # def prepare_conditions(self):
        # conditions = [""]
        # group_by = ""
        # if "selected_date" in self.filters:
        #     conditions.append(""" se.posting_date = '%s'"""%self.filters.get("selected_date"))
        # else:
        #     conditions.append(""" se.posting_date = '%s'""" % self.today)
        # if "item_group" in self.filters:
        #     conditions.append(""" i.item_group= '%s'""" % self.filters.get("item_group"))
        # if "group_by" in self.filters:
        #     group_by = " group by i.variant_of "
        # conditions_string = " and ".join(conditions)
        # return "%s %s" %(conditions_string,group_by)
    def get_custom_data(self,period,warehouse):
        cur_date = '2018-05-04'
        week_start_date = '2018-05-05'
        week_end_date = '2018-05-25'
        custom_data = []
        if period=='yesterday':
            condition = """ a.date >= (NOW()- INTERVAL 1 DAY) """
        elif period=='week':
            condition = """ a.date >= ('%s') and a.date < ('%s')""" %(self.weekstartdate,self.weekenddate)
        elif period=='month':
            condition = """ MONTH(a.date) = MONTH('{0}') and YEAR(a.date) = YEAR('{0}') """.format(self.today)
        if warehouse=='Incoming Team':
            warehouse_condition = """ sed.s_warehouse = 'incoming & Dis-assebly - Uyn'
        and (sed.t_warehouse Like 'Tech Team - Uyn' or sed.t_warehouse = 'Final QC & Packing - Uyn' or sed.t_warehouse Like 'Ready To Ship - Uyn' or sed.t_warehouse Like 'G3 Ready To Ship - Uyn' or sed.t_warehouse Like 'Ready To Ship Grade B- Uyn') """
            inspection_type = "Incoming"
        elif warehouse=='Tech Team':
            warehouse_condition = """ sed.s_warehouse = 'Tech Team - Uyn'
        and (sed.t_warehouse = 'Final QC & Packing - Uyn' or sed.t_warehouse Like 'Ready To Ship - Uyn' or sed.t_warehouse Like 'G3 Ready To Ship - Uyn' or sed.t_warehouse Like 'Ready To Ship Grade B- Uyn') """
            inspection_type = "In Process"
        elif warehouse=='Chip Team':
            warehouse_condition = """ sed.s_warehouse = 'Chip Tech - Uyn'
        and (sed.t_warehouse = 'Tech Team - Uyn' or sed.t_warehouse = 'Final QC & Packing - Uyn' or sed.t_warehouse Like 'Ready To Ship - Uyn' or sed.t_warehouse Like 'G3 Ready To Ship - Uyn' or sed.t_warehouse Like 'Ready To Ship Grade B- Uyn') """
            inspection_type = "In Process"
        # elif warehouse=='Final QC Team':
        #     warehouse_condition = """ sed.s_warehouse = 'Final QC & Packing - Uyn' """
        #     inspection_type = "Final QC"
        if warehouse != 'Final QC Team':    
            productivity_daily_sql = """ 
            select a.employee, count(a.serial_no) as count
            from
            (
            select qi.inspected_by as employee ,sed.serial_no as serial_no ,min(se.posting_date) as date
            from `tabStock Entry` se 
            inner join `tabStock Entry Detail` sed on sed.parent=se.name 
            inner join `tabQuality Inspection` qi on qi.item_serial_no=sed.serial_no 
            and se.docstatus='1'
            and qi.docstatus = '1'
            and se.posting_date
            and se.purpose = 'Material Transfer'
            and qi.inspection_type = '{2}'
            and {1}
            group by qi.inspected_by,sed.serial_no
            )as a
            where {0}
            group by a.employee;
            """.format(condition,warehouse_condition,inspection_type)
        else:
            if period=='yesterday':
                date_condition = """ report_date = (CURDATE()- INTERVAL 1 DAY) """
            elif period=='week':
                date_condition = """ report_date >= ('%s') and report_date < ('%s')""" %(self.weekstartdate,self.weekenddate)
            elif period=='month':
                date_condition = """ MONTH(report_date) = MONTH('{0}') and YEAR(report_date) = YEAR('{0}') """.format(self.today)
            productivity_daily_sql = """ select inspected_by as employee,count(*) as count from `tabQuality Inspection` where inspection_type='Final QC' and {0} and docstatus=1 group by inspected_by """.format(date_condition)
        print productivity_daily_sql
        for prod in frappe.db.sql(productivity_daily_sql,as_dict=1):
            custom_data.append([prod.get("employee"),prod.get("count")])
        return custom_data
    def get_data(self):
        data = []
        warehouses = ['Incoming Team','Tech Team','Chip Team','Final QC Team']
        for warehouse in warehouses:
            data.append([warehouse,"",""])
            today_data = self.get_custom_data('yesterday',warehouse)
            week_data = self.get_custom_data('week',warehouse)
            month_data = self.get_custom_data('month',warehouse)
            emps = []
            for emp in today_data:
                if emp[0] not in emps:
                    emps.append(emp[0])
            for emp in week_data:
                if emp[0] not in emps: 
                    emps.append(emp[0])
            for emp in month_data:
                if emp[0] not in emps: 
                    emps.append(emp[0])
            pre_data = []
            for employee in emps:
                emp_found = 0
                for emp in today_data:
                    emp_found = 0
                    count_str = ""
                    if emp[0] == employee:
                        emp_found = 1
                        count_str = "%s" %(emp[1])
                        break
                if not emp_found:
                    count_str = "0"
                for emp in week_data:
                    emp_found = 0
                    if emp[0] == employee:
                        emp_found = 1
                        count_str = "%s,%s" %(count_str,emp[1])
                        break
                if not emp_found:
                    count_str = "%s,0" %(count_str)
                for emp in month_data:
                    emp_found = 0
                    if emp[0] == employee:
                        emp_found = 1
                        count_str = "%s,%s" %(count_str,emp[1])
                        break
                if not emp_found:
                    count_str = "%s,0" %(count_str)
                count_str = "%s,%s" %(employee,count_str)
                pre_data.append(count_str.split(','))
            
            print "===================="
            # print "weekstart: %s, weekend: %s" %(self.weekstartdate,self.weekenddate)
            # print pre_data
            data = data + pre_data
        return data
@frappe.whitelist()
def execute(filters=None):
    args = {

    }
    return ReadyToShip(filters).run(args)
    # data = []

    # rows = get_dataget_data()
    # for row in rows:
    #   data.append(row)
    # return columns,data






