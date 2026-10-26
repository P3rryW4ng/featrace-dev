"""Bounded task-scoped execution grants, independent of evidence applicability."""
from datetime import datetime,timezone
MAX_GRANTS=16


def material(rules):
    # Decision/source remain substantive; pure permission/approver metadata does not re-sign facts.
    return [{k:v for k,v in r.items() if k not in ('permission','authority')} for r in rules]


def validate(doc,fail):
    if 'facts' not in doc:return
    grants=doc.get('authorizations')
    if not isinstance(grants,dict) or len(grants)>MAX_GRANTS:fail('AUTHORIZATION_LIMIT')
    keys={'id','check','definition_digest','execution_digest','policy_digest','mode','authority','decision_at','reason','expires_at','uses'}
    for gid,g in grants.items():
        if (not isinstance(g,dict) or set(g)!=keys or g['id']!=gid or g['mode'] not in ('once','task')
                or not all(isinstance(g[k],str) and g[k].strip() for k in ('id','check','definition_digest','policy_digest','authority','decision_at','reason','expires_at'))
                or not isinstance(g['uses'],list) or len(g['uses'])>128 or any(not isinstance(x,str) for x in g['uses'])
                or len(set(g['uses']))!=len(g['uses']) or (g['mode']=='once' and len(g['uses'])>1)
                or (g['mode']=='once' and not isinstance(g['execution_digest'],str))
                or (g['mode']=='task' and g['execution_digest'] is not None)):
            fail('AUTHORIZATION_INVALID')


def select(doc,check,stamp,policy_digest,definition_digest,rules,at,fail):
    if any(r['permission']=='denied' for r in rules):fail('OPERATION_POLICY_DENIED')
    if not any(r['permission']=='ask' for r in rules):
        return {'kind':'standing','at':at,'policy_digest':policy_digest}
    for g in reversed(list(doc['authorizations'].values())):
        if (g['check']==check['id'] and g['definition_digest']==definition_digest
                and g['policy_digest']==policy_digest and datetime.fromisoformat(g['expires_at'])>datetime.fromisoformat(at)
                and (g['mode']=='task' or (not g['uses'] and g['execution_digest']==stamp))):
            return {'kind':'grant','grant':g['id'],'at':at,'policy_digest':policy_digest}
    fail('OPERATION_POLICY_ASK')
