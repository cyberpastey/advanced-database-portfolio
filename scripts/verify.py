"""Rebuild and verify the isolated PayFlow lab. Never point this at production."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import json, os, statistics, time, threading, concurrent.futures, traceback
import psycopg
from pymongo import MongoClient
from pymongo.errors import WriteError, DuplicateKeyError

R = Path(__file__).resolve().parents[1]
for line in (R/'.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k,v=line.split('=',1); os.environ.setdefault(k,v)
PW=os.environ['POSTGRES_PASSWORD']
DSN=dict(host='127.0.0.1',port=55432,dbname='payflow',user='payflow',password=PW)
RUN={'started_at':datetime.now(timezone.utc).isoformat(),'activities':{}}
def connect(**kw):
    return psycopg.connect(**(DSN|kw))
def save(path,obj):
    p=R/path; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,default=str)+'\n',encoding='utf-8')
def sql(c,text,args=None): return c.execute(text,args)
def balances(c,ids=(2,3)):
    return dict(c.execute('SELECT wallet_id,balance FROM payflow.wallet_balances WHERE wallet_id=ANY(%s)',(list(ids),)).fetchall())
def post(c,key,s=2,r=3,a=1,rev=None):
    return c.execute('SELECT payflow.post_transfer(%s,%s,%s,%s,%s)',(key,s,r,a,rev)).fetchone()[0]
def invariant(c):
    net=c.execute('SELECT coalesce(sum(amount),0) FROM payflow.ledger_entries').fetchone()[0]
    bad=c.execute("SELECT count(*) FROM payflow.wallet_balances WHERE kind='customer' AND balance<0").fetchone()[0]
    shape=c.execute('''SELECT count(*) FROM (SELECT t.transfer_id FROM payflow.transfers t
       LEFT JOIN payflow.ledger_entries l USING(transfer_id) GROUP BY t.transfer_id
       HAVING count(l.entry_id)<>2 OR sum(l.amount)<>0
       OR sum(l.amount) FILTER(WHERE l.wallet_id=t.sender_id) IS DISTINCT FROM -t.amount
       OR sum(l.amount) FILTER(WHERE l.wallet_id=t.receiver_id) IS DISTINCT FROM t.amount) x''').fetchone()[0]
    missing=c.execute('SELECT count(*) FROM payflow.transfers t LEFT JOIN payflow.outbox_events o USING(transfer_id) WHERE o.event_id IS NULL').fetchone()[0]
    assert net==0 and bad==0 and shape==0 and missing==0,(net,bad,shape,missing)
    return dict(net_ledger=str(net),negative_customers=bad,malformed_transfers=shape,missing_outbox=missing)

def p1():
    evidence={}
    with connect() as c:
        c.execute((R/'portfolio-1-database-design/schema.sql').read_text())
        c.execute((R/'portfolio-1-database-design/sample_data.sql').read_text())
    with connect() as c:
        evidence['versions']=c.execute('SELECT version(),current_database()').fetchone()
        evidence['rows']={t:c.execute(f'SELECT count(*) FROM payflow.{t}').fetchone()[0] for t in ['customers','wallets','transfers','ledger_entries','outbox_events']}
        evidence['invariants']=invariant(c)
    tests=[
      ('unique_email',"INSERT INTO payflow.customers(full_name,email) VALUES('Duplicate','customer1@example.test')",'23505'),
      ('foreign_key',"INSERT INTO payflow.wallets(customer_id,kind) VALUES(9999999,'customer')",'23503'),
      ('wallet_kind',"INSERT INTO payflow.wallets(kind) VALUES('invalid')",'23514'),
      ('same_wallet',"SELECT payflow.post_transfer('same-wallet',2,2,1)",'22023'),
      ('fractional_kobo',"SELECT payflow.post_transfer('fractional',2,3,1.001)",'22023'),
      ('negative_amount',"SELECT payflow.post_transfer('negative',2,3,-1)",'22023'),
      ('immutable',"UPDATE payflow.ledger_entries SET amount=amount WHERE entry_id=1",'23514'),
      ('incomplete_posting',"INSERT INTO payflow.transfers(request_key,sender_id,receiver_id,amount) VALUES('bad-shape',2,3,1)",'23514'),
      ('app_cannot_insert',"SET ROLE payflow_app; INSERT INTO payflow.ledger_entries(transfer_id,wallet_id,amount) VALUES(1,2,1)",'42501')]
    evidence['negative_tests']=[]
    for name,query,expected in tests:
        try:
            with connect() as c: c.execute(query)
        except psycopg.Error as e:
            assert e.sqlstate==expected,(name,e.sqlstate)
            evidence['negative_tests'].append({'test':name,'sqlstate':e.sqlstate,'outcome':'rejected as expected','message':e.diag.message_primary})
        else: raise AssertionError(name+' unexpectedly accepted')
    with connect() as c:
        c.execute('SET ROLE payflow_app'); tid=post(c,'role-execute',2,3,1)
        evidence['app_execute_transfer']=tid
    save('portfolio-1-database-design/evidence/verification.json',evidence)
    return evidence

def p2():
    # Bound transaction-level advisory locks and deferred-trigger queues per batch.
    for start in range(1,60001,500):
        with connect() as batch:
            batch.execute("SELECT payflow.post_transfer('bench-'||i,2+(i%%2000),2+((i+1)%%2000),1+(i%%100)) FROM generate_series(%s::integer,%s::integer) i",(start,start+499))
    with connect() as c:
        # Setup timestamp assignment is privileged fixture construction, not application mutation.
        c.execute("SET search_path=payflow,public")
        c.execute('ALTER TABLE transfers DISABLE TRIGGER transfers_immutable')
        c.execute("UPDATE transfers SET created_at='2026-01-01'::timestamptz+(transfer_id%8640000)*interval '1 second' WHERE request_key LIKE 'bench-%'")
        # 60k rows span a day; Q8 uses this reproducible interval rather than an empty date.
        c.execute('ALTER TABLE transfers ENABLE TRIGGER transfers_immutable')
        c.execute('ANALYZE payflow.transfers; ANALYZE payflow.ledger_entries')
    qs={
       'time_range':"SELECT transfer_id,created_at,amount FROM payflow.transfers WHERE created_at>='2026-01-01 10:00:00+00' AND created_at<'2026-01-01 10:10:00+00' ORDER BY created_at,transfer_id",
       'high_value':"SELECT transfer_id,amount FROM payflow.transfers WHERE amount>=100000 ORDER BY amount,transfer_id"}
    results={}
    with connect(autocommit=True) as c:
        for idx in ['transfers_created_id','transfers_amount']:
            c.execute(f'DROP INDEX IF EXISTS payflow.{idx}')
        before={}
        for name,q in qs.items():
            before[name]=c.execute(q).fetchall()
            c.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+q).fetchone()
            plans=[c.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+q).fetchone()[0] for _ in range(5)]
            results[name]={'sql':q,'rows':len(before[name]),'before_plans':plans}
        c.execute((R/'portfolio-2-query-optimisation/indexes.sql').read_text())
        for name,q in qs.items():
            after=c.execute(q).fetchall(); assert after==before[name]
            c.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+q).fetchone()
            plans=[c.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+q).fetchone()[0] for _ in range(5)]
            b=statistics.median(p[0]['Execution Time'] for p in results[name]['before_plans'])
            a=statistics.median(p[0]['Execution Time'] for p in plans)
            results[name].update(after_plans=plans,before_median_ms=b,after_median_ms=a,result_parity=True,result_sample=after[:20])
        # Execute the supplied multi-statement query file and capture all result sets.
        cur=c.execute((R/'portfolio-2-query-optimisation/queries.sql').read_text())
        sets=[]
        while True:
            if cur.description: sets.append({'columns':[d.name for d in cur.description],'rows':cur.fetchall()})
            if not cur.nextset(): break
        save('portfolio-2-query-optimisation/evidence/query_results.json',sets)
        results['invariants']=invariant(c)
    save('portfolio-2-query-optimisation/execution_plans/benchmarks.json',results)
    lines=['# Actual performance analysis','Five measured trials per condition after an excluded warm-up. Same results verified. No planner scan type was forced.']
    for n in qs:
        e=results[n]; lines.append(f"{n}: {e['rows']} rows; baseline median {e['before_median_ms']:.3f} ms; indexed median {e['after_median_ms']:.3f} ms. Inspect raw plans for actual nodes and buffers.")
    lines.append('Limitations: single host, one dataset, baseline measured before indexed condition, cache drift, no concurrent production load. Timings are observations, not universal speed guarantees. Indexes incur write and storage overhead.')
    (R/'portfolio-2-query-optimisation/performance_analysis.md').write_text('\n\n'.join(lines)+'\n')
    return {n:{k:v for k,v in results[n].items() if k not in ['before_plans','after_plans','result_sample']} for n in qs}

def p3():
    e={}
    with connect() as c: before=balances(c)
    with connect() as c: tid=post(c,'verified-success',2,3,100)
    with connect() as c:
        after=balances(c); assert after[2]==before[2]-100 and after[3]==before[3]+100
        e['commit']={'status':'COMMIT','transfer_id':tid,'before':before,'after':after}
        assert post(c,'verified-success',2,3,100)==tid
    try:
        with connect() as c:
            post(c,'forced-rollback',2,3,25)
            c.execute('SELECT 1/0')
    except psycopg.errors.DivisionByZero: pass
    with connect() as c:
        assert balances(c)==after
        assert c.execute("SELECT count(*) FROM payflow.transfers WHERE request_key='forced-rollback'").fetchone()[0]==0
        e['rollback']={'status':'ROLLBACK','failure_sqlstate':'22012','unchanged_balances':True,'no_transfer':True}
        rev=post(c,'verified-reversal',3,2,100,tid)
        e['reversal']={'original':tid,'compensation':rev}
    try:
        with connect() as c: post(c,'verified-success',2,3,101)
    except psycopg.errors.InvalidParameterValue: e['idempotency_mismatch']='22023 rejected'
    else: raise AssertionError('mismatch accepted')
    # Controlled two-session competition: each individually affordable, jointly not.
    with connect() as c: available=balances(c,(10,))[10]
    amount=(available*Decimal('0.75')).quantize(Decimal('.01'))
    barrier=threading.Barrier(2)
    def worker(i):
        try:
            with connect() as c:
                c.execute("SET LOCAL lock_timeout='15s'")
                barrier.wait(timeout=10); ident=post(c,f'competition-{i}',10,11+i,amount)
            return {'worker':i,'outcome':'COMMIT','transfer_id':ident}
        except psycopg.Error as x: return {'worker':i,'outcome':'ROLLBACK','sqlstate':x.sqlstate,'error':x.diag.message_primary}
    with concurrent.futures.ThreadPoolExecutor(2) as ex: outcomes=list(ex.map(worker,[0,1]))
    assert sum(x['outcome']=='COMMIT' for x in outcomes)==1
    assert any(x.get('sqlstate')=='23514' for x in outcomes)
    e['competing_withdrawals']={'starting_balance':available,'each_amount':amount,'sessions':outcomes}
    # Observe a real blocked backend while A holds the wallet row.
    a=connect(); b=connect(); monitor=connect(autocommit=True)
    try:
        a.execute('SELECT wallet_id FROM payflow.wallets WHERE wallet_id=20 FOR UPDATE')
        pid=b.info.backend_pid
        def blocked():
            try:
                post(b,'lock-observation',20,21,1); b.commit(); return 'COMMIT'
            except Exception: b.rollback(); raise
        with concurrent.futures.ThreadPoolExecutor(1) as ex:
            future=ex.submit(blocked); observed=None
            for _ in range(100):
                row=monitor.execute('SELECT wait_event_type,wait_event FROM pg_stat_activity WHERE pid=%s',(pid,)).fetchone()
                if row and row[0]=='Lock': observed=row; break
                time.sleep(.05)
            a.commit(); result=future.result(timeout=20)
        assert observed, 'No actual lock wait observed'
        e['locking']={'observed_wait':observed,'after_release':result}
    finally: a.close(); b.close(); monitor.close()
    e['isolation']={}
    for level in ['READ COMMITTED','REPEATABLE READ']:
        a=connect(); b=connect()
        try:
            a.execute('BEGIN ISOLATION LEVEL '+level)
            first=balances(a,(30,))[30]
            post(b,'isolation-'+level,31,30,1); b.commit()
            second=balances(a,(30,))[30]
            assert second==first+(1 if level=='READ COMMITTED' else 0)
            e['isolation'][level]={'first':first,'second_after_other_commit':second}
            a.commit()
        finally: a.close(); b.close()
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS payflow.isolation_probe(id int PRIMARY KEY,value int)')
        c.execute('INSERT INTO payflow.isolation_probe VALUES(1,0) ON CONFLICT(id) DO UPDATE SET value=0')
    a=connect(); b=connect()
    try:
        for c in (a,b):
            c.execute('BEGIN ISOLATION LEVEL SERIALIZABLE'); c.execute('SELECT value FROM payflow.isolation_probe WHERE id=1').fetchone()
        a.execute('UPDATE payflow.isolation_probe SET value=value+1 WHERE id=1'); a.commit()
        try:
            b.execute('UPDATE payflow.isolation_probe SET value=value+1 WHERE id=1'); b.commit()
        except psycopg.errors.SerializationFailure:
            b.rollback(); e['serializable_conflict']={'sqlstate':'40001','outcome':'ROLLBACK; retry whole transaction required'}
        else: raise AssertionError('Expected serializable conflict')
    finally: a.close(); b.close()
    with connect() as c: e['invariants']=invariant(c)
    save('portfolio-3-transactions-concurrency/evidence/scenarios.json',e)
    return e

def p4():
    m=MongoClient('mongodb://127.0.0.1:57017',serverSelectionTimeoutMS=5000)
    try:
        d=m.payflow_lab; d.drop_collection('events')
        validator=json.loads((R/'portfolio-4-nosql/mongodb_schema/validator.json').read_text())
        d.create_collection('events',validator=validator,validationLevel='strict',validationAction='error')
        e=d.events
        e.create_index('event_id',unique=True)
        e.create_index([('wallet_id',1),('occurred_at',-1)])
        e.create_index('risk_score')
        with connect() as c: ids=c.execute('SELECT transfer_id,receiver_id FROM payflow.transfers ORDER BY transfer_id LIMIT 100').fetchall()
        docs=[dict(event_id=f'synthetic-{i}',wallet_id=int(w),transfer_id=int(t),type='transfer_review',occurred_at=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=i),risk_score=i%101,metadata={'device':f'sim-{i%5}','rule':'synthetic_velocity'}) for i,(t,w) in enumerate(ids)]
        e.insert_many(docs)
        assert e.count_documents({})==100
        found=list(e.find({'risk_score':{'$gte':70}},{'_id':0}).limit(5))
        upd=e.update_one({'event_id':'synthetic-0'},{'$set':{'metadata.reviewed':True}}); assert upd.modified_count==1
        assert e.find_one({'event_id':'synthetic-0'})['metadata']['reviewed'] is True
        invalid=dict(docs[1]); invalid.pop('_id',None); invalid['event_id']='invalid'; invalid['risk_score']=101
        try: e.insert_one(invalid)
        except WriteError as x: assert x.code==121; invalid_code=x.code
        else: raise AssertionError('Invalid document accepted')
        dupe=dict(docs[1]); dupe.pop('_id',None)
        try: e.insert_one(dupe)
        except DuplicateKeyError as x: duplicate_code=x.code
        else: raise AssertionError('Duplicate accepted')
        aggregate=list(e.aggregate([{'$group':{'_id':'$type','count':{'$sum':1},'meanRisk':{'$avg':'$risk_score'}}}]))
        assert aggregate[0]['count']==100
        deleted=e.delete_one({'event_id':'synthetic-99'}); assert deleted.deleted_count==1
        assert e.count_documents({})==99
        evidence=dict(version=m.server_info()['version'],inserted=100,filtered_sample=found,updated=1,deleted=1,remaining=99,invalid_document_error=invalid_code,duplicate_event_error=duplicate_code,aggregation_before_delete=aggregate,indexes=list(e.list_indexes()))
        save('portfolio-4-nosql/evidence/operations.json',evidence)
        return evidence
    finally: m.close()

def p5():
    # Lab-only password is never written into tracked evidence.
    replica=connect(port=55433,autocommit=True); primary=connect(autocommit=True)
    try:
        exists=replica.execute("SELECT count(*) FROM pg_subscription WHERE subname='payflow_sub'").fetchone()[0]
        if exists: replica.execute('DROP SUBSCRIPTION payflow_sub')
        for c in [primary,replica]:
            c.execute('CREATE SCHEMA IF NOT EXISTS distribution_lab')
            c.execute('DROP TABLE IF EXISTS distribution_lab.replication_probe')
            c.execute('CREATE TABLE distribution_lab.replication_probe(id int PRIMARY KEY,note text NOT NULL)')
        primary.execute('DROP PUBLICATION IF EXISTS payflow_pub')
        primary.execute("DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='payflow_repl') THEN CREATE ROLE payflow_repl LOGIN REPLICATION; END IF; END $$")
        primary.execute(psycopg.sql.SQL('ALTER ROLE payflow_repl PASSWORD {}').format(psycopg.sql.Literal(PW)))
        primary.execute('GRANT CONNECT ON DATABASE payflow TO payflow_repl')
        primary.execute('GRANT USAGE ON SCHEMA distribution_lab TO payflow_repl')
        primary.execute('GRANT SELECT ON distribution_lab.replication_probe TO payflow_repl')
        primary.execute('CREATE PUBLICATION payflow_pub FOR TABLE distribution_lab.replication_probe')
        conninfo=f'host=postgres port=5432 dbname=payflow user=payflow_repl password={PW}'
        replica.execute(psycopg.sql.SQL('CREATE SUBSCRIPTION payflow_sub CONNECTION {} PUBLICATION payflow_pub').format(psycopg.sql.Literal(conninfo)))
        def wait_for(ident):
            start=time.monotonic()
            for _ in range(200):
                if replica.execute('SELECT count(*) FROM distribution_lab.replication_probe WHERE id=%s',(ident,)).fetchone()[0]:
                    return round((time.monotonic()-start)*1000,3)
                time.sleep(.1)
            raise TimeoutError('Subscriber did not catch up')
        primary.execute("INSERT INTO distribution_lab.replication_probe VALUES(1,'initial synthetic marker')")
        first=wait_for(1)
        replica.execute('ALTER SUBSCRIPTION payflow_sub DISABLE')
        # Wait until worker has exited before testing paused state.
        for _ in range(100):
            if replica.execute("SELECT count(*) FROM pg_stat_subscription WHERE subname='payflow_sub' AND pid IS NOT NULL").fetchone()[0]==0: break
            time.sleep(.1)
        else: raise TimeoutError('Subscription worker did not stop')
        primary.execute("INSERT INTO distribution_lab.replication_probe VALUES(2,'paused marker')")
        absent=replica.execute('SELECT count(*) FROM distribution_lab.replication_probe WHERE id=2').fetchone()[0]==0
        assert absent
        replica.execute('ALTER SUBSCRIPTION payflow_sub ENABLE')
        recovery=wait_for(2)
        rows=replica.execute('TABLE distribution_lab.replication_probe').fetchall()
        assert sorted(rows)==sorted(primary.execute('TABLE distribution_lab.replication_probe').fetchall())
        e=dict(first_observed_ms=first,absent_while_disabled=absent,catchup_observed_ms=recovery,rows=rows,
            subscription=replica.execute('SELECT subname,subenabled FROM pg_subscription').fetchall(),
            publication=primary.execute('SELECT pubname,puballtables FROM pg_publication').fetchall(),
            limitations='Logical probe only; no cloud, HA failover, schema/sequence replication or backup restore demonstrated')
        save('portfolio-5-distributed-cloud/evidence/replication.json',e)
        return e
    finally: replica.close(); primary.close()

def main():
    for name,fn in [('p1',p1),('p2',p2),('p3',p3),('p4',p4),('p5',p5)]:
        print('Running',name,flush=True)
        try:
            result=fn(); RUN['activities'][name]={'status':'Completed and verified by tool execution','summary':result}
        except Exception as x:
            RUN['activities'][name]={'status':'Implemented but verification failed','error':str(x).replace(PW,'[REDACTED]'),'traceback':traceback.format_exc().replace(PW,'[REDACTED]')}
            save('documentation/run_manifest.json',RUN); raise
        save('documentation/run_manifest.json',RUN)
        print(name,'PASS',flush=True)
    RUN['finished_at']=datetime.now(timezone.utc).isoformat()
    save('documentation/run_manifest.json',RUN)
    print('All five runtime gates passed. Student review, GitHub/access, final summary and submission remain separate gates.',flush=True)
if __name__=='__main__': main()
