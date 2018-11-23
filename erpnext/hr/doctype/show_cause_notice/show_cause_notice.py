# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, markdown
from erpnext_uyn_customizations.vlog import vwrite
class ShowCauseNotice(Document):
	pass

@frappe.whitelist()
def render_msg(showcause,method):
	vwrite(method)
	tm = showcause
	data = {
		'employee': showcause.__dict__.get("employee"),
		'reason_for_show_cause': showcause.__dict__.get("reason_for_show_cause"),
		'preliminary_investigation': showcause.__dict__.get("preliminary_investigation"),
		'decision_of_violation': showcause.__dict__.get("decision_of_violation")
	}
	stats = frappe.render_template('erpnext/hr/doctype/show_cause_notice/show_cause_notice.md', data, is_path=True)
	res = markdown(stats)
	import re
	cleanr = re.compile('<.*?>')
  	cleantext = re.sub(cleanr, '', res)
	
	tm.show_cause_notice = res
	# tm.save(ignore_permissions=True)
	if method == 'on_submit':
		subject_title = 'Show Cause Notice: %s' % showcause.__dict__.get("employee")
		email_id = get_employee_email(showcause.__dict__.get("employee"))
		frappe.sendmail(recipients=[email_id,"visheshhanda@usedyetnew.com","marketing@usedyetnew.com"], subject=subject_title, message=markdown(stats))

def get_employee_email(emp_name):
	employee = frappe.get_all('Employee',filters={"name":emp_name},fields=['user_id'])
	if not len(employee):
		user = frappe.get_all('User', filters={'full_name': emp_name}, fields=['email'])
		return user[0].get("email")

	else:
		return employee[0].get("user_id")
