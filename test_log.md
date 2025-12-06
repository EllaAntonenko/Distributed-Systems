Test 2 - send (Msg1, W=1) - Ok
Command:
curl -X POST -H "Content-Type: application/json" -d "{\"msg\":\"Msg1\",\"w\":1}" http://localhost:5000/message
Result:
{"entry":{"id":"284329f3a73947c3b0accc2676401f1b","msg":"Msg1","seq":1,"ts":1765053171.36539},"status":"ok"}


Test 3 - send (Msg2, W=2) - Ok
Command:
curl -X POST -H "Content-Type: application/json" -d "{\"msg\":\"Msg2\",\"w\":2}" http://localhost:5000/message
Result:
{"acks":2,"entry":{"id":"462398e5cf964f6bb736cbf4416904d7","msg":"Msg2","seq":3,"ts":1765053793.106921},"status":"ok"}


Test 4 - send (Msg3, W=3) - Wait
Command:
curl -X POST -H "Content-Type: application/json" -d "{\"msg\":\"Msg3\",\"w\":3}" http://localhost:5000/message
Result:
{"acks":3,"entry":{"id":"984327ae40334331b0c471daacf9e9d7","msg":"Msg3","seq":4,"ts":1765053863.5495832},"status":"ok"}


Test 5 - send (Msg4, W=1) - Ok
Command:
curl -X POST -H "Content-Type: application/json" -d "{\"msg\":\"Msg4\",\"w\":1}" http://localhost:5000/message
Result: 
{"entry":{"id":"a4bf03c1a4d541378d1fb27cc79e3c0b","msg":"Msg4","seq":6,"ts":1765053938.92979},"status":"ok"}


Test 6 - Check messages on S2 - [Msg1, (Msg2), (Msg3)]
Command:
curl http://localhost:5002/messages
Result:
[{"id":"b991e376e0eb47e6b6806e1978e225a9","msg":"Msg2","seq":2,"ts":1765053383.7896035},{"id":"462398e5cf964f6bb736cbf4416904d7","msg":"Msg2","seq":3,"ts":1765053793.106921},{"id":"984327ae40334331b0c471daacf9e9d7","msg":"Msg3","seq":4,"ts":1765053863.5495832}]



Test 7 - Check messages on M|S1 - [Msg1, Msg2, Msg3, Msg4]
Command:
curl http://localhost:5000/messages

Result:
[{"id":"284329f3a73947c3b0accc2676401f1b","msg":"Msg1","seq":1,"ts":1765053171.36539},{"id":"b991e376e0eb47e6b6806e1978e225a9","msg":"Msg2","seq":2,"ts":1765053383.7896035},{"id":"462398e5cf964f6bb736cbf4416904d7","msg":"Msg2","seq":3,"ts":1765053793.106921},{"id":"984327ae40334331b0c471daacf9e9d7","msg":"Msg3","seq":4,"ts":1765053863.5495832},{"id":"63bf9fa801fe4886bbf714717a570809","msg":"Msg4","seq":5,"ts":1765053933.3843405},{"id":"a4bf03c1a4d541378d1fb27cc79e3c0b","msg":"Msg4","seq":6,"ts":1765053938.92979}]
curl http://localhost:5001/messages

[{"id":"b991e376e0eb47e6b6806e1978e225a9","msg":"Msg2","seq":2,"ts":1765053383.7896035},{"id":"462398e5cf964f6bb736cbf4416904d7","msg":"Msg2","seq":3,"ts":1765053793.106921},{"id":"984327ae40334331b0c471daacf9e9d7","msg":"Msg3","seq":4,"ts":1765053863.5495832}]