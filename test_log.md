Test 2 - send (Msg1, W=1) - Ok
Command:
curl -X POST http://localhost:8000/messages -H "Content-Type: application/json" -d "{\"id\":\"m1\",\"payload\":\"Msg1\",\"w\":1}"
Result:
{"status":"ok","seq":1,"acked_by":["master"]}


Test 3 - send (Msg2, W=2) - Ok
Command:
curl -X POST http://localhost:8000/messages ^
 -H "Content-Type: application/json" ^
 -d "{\"id\":\"m2\",\"payload\":\"Msg2\",\"w\":2}"
Result:
{"status":"ok","seq":2,"acked_by":["master","s1"]}


Test 4 - send (Msg3, W=3) - Wait
Command:
curl -X POST http://localhost:8000/messages ^
 -H "Content-Type: application/json" ^
 -d "{\"id\":\"m3\",\"payload\":\"Msg3\",\"w\":3}"
Result:



Test 5 - send (Msg4, W=1) - Ok
Command:
curl -X POST http://localhost:8000/messages ^
 -H "Content-Type: application/json" ^
 -d "{\"id\":\"m4\",\"payload\":\"Msg4\",\"w\":1}"
Result: 
{"status":"ok","seq":4}

