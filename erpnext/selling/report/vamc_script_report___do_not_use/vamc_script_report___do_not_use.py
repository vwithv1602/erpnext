# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _
import operator
from erpnext_ebay.vlog import vwrite

class OperationsProductivity(object):
    def __init__(self, filters=None):
        self.filters = frappe._dict(filters or {})
        self.selected_date_obj = self.datetime.strptime(self.datetime.today().strftime('%Y-%m-%d'), '%Y-%m-%d')
        # >> change date here for older dates
        # self.selected_date_obj = self.datetime.strptime('2018-11-18', '%Y-%m-%d')
		# << change date here for older dates
        self.selected_month = self.selected_date_obj.strftime('%B')
        self.today = str(self.selected_date_obj)[:10]
        from datetime import timedelta,datetime
        self.yesterday = self.selected_date_obj - self.timedelta(1)
        self.yesterday_str = str(self.yesterday)[:10]
        self.weekstartdate = self.week_range(self.selected_date_obj)[0]
        self.weekenddate = self.week_range(self.selected_date_obj)[1]
        print self.today
        print self.yesterday_str
        print self.weekstartdate
        print self.weekenddate
        
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
		date = date - self.timedelta(1)
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
            _("Yesterday") + ":Data:70",
            _("This Week") + ":Data:70",
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
        #cur_date = '2018-05-04'
        #week_start_date = '2018-05-05'
        #week_end_date = '2018-05-25'
        custom_data = []
        if period=='yesterday':
            condition = """ a.date = ('{0}') """.format(self.yesterday_str)
        elif period=='week':
            condition = """ a.date >= ('{0}') and a.date <= ('{1}') and MONTH(a.date)=MONTH('{2}') and YEAR(a.date)=YEAR('{2}') """.format(self.weekstartdate,self.weekenddate,self.today)
        elif period=='month':
            condition = """ MONTH(a.date) = MONTH('{0}') and YEAR(a.date) = YEAR('{0}') """.format(self.today)
        if warehouse=='Incoming Team':
            warehouse_condition = """ sed.s_warehouse = 'incoming & Dis-assebly - Uyn'
        and (sed.t_warehouse Like 'Tech Team - Uyn' or sed.t_warehouse = 'Final QC & Packing - Uyn' or sed.t_warehouse Like 'Ready To Ship - Uyn' or sed.t_warehouse Like 'G3 Ready To Ship - Uyn' or sed.t_warehouse Like 'Ready To Ship Grade B- Uyn') """
            inspection_type = "Incoming"
        elif warehouse=='Tech Team':
            warehouse_condition = """ sed.s_warehouse = 'Tech Team - Uyn'
        and (sed.t_warehouse = 'Final QC & Packing - Uyn' or sed.t_warehouse Like 'Ready To Ship - Uyn' or sed.t_warehouse Like 'G3 Ready To Ship - Uyn' or sed.t_warehouse Like 'Ready To Ship Grade B- Uyn') and qi.inspected_by not in ('ravindrakathare@gmail.com') """
            inspection_type = "In Process"
        elif warehouse=='Chip Team':
            warehouse_condition = """ sed.s_warehouse = 'Chip Tech - Uyn'
        and (sed.t_warehouse = 'Tech Team - Uyn' or sed.t_warehouse = 'Final QC & Packing - Uyn' or sed.t_warehouse Like 'Ready To Ship - Uyn' or sed.t_warehouse Like 'G3 Ready To Ship - Uyn' or sed.t_warehouse Like 'Ready To Ship Grade B- Uyn') """
            inspection_type = "Chip Level In Process"
        elif warehouse=='Final QC Team':
            warehouse_condition = """ sed.s_warehouse = 'Final QC & Packing - Uyn' and qi.inspected_by in ('ayyanamanidiot@gmail.com','mdayyan007f@gmail.com','mohd.zaheduyn@gmail.com','sagarsahusagarsahu96@gmail.com') """
            inspection_type = "Final QC"
        # elif warehouse=='Final QC Team':
        #     warehouse_condition = """ sed.s_warehouse = 'Final QC & Packing - Uyn' """
        #     inspection_type = "Final QC"
        if warehouse!='Incoming Team' and warehouse!='Final QC Team':    
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
        elif warehouse=='Incoming Team':
            if period=='yesterday':
                qi_condition = """ report_date = ('{0}') and inspection_type='Incoming' """.format(self.yesterday_str)
                asis_condition = """ se.posting_date = ('{0}') """.format(self.yesterday_str)
            elif period=='week':
                qi_condition = """ report_date >= ('{0}') and report_date <= ('{1}') and inspection_type='Incoming' and MONTH(report_date)=MONTH('{2}') and YEAR(report_date)=YEAR('{2}') """.format(self.weekstartdate,self.weekenddate,self.today)
                asis_condition = """ se.posting_date >= ('{0}') and se.posting_date <= ('{1}') and MONTH(se.posting_date)=MONTH('{2}') and YEAR(se.posting_date)=YEAR('{2}') """.format(self.weekstartdate,self.weekenddate,self.today)
            elif period=='month':
                qi_condition = """ MONTH(report_date) = MONTH('{0}') and YEAR(report_date) = YEAR('{0}')  and inspection_type='Incoming'""".format(self.today)
                asis_condition = """ MONTH(se.posting_date) = MONTH('{0}') and YEAR(se.posting_date) = YEAR('{0}') """.format(self.today)
            productivity_daily_sql = """
            select inspected_by as employee,count(name) as count from `tabQuality Inspection` where {0} and inspected_by in ('vijaybhaskarkata@gmail.com','girimyki@gmail.com','sknadim690@gmail.com','ravindrakathare@gmail.com') group by inspected_by
            union
            select se.owner as employee,count(se.name) as count from `tabStock Entry` se
            left join `tabStock Entry Detail` sed on sed.parent=se.name
            left join `tabSerial No` sn on sn.name=sed.barcode
	    inner join `tabItem` i on i.item_code=sn.item_code
            where 
            se.purpose='Repack'
 	    and i.item_group='Laptop MotherBoard'
            and sed.s_warehouse='incoming & Dis-assebly - Uyn'
            and se.docstatus=1
            and {1}
	    and se.owner in ('vijaybhaskarkata@gmail.com','girimyki@gmail.com','sknadim690@gmail.com','ravindrakathare@gmail.com')
            group by se.owner
            """.format(qi_condition,asis_condition)
        else:
            if period=='yesterday':
                date_condition = """ report_date = ('{0}') """.format(self.yesterday_str)
            elif period=='week':
                date_condition = """ report_date >= ('{0}') and report_date <= ('{1}') and MONTH(report_date)=MONTH('{2}') and YEAR(report_date)=YEAR('{2}') """.format(self.weekstartdate,self.weekenddate,self.today)
            elif period=='month':
                date_condition = """ MONTH(report_date) = MONTH('{0}') and YEAR(report_date) = YEAR('{0}') """.format(self.today)
            #productivity_daily_sql = """ select inspected_by as employee,count(*) as count from `tabQuality Inspection` where inspection_type='Final QC' and {0} and docstatus=1 group by inspected_by """.format(date_condition)
            productivity_daily_sql = """ select a.employee, count(a.serial_no) as count
            from
            (
            select qi.inspected_by as employee ,sed.serial_no as serial_no ,(se.posting_date) as date
            from `tabStock Entry` se 
            inner join `tabStock Entry Detail` sed on sed.parent=se.name 
            inner join `tabQuality Inspection` qi on qi.item_serial_no=sed.serial_no 
            and se.docstatus='1'
            and qi.docstatus = '1'
            and se.posting_date
            and se.purpose = 'Material Transfer'
            and qi.inspection_type = '{2}'
            and {1}
            )as a
            where {0}
            group by a.employee; """.format(condition,warehouse_condition,inspection_type)
            productivity_daily_sql = """ select inspected_by as employee,count(*) as count from `tabQuality Inspection` where inspection_type='Final QC' and {0} and docstatus=1 and inspected_by in ('mdayyan007f@gmail.com','sagarsahusagarsahu96@gmail.com','asifalishaik022@gmail.com','modelerboyyaseen@gmail.com','salman@usedyetnew.com','girimyki@gmail.com') group by inspected_by """.format(date_condition)

        # print productivity_daily_sql
        incoming_employs_array = []
        incoming_employs_count_array = []
        for prod in frappe.db.sql(productivity_daily_sql,as_dict=1):
            if warehouse=='Incoming Team':
                incoming_employs_array.append(prod.get("employee"))
                incoming_employs_count_array.append((prod.get("employee"),prod.get("count")))
            else:
                custom_data.append([prod.get("employee"),prod.get("count")])
        if warehouse=='Incoming Team':
            num_dict = {}
            for t in incoming_employs_count_array:
                if t[0] in num_dict:
                    num_dict[t[0]] = num_dict[t[0]]+t[1]
                else:
                    num_dict[t[0]] = t[1]
            for key,value in num_dict.items():
                custom_data.append([str(key),str(value)])
        return custom_data
        # return custom_data
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
                    count_str = 0
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
        data.append(["Company Net Productivity","","",""])
        # net_today = """ select count(sed.serial_no) as month from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name where se.posting_date = CURDATE() - INTERVAL 1 DAY and sed.s_warehouse='Packing - Uyn' and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and sed.serial_no not in (select sed.serial_no from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name where sed.s_warehouse='G3 Ready To Ship - Uyn' and sed.t_warehouse='Flat 301 Inward - Uyn' and se.docstatus=1) """
        # net_week = """ select count(sed.serial_no) as month from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name where se.posting_date > CURDATE() - INTERVAL 7 DAY and se.posting_date <= CURDATE() and sed.s_warehouse='Packing - Uyn' and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and sed.serial_no not in (select sed.serial_no from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name where sed.s_warehouse='G3 Ready To Ship - Uyn' and sed.t_warehouse='Flat 301 Inward - Uyn' and se.docstatus=1) """
        # net_month = """ select count(sed.serial_no) as month from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name where MONTH(se.posting_date)=MONTH(CURDATE()) and YEAR(se.posting_date) = YEAR(CURDATE()) and sed.s_warehouse='Packing - Uyn' and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and sed.serial_no not in (select sed.serial_no from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name where sed.s_warehouse='G3 Ready To Ship - Uyn' and sed.t_warehouse='Flat 301 Inward - Uyn' and se.docstatus=1) """
        net_today = """ 
            (select count(distinct sed.serial_no) as daily from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and se.posting_date = '{1}' and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{0}' and se.purpose='Material Transfer')
            union
            (select count(distinct sed.serial_no) as daily from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and se.posting_date = '{1}' and sed.t_warehouse='Amazon Warehouse - Uyn' and sed.s_warehouse<>'G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{0}' and se.purpose='Material Transfer')
            union
            (select count(distinct dni.serial_no) as daily from `tabDelivery Note Item` dni inner join `tabDelivery Note` dn on dn.name=dni.parent inner join tabItem i on i.item_code=dni.item_code where i.item_group='Laptops' and dn.posting_date > '{1}' and dni.warehouse not in ('Amazon Warehouse - Uyn','G3 Ready To Ship - Uyn') and dn.is_return='0' and dni.item_code not like '{0}' and dn.docstatus='1')
        """.format("%Macbook%",self.yesterday_str)
        net_week = """
            (select count(distinct sed.serial_no) as weekly from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and se.posting_date >='{0}' and se.posting_date <= '{1}' and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{2}' and se.purpose='Material Transfer' and MONTH(se.posting_date)=MONTH('{3}') and YEAR(se.posting_date)=YEAR('{3}'))
            union
            (select count(distinct sed.serial_no) as weekly from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and se.posting_date >='{0}' and se.posting_date <= '{1}' and sed.t_warehouse='Amazon Warehouse - Uyn' and sed.s_warehouse<>'G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{2}' and se.purpose='Material Transfer' and MONTH(se.posting_date)=MONTH('{3}') and YEAR(se.posting_date)=YEAR('{3}'))
            union
            (select count(distinct dni.serial_no) as weekly from `tabDelivery Note Item` dni inner join `tabDelivery Note` dn on dn.name=dni.parent inner join tabItem i on i.item_code=dni.item_code where i.item_group='Laptops' and dn.posting_date >='{0}' and dn.posting_date <= '{1}' and dni.warehouse not in ('Amazon Warehouse - Uyn','G3 Ready To Ship - Uyn') and dn.is_return='0' and dni.item_code not like '{2}' and dn.docstatus='1' and MONTH(dn.posting_date)=MONTH('{3}') and YEAR(dn.posting_date)=YEAR('{3}'))
        """.format(self.weekstartdate,self.weekenddate,"%Macbook%",self.today)
        net_month = """
            (select count(distinct sed.serial_no) as monthly from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and MONTH(se.posting_date)=MONTH('{1}') and YEAR(se.posting_date) = YEAR('{1}') and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{0}' and se.purpose='Material Transfer')
            union
            (select count(distinct sed.serial_no) as monthly from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and MONTH(se.posting_date)=MONTH('{1}') and YEAR(se.posting_date) = YEAR('{1}') and sed.t_warehouse='Amazon Warehouse - Uyn' and sed.s_warehouse<>'G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{0}' and se.purpose='Material Transfer')
            union
            (select count(distinct dni.serial_no) as monthly from `tabDelivery Note Item` dni inner join `tabDelivery Note` dn on dn.name=dni.parent inner join tabItem i on i.item_code=dni.item_code where i.item_group='Laptops' and MONTH(dn.posting_date)=MONTH('{1}') and YEAR(dn.posting_date) = YEAR('{1}') and dni.warehouse not in ('Amazon Warehouse - Uyn','G3 Ready To Ship - Uyn') and dn.is_return='0' and dni.item_code not like '{0}' and dn.docstatus='1')
        """.format("%Macbook%",self.today)
        gross_today = """ 
            (select count(sed.serial_no) as daily from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and se.posting_date = '{1}' and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{0}' and se.purpose='Material Transfer')
            union
            (select count(sed.serial_no) as daily from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and se.posting_date = '{1}' and sed.t_warehouse='Amazon Warehouse - Uyn' and sed.s_warehouse<>'G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{0}' and se.purpose='Material Transfer')
            union
            (select sum(dni.qty) as daily from `tabDelivery Note Item` dni inner join `tabDelivery Note` dn on dn.name=dni.parent inner join tabItem i on i.item_code=dni.item_code where i.item_group='Laptops' and dn.posting_date > '{1}' and dni.warehouse not in ('Amazon Warehouse - Uyn','G3 Ready To Ship - Uyn') and dn.is_return='0' and dni.item_code not like '{0}' and dn.docstatus='1')
        """.format("%Macbook%",self.yesterday_str)
        gross_week = """
            (select count(sed.serial_no) as weekly from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and se.posting_date >='{0}' and se.posting_date <= '{1}' and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{2}' and se.purpose='Material Transfer' and MONTH(se.posting_date)=MONTH('{3}') and YEAR(se.posting_date)=YEAR('{3}'))
            union
            (select count(sed.serial_no) as weekly from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and se.posting_date >='{0}' and se.posting_date <= '{1}' and sed.t_warehouse='Amazon Warehouse - Uyn' and sed.s_warehouse<>'G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{2}' and se.purpose='Material Transfer' and MONTH(se.posting_date)=MONTH('{3}') and YEAR(se.posting_date)=YEAR('{3}'))
            union
            (select sum(dni.qty) as weekly from `tabDelivery Note Item` dni inner join `tabDelivery Note` dn on dn.name=dni.parent inner join tabItem i on i.item_code=dni.item_code where i.item_group='Laptops' and dn.posting_date >='{0}' and dn.posting_date <= '{1}' and dni.warehouse not in ('Amazon Warehouse - Uyn','G3 Ready To Ship - Uyn') and dn.is_return='0' and dni.item_code not like '{2}' and dn.docstatus='1' and MONTH(dn.posting_date)=MONTH('{3}') and YEAR(dn.posting_date)=YEAR('{3}'))
        """.format(self.weekstartdate,self.weekenddate,"%Macbook%",self.today)
        gross_month = """
            (select count(sed.serial_no) as monthly from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and MONTH(se.posting_date)=MONTH('{1}') and YEAR(se.posting_date) = YEAR('{1}') and sed.t_warehouse='G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{0}' and se.purpose='Material Transfer')
            union
            (select count(sed.serial_no) as monthly from `tabStock Entry` se inner join `tabStock Entry Detail` sed on sed.parent=se.name inner join tabItem i on i.item_code=sed.item_code where i.item_group='Laptops' and MONTH(se.posting_date)=MONTH('{1}') and YEAR(se.posting_date) = YEAR('{1}') and sed.t_warehouse='Amazon Warehouse - Uyn' and sed.s_warehouse<>'G3 Ready To Ship - Uyn' and se.docstatus=1 and i.item_code not like '{0}' and se.purpose='Material Transfer')
            union
            (select sum(dni.qty) as monthly from `tabDelivery Note Item` dni inner join `tabDelivery Note` dn on dn.name=dni.parent inner join tabItem i on i.item_code=dni.item_code where i.item_group='Laptops' and MONTH(dn.posting_date)=MONTH('{1}') and YEAR(dn.posting_date) = YEAR('{1}') and dni.warehouse not in ('Amazon Warehouse - Uyn','G3 Ready To Ship - Uyn') and dn.is_return='0' and dni.item_code not like '{0}' and dn.docstatus='1')
        """.format("%Macbook%",self.today)
        daily_net_prod_res = 0
        weekly_net_prod_res = 0
        montly_net_prod_res = 0
        daily_gross_prod_res = 0
        weekly_gross_prod_res = 0
        montly_gross_prod_res = 0
        for net_prod in frappe.db.sql(net_today,as_dict=1):
            if net_prod.get("daily"):
                daily_net_prod_res += net_prod.get("daily")
        for net_prod in frappe.db.sql(net_week,as_dict=1):
            if net_prod.get("weekly"):
                weekly_net_prod_res += net_prod.get("weekly")
        for net_prod in frappe.db.sql(net_month,as_dict=1):
            if net_prod.get("monthly"):
                montly_net_prod_res += net_prod.get("monthly")
        for gross_prod in frappe.db.sql(gross_today,as_dict=1):
            if gross_prod.get("daily"):
                daily_gross_prod_res += gross_prod.get("daily")
        for gross_prod in frappe.db.sql(gross_week,as_dict=1):
            if gross_prod.get("weekly"):
                weekly_gross_prod_res += gross_prod.get("weekly")
        for gross_prod in frappe.db.sql(gross_month,as_dict=1):
            if gross_prod.get("monthly"):
                montly_gross_prod_res += gross_prod.get("monthly")
        data.append(["Format: net (gross)","%s (%s)" %(daily_net_prod_res,daily_gross_prod_res),"%s (%s)" %(weekly_net_prod_res,weekly_gross_prod_res),"%s (%s)" %(montly_net_prod_res,montly_gross_prod_res)])
        return data
@frappe.whitelist()
def execute(filters=None):
    args = {

    }
    return OperationsProductivity(filters).run(args)
    # data = []

    # rows = get_dataget_data()
    # for row in rows:
    #   data.append(row)
    # return columns,data
