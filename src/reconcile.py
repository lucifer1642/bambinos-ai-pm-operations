import pandas as pd, json, argparse
from pathlib import Path

def run(data_dir):
    d=Path(data_dir)
    inv=pd.read_csv(d/'1_invoices.csv',dtype=str,keep_default_na=False)
    forms=pd.read_csv(d/'2_faculty_form_unapproved.csv',dtype=str,keep_default_na=False)
    req=pd.read_csv(d/'3_booking_requests.csv',dtype=str,keep_default_na=False)
    sched=pd.read_csv(d/'4_class_schedule_bookings.csv',dtype=str,keep_default_na=False)
    ref=pd.read_csv(d/'reference_active_batches_and_students.csv',dtype=str,keep_default_na=False)
    for df in [inv,forms,req,sched,ref]:
        if 'deleted_at' in df: df.drop(df[df.deleted_at.str.upper()!='NULL'].index,inplace=True)
    # Ignore only explicit soft-deleted rows; NULL is the source's live marker.
    invmap={r.id:r for r in inv.itertuples()}; refmap={r.student_id:r for r in ref.itertuples()}
    req_by_invoice={r.invoice_id:r for r in req.itertuples()}
    schedule_by_req={}
    for r in sched.itertuples(): schedule_by_req.setdefault(r.bookingrequest_id,[]).append(r)
    seen={}; approvals=[]; exceptions=[]; messages=[]
    def flag(code,reason,owner,invoice,form,action):
        exceptions.append({'invoice_id':invoice,'form_id':form,'reason_code':code,'reason':reason,'owner':owner,'next_action':action})
    for f in forms.itertuples():
        iid=f.invoice_id; i=invmap.get(iid); student=refmap.get(f.student_id)
        if iid in seen:
            flag('DUPLICATE_FORM','Multiple faculty forms reference the same invoice; retain one canonical submission and audit duplicate.','Operations',iid,f.id,'Deduplicate by invoice_id; do not create a second booking.')
            continue
        seen[iid]=f.id
        if not i:
            flag('INVOICE_NOT_FOUND','Form references an invoice_id absent from invoices.','Operations + Teacher',iid,f.id,'Teacher to correct invoice reference; Ops verify gateway record.')
            continue
        if i.payment_status!='Paid':
            code='PAYMENT_FAILED' if i.payment_status=='Failed' else 'PARTIAL_PAYMENT'
            flag(code,f"Invoice status is {i.payment_status}; only fully Paid renewals qualify for automatic approval.",'Finance/Ops',iid,f.id,'Confirm settlement with gateway; request balance payment if applicable.')
            continue
        if not student:
            flag('STUDENT_REFERENCE_MISSING','Student not found in active reference master.','Operations',iid,f.id,'Validate student identity and active enrolment before booking.')
            continue
        mismatches=[]
        for label,a,b in [('user_id',i.user_id,f.user_id),('student_id',i.student_id,f.student_id),('class_id',i.class_id,f.class_id),('educator_id',i.educator_id,f.educator_id)]:
            if a!=b: mismatches.append(label)
        if mismatches:
            flag('IDENTITY_OR_OWNERSHIP_MISMATCH','Invoice and form disagree on '+', '.join(mismatches)+'.','Operations',iid,f.id,'Resolve against canonical student record; do not infer identity from masked PII.')
            continue
        if f.educator_id!=student.educator_id or f.class_id!=student.class_id:
            flag('MASTER_DATA_MISMATCH','Form educator/class does not match active student master.','Operations + Academic Ops',iid,f.id,'Confirm teacher/course ownership and update source record.')
            continue
        if f.parent_mobile and i.mobile and f.parent_mobile!=i.mobile:
            # Masked strings are not identity proof; mismatch routed for human confirmation.
            flag('PARENT_CONTACT_MISMATCH','Form parent mobile differs from invoice mobile; masked data prevents reliable fuzzy matching.','Parent Support',iid,f.id,'Confirm payer/guardian using verified contact channel; update canonical contact only after verification.')
            continue
        if float(i.net_amount or 0)!=float(f.amount_paid or 0):
            flag('AMOUNT_MISMATCH',f"Invoice net_amount {i.net_amount} differs from faculty amount_paid {f.amount_paid}.",'Finance + Teacher',''+iid,f.id,'Teacher correct amount; Finance verify invoice discount/net settlement.')
            continue
        if f.continue_same_batch!='Yes':
            flag('BATCH_CHANGE_REQUEST','Parent/teacher selected a different batch or schedule.','Scheduling Ops',iid,f.id,'Offer eligible batches and capacity; obtain parent confirmation before allocation.')
            continue
        if f.current_classbatch_id!=student.current_classbatch_id:
            flag('CURRENT_BATCH_MISMATCH','Form current batch differs from active student master.','Scheduling Ops',iid,f.id,'Verify latest enrolment/batch history.')
            continue
        if f.preferred_days!=student.batch_days or f.preferred_time_slot!=student.batch_start_time:
            flag('SCHEDULE_PREFERENCE_MISMATCH','Same-batch request does not match reference batch days/time.','Scheduling Ops',''+iid,f.id,'Confirm intended schedule with parent and teacher.')
            continue
        if int(student.active_students_count)>=int(student.max_batch_size):
            flag('BATCH_AT_CAPACITY','Current batch is already at maximum capacity.','Scheduling Ops',iid,f.id,'Check approved capacity buffer or propose alternate batch; never overbook.')
            continue
        if iid in req_by_invoice:
            existing=req_by_invoice[iid]
            flag('BOOKING_REQUEST_ALREADY_EXISTS',f"Booking request {existing.id} already exists; avoid duplicate creation.",'Operations',iid,f.id,'Idempotently update/continue existing request after checking its status.')
            continue
        approvals.append({'invoice_id':iid,'form_id':f.id,'student_id':f.student_id,'user_id':f.user_id,'class_id':f.class_id,'educator_id':f.educator_id,'classbatch_id':student.current_classbatch_id,'sessions_count':f.sessions_purchased,'preferred_days':f.preferred_days,'preferred_time':f.preferred_time_slot,'decision':'AUTO_APPROVE_READY','note':'Payment, identity, amount, same-batch, schedule and capacity checks passed. Create booking request idempotently.'})
    # Invoice-level orphan and missing-form detection
    for i in inv.itertuples():
        if i.payment_status=='Paid' and i.is_renewal=='Yes' and i.id not in seen:
            flag('PAID_INVOICE_NO_FORM','Paid renewal invoice has no faculty renewal form.','Teacher + Operations',i.id,'','Auto-remind teacher; after 12h escalate to faculty lead.')
    # Actionable templates, never auto-send without verified contact & policy approval.
    for e in exceptions:
        audience='parent' if e['owner']=='Parent Support' else ('teacher' if 'Teacher' in e['owner'] else 'ops')
        messages.append({'invoice_id':e['invoice_id'],'audience':audience,'reason_code':e['reason_code'],'draft':f"Hello, we are completing the renewal for invoice {e['invoice_id']}. Our team needs to verify one detail ({e['reason_code']}) before confirming the next classes. Please reply to this message or contact Bambinos support. We will keep you updated."})
    # Existing booking requests are monitored separately, not silently auto-allocated.
    backlog=[]
    for r in req.itertuples():
        if r.request_status!='Completed' or r.batch_allocated!='Yes':
            backlog.append({'booking_request_id':r.id,'invoice_id':r.invoice_id,'status':r.request_status,'reason_code':'BOOKING_ALLOCATION_PENDING','owner':'Scheduling Ops'})
    result={'summary':{'invoice_rows':len(inv),'faculty_forms':len(forms),'booking_requests':len(req),'schedule_rows':len(sched),'auto_approve_ready':len(approvals),'exceptions':len(exceptions),'open_booking_requests':len(backlog)},'auto_approved_ready':approvals,'exceptions':exceptions,'message_drafts':messages,'booking_backlog':backlog}
    out=Path(data_dir).parent/'results';out.mkdir(exist_ok=True)
    pd.DataFrame(approvals).to_csv(out/'auto_approved_ready.csv',index=False)
    pd.DataFrame(exceptions).to_csv(out/'flagged_exceptions.csv',index=False)
    pd.DataFrame(messages).to_csv(out/'message_drafts.csv',index=False)
    (out/'reconciliation_summary.json').write_text(json.dumps(result,indent=2))
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data',default='data');a=ap.parse_args();print(json.dumps(run(a.data)['summary'],indent=2))
