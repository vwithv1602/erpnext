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
        columns = self.get_columns()
        data = self.get_data()
        return columns, data

    def get_columns(self):
        """return columns bab on filters"""
        columns = [
            _("Item Group") + "::120", 
            _("Item Code") + ":Data:320",
            _("RTS Qty") + ":Int:100",
            _("RTS Grade B Qty") + ":Int:100",
            _("Other Qty") + ":Int:100",
            _("Variant") + ":Check:100"
        ]
        return columns

    def is_duplicate_object(self,name_value_list,name_value):
        for ext_name_value in name_value_list:
            if ext_name_value[0]==name_value.get("item_group") and ext_name_value[1]==name_value.get("variant_of") and ext_name_value[2]==name_value.get("qty"):
                return False
        return True

    from datetime import timedelta,datetime
    
    def get_data(self):
        data = []
        
        rts_non_variant_result = self.get_non_variant_result_for_rts()
        # for item_group,item_code,qty,is_variant in rts_non_variant_result:
        for item in rts_non_variant_result:
            if item.get("qty") > 0:
                data.append([item.get("item_group"),item.get("variant_of"),item.get("qty"),item.get("grade_b_qty"),item.get("other_qty"),0])
        rts_variant_result = self.get_variant_result_for_rts()
        # for item_group,item_code,qty,is_variant in rts_variant_result:
        #     data.append([item_group,item_code,qty,is_variant])
        for item in rts_variant_result:
            if self.is_duplicate_object(data,item) and item.get("qty")>0:
                data.append([item.get("item_group"),item.get("variant_of"),item.get("qty"),item.get("grade_b_qty"),item.get("other_qty"),1])
        
        return data
    def get_non_variant_result_for_rts(self):
        result = []
        non_variant_rts_sql = """ 
        select i.item_group as item_group,i.item_code as item_code,sum(sle.actual_qty) as "qty",i.variant_of from `tabStock Ledger Entry` sle inner join `tabItem` i on i.item_code=sle.item_code where sle.warehouse in ('Ready To Ship - Uyn','Ready To Ship - FZI') and i.variant_of is NULL group by i.item_group,i.item_code limit 10
        """
        
        for item in frappe.db.sql(non_variant_rts_sql,as_dict=1):
            other_non_variant_rts_sql = """ 
            select i.item_group as item_group,i.item_code as item_code,sum(sle.actual_qty) as "qty",i.variant_of from `tabStock Ledger Entry` sle inner join `tabItem` i on i.item_code=sle.item_code where sle.warehouse not in ('Ready To Ship - Uyn','Ready To Ship - FZI') and i.variant_of is NULL and i.item_code='%s' group by i.item_group,i.item_code limit 10""" % item.get("item_code")
            grade_b_non_variant_rts_sql = """ 
            select i.item_group as item_group,i.item_code as item_code,sum(sle.actual_qty) as "qty",i.variant_of from `tabStock Ledger Entry` sle inner join `tabItem` i on i.item_code=sle.item_code where sle.warehouse in ('Ready To Ship Grade B - Uyn') and i.variant_of is NULL and i.item_code='%s' group by i.item_group,i.item_code limit 10""" % item.get("item_code")
            grade_b_non_variant_rts_res = frappe.db.sql(grade_b_non_variant_rts_sql,as_dict=1)
            other_qty_res = frappe.db.sql(other_non_variant_rts_sql,as_dict=1)
            if len(other_qty_res)>0:
                other_qty = other_qty_res[0].get("qty")
            else:
                other_qty = 0
            if len(grade_b_non_variant_rts_res)>0:
                grade_b_qty = grade_b_non_variant_rts_res[0].get("qty")
            else:
                grade_b_qty = 0
            result.append({"item_group":item.get("item_group"),"variant_of":item.get("item_code"),"qty":item.get("qty"),"grade_b_qty":grade_b_qty,"other_qty":other_qty})
        return result
    
    def get_variant_result_for_rts(self):
        result = []
        variant_rts_sql = """ 
        select distinct i.item_code as item_code,i.variant_of as variant_of,i.item_group as item_group from `tabStock Ledger Entry` sle inner join `tabItem` i on i.item_code=sle.item_code where sle.warehouse in ('Ready To Ship - Uyn','Ready To Ship - FZI') and i.variant_of is NOT NULL limit 10
        """
        variant_rts_res = frappe.db.sql(variant_rts_sql,as_dict=1)
        # for each item get non_replaceable_attr_vals
        for item in variant_rts_res:            
            # non_replaceable_attr_vals_sql = """ select iva.attribute_value from `tabItem Variant Attribute` iva inner join `tabItem Attribute` ia on iva.attribute = ia.attribute_name where ia.is_replacable = "0" and iva.parent = '%s'""" % item.get("item_code")
            non_replaceable_attr_vals_sql = """ select iav.abbr from `tabItem Variant Attribute` iva inner join `tabItem Attribute` ia on iva.attribute = ia.attribute_name inner join `tabItem Attribute Value` iav on iav.attribute_value=iva.attribute_value where ia.is_replacable = "0" and iva.parent = '%s' and iva.attribute=iav.parent limit 10 """ % item.get("item_code")
            non_replaceable_attr_vals = []
            for nrav in frappe.db.sql(non_replaceable_attr_vals_sql, as_dict=1):
                non_replaceable_attr_vals.append(nrav.get("abbr"))
            # Create the where_string to be added in sql
            where_string = ""
            nravs = ""
            for attribute in non_replaceable_attr_vals:
                where_string += " and item_code like %s " % ('\'%'+attribute+'%\'')
                nravs += "-%s" % attribute
            # Prepare the below query to get the balance
            bal_sql = """ select sum(actual_qty) as bal_qty from `tabStock Ledger Entry` where item_code in (select distinct item_code from  `tabItem Variant Attribute` iva inner join tabItem i on i.item_code = iva.parent where i.variant_of ='%s' %s and warehouse  in ('Ready To Ship - Uyn','Ready To Ship - FZI') ) limit 10""" %(item.get("variant_of"),where_string)
            other_bal_sql = """ select sum(actual_qty) as bal_qty from `tabStock Ledger Entry` where item_code in (select distinct item_code from  `tabItem Variant Attribute` iva inner join tabItem i on i.item_code = iva.parent where i.variant_of ='%s' %s and warehouse not in ('Ready To Ship - Uyn','Ready To Ship - FZI') ) limit 10""" %(item.get("variant_of"),where_string)
            grade_b_bal_sql = """ select sum(actual_qty) as bal_qty from `tabStock Ledger Entry` where item_code in (select distinct item_code from  `tabItem Variant Attribute` iva inner join tabItem i on i.item_code = iva.parent where i.variant_of ='%s' %s and warehouse in ('Ready To Ship Grade B - Uyn') ) limit 10""" %(item.get("variant_of"),where_string)
            grade_b_bal_res = frappe.db.sql(grade_b_bal_sql, as_dict=1)
            grade_b_qty = grade_b_bal_res[0].get("bal_qty")
            other_bal_res = frappe.db.sql(other_bal_sql, as_dict=1)
            other_qty = other_bal_res[0].get("bal_qty")
            if other_qty < 0:
                other_qty = 0
            if grade_b_qty < 0:
                grade_b_qty = 0
            for bal_qty in frappe.db.sql(bal_sql, as_dict=1):
                if bal_qty.get("bal_qty"):
                    qty_to_be_updated = bal_qty.get("bal_qty")
                    if qty_to_be_updated > 0:
                        result.append({"item_group":item.get("item_group"),"variant_of":item.get("variant_of")+nravs,"qty":qty_to_be_updated,"grade_b_qty":grade_b_qty,"other_qty":other_qty})
                    # vwrite("%s %s : %s" % (item.get("variant_of"),nravs,qty_to_be_updated))
                #else:
                    #qty_to_be_updated = 0
                    #result.append({"item_group":item.get("item_group"),"variant_of":item.get("variant_of")+nravs,"qty":qty_to_be_updated})
                    # vwrite("%s %s : %s" % (item.get("variant_of"),nravs,qty_to_be_updated))
        
        return result

def execute(filters=None):
    args = {

    }
    return ReadyToShip(filters).run(args)
    # data = []

    # rows = get_dataget_data()
    # for row in rows:
    #   data.append(row)
    # return columns,data




