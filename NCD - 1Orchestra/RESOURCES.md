# ทรัพยากรและ claims

ไม่มี paid API budget ที่ผู้ใช้อนุมัติไว้สำหรับ runner
ตัวเลขใน collection config เป็นข้อเสนอด้านการออกแบบ ไม่ใช่สิทธิเริ่มใช้เงิน
ใช้เครื่องมือที่ session มีอยู่ภายในงานที่ได้รับมอบหมาย; meter ที่ไม่มีให้ unknown

| ทรัพยากร | เพดานเสนอ / สถานะ | การใช้งาน |
| --- | --- | --- |
| Workers | <=3 + coordinator 1 | จำกัดตาม slots จริงด้วย; roles ใช้ต่อกันได้ |
| Search | <=8 queries และ <=10 candidates/scout | ต้องเก็บ actual query log |
| Full document retrieval | <=10/run | rights/access gates ก่อนดึง |
| Requests | timeout 30s, retry <=1, <=10/host/min | หยุดเมื่อ access restricted |
| Model tokens | <=40,000/run เสนอ | ยังไม่มี provider/model หรือ meter |
| API spend | $5/run เสนอ; authorized new paid API spend $0 | ต้องเลือก provider และได้รับงบจริงก่อน |
| CPU/GPU | CPU baseline required; GPU ไม่มี allocation | ระบุเครื่องจริงก่อน experiment |
| Clinical review | ยังไม่มี reviewer ที่ได้รับมอบหมาย | acceptance/gold answers รอคนตรวจ |

ค่า canonical สำหรับ runner ที่จะสร้างอยู่ใน
[collection_agents.json](../configs/collection_agents.json); ขณะนี้ไม่มี runtime enforcement

## Ledger — append-only events

| Event / actual date | Kind | Claim / owner | Scope / limit / usage | State or evidence |
| --- | --- | --- | --- | --- |
| init-20261005 / 2026-10-05 | initialization | none / coordinator | ตั้งโครงเท่านั้น; usage unknown | ไม่มี active claim จากการตั้งโครง |

ก่อนงานจริง append `claim` พร้อม ID, owner, stream/run, เครื่องมือ/อุปกรณ์, limits และ timestamp
เมื่อเสร็จ append `usage` และ `release` อ้าง claim เดิม
Active claims คือ claim events ที่ยังไม่มี release ไม่ใช่การนับทุกแถวในตาราง
เจ้าของแจ้ง coordinator ผ่าน BOARD; coordinator เป็น writer ของ ledger
ไม่มี scheduler หรือ watcher คอย reclaim ทรัพยากรอัตโนมัติ
