# Context Diagram (Strict)

Single system boundary (CHECK8) + external entities only. No internal data stores.

```mermaid
flowchart LR
    Student[Student]
    Faculty[Faculty / Instructor]
    Admin[System Admin]

    System((CHECK8))

    Student <-->|Login/Signup, view clearance status, QR token| System
    Faculty <-->|Verify student (QR/token), manage clearances & groups| System
    Admin <-->|User/faculty/course setup, oversight| System
```

