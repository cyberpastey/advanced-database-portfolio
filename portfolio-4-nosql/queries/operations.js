// Run with mongosh against the isolated payflow_lab database after loading validator.
const d=db.getSiblingDB('payflow_lab');
printjson(d.events.find({risk_score:{$gte:70}}).limit(10).toArray());
printjson(d.events.aggregate([{$group:{_id:'$type',count:{$sum:1},meanRisk:{$avg:'$risk_score'}}}]).toArray());
printjson(d.events.getIndexes());
// Executable create/update/delete and validation tests are in scripts/verify.py.
