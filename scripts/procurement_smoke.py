"""Exercise deployed procurement over HTTP; reports omit credentials/raw evidence.

Always simulated orders. Each committed test consumes the synthetic shared cap.
Usage: .venv/bin/python scripts/procurement_smoke.py --url https://... [--live]
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from backend.config import access_codes, LOCAL

parser=argparse.ArgumentParser()
parser.add_argument('--url',required=True)
parser.add_argument('--live',action='store_true')
args=parser.parse_args()
checks=[]
report={'url':args.url,'checks':checks,'orders':'simulated_only'}

def checked(name,condition):
    assert condition,name
    checks.append(name)
    report['check_count']=len(checks)
    (LOCAL/'procurement-deployed-report.json').write_text(json.dumps(report,indent=2))
    print('PASS '+name,flush=True)

with httpx.Client(base_url=args.url,timeout=100) as client:
    health=client.get('/health')
    checked('HTTPS health and persistent storage',health.status_code==200 and health.json()['storage'] in ['sqlite','postgres'])
    checked('Private cart requires authentication',client.get('/api/v1/procurement/sessions/missing').status_code==401)
    checked('Buyer sign-in',client.post('/api/v1/session',json={'access_code':access_codes()['buyer']}).status_code==200)
    def call(path,data):
        response=client.post('/api/v1/procurement/sessions'+path,json=data)
        assert response.status_code==200,(response.status_code,response.text[:400])
        return response.json()
    session=call('',{'message':'20 litres of lactose-free milk and 10 kg of cheese by Monday. Choose the cheapest suitable products.','mode':'fixture','use_model':False})
    checked('Real catalog multi-product quotation',len(session['lines'])==2 and session['order_status']=='READY_TO_ORDER' and session['cart']['subtotal'] is not None)
    before=session['lines'][1]['selected_product_id']
    old_version=session['version']
    session=call('/'+session['id']+'/actions',{'version':old_version,'action':'message','message':'Change milk to 30 litres'})
    checked('Follow-up preserves unaffected choice',session['lines'][1]['selected_product_id']==before and session['lines'][0]['quantity']=='30')
    response=client.post('/api/v1/procurement/sessions/'+session['id']+'/actions',json={'version':old_version,'action':'quote'})
    checked('Concurrent stale version rejected',response.status_code==409)
    session=call('/'+session['id']+'/actions',{'version':session['version'],'action':'set_budget','budget':'0.01'})
    checked('Hard budget blocks whole basket',not session['can_confirm'] and session['order_status']!='READY_TO_ORDER')
    session=call('/'+session['id']+'/actions',{'version':session['version'],'action':'set_budget','budget':'500'})
    checked('Explicit budget correction restores basket',session['can_confirm'])
    sid=session['id']
    fingerprint=session['offer']['fingerprint']
    key='smoke-'+uuid.uuid4().hex
    response=client.post('/api/v1/procurement/sessions/'+sid+'/confirm',json={'fingerprint':fingerprint},headers={'Idempotency-Key':key})
    assert response.status_code==200,response.text[:400]
    receipt=response.json()['receipt']
    checked('Fresh revalidation and simulated receipt',receipt['simulated'] is True)
    response=client.post('/api/v1/procurement/sessions/'+sid+'/confirm',json={'fingerprint':fingerprint},headers={'Idempotency-Key':key})
    checked('Idempotent confirmation returns same receipt',response.status_code==200 and response.json()['receipt']['id']==receipt['id'] and response.json()['receipt']['idempotent_replay'])
    verification=client.get('/api/v1/procurement/sessions/'+sid+'/verify').json()
    checked('Read-only receipt consistency',verification['integrity_valid'] and verification['scope_valid'])
    report['receipt_id']=receipt['id']; report['synthetic_subtotal']=receipt['total']
    # A fresh app request reopens durable state, not an in-browser copy.
    restored=client.get('/api/v1/procurement/sessions/'+sid).json()
    checked('Saved cart and receipt recovery',restored['receipt']['id']==receipt['id'])
    if args.live:
        result=call('',{'message':'I need 20 litres of lactose-free milk and 5 kg of butter by Monday. Budget €500. Choose the cheapest suitable products.','mode':'live','use_model':True})
        checked('Live NVIDIA typed interpretation',result.get('interpretation_source')=='NVIDIA typed interpretation' and len(result['lines'])==2)
        sources={c['source'] for line in result['lines'] for c in line['candidates']}
        checked('Live Valio price and availability',sources=={'live_valio_sandbox'})
        report['live_status']=result['order_status']
        report['live_subtotal']=result['cart']['subtotal']
    report['check_count']=len(checks)
    (LOCAL/'procurement-deployed-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
