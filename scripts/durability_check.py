"""Optional normal-restart check after verify.py, from the repository root."""
import subprocess, time
import verify as v
with v.connect() as c:
    before=c.execute('SELECT count(*),sum(amount) FROM payflow.transfers').fetchone()
    v.invariant(c)
subprocess.run(['docker','compose','restart','postgres'],cwd=v.R,check=True)
for attempt in range(60):
    try:
        with v.connect() as c:
            after=c.execute('SELECT count(*),sum(amount) FROM payflow.transfers').fetchone()
            assert before==after
            evidence={'before':before,'after':after,'normal_restart':True,'invariants':v.invariant(c),'limitation':'Normal restart only; not power-loss or restore testing'}
        break
    except v.psycopg.OperationalError:
        time.sleep(1)
else:
    raise TimeoutError('Primary did not return after normal restart')
v.save('portfolio-3-transactions-concurrency/evidence/durability.json',evidence)
print('Normal restart durability check passed')
