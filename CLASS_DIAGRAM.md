# Class Diagram (Database Models)

Excludes: `event`, `event_clearance`, `event_enrollment`, `semester`, `faculty_user_role`, `default_assignatory`.

```classDiagram
direction TB

class Faculty {
    +int id
    +string name
}

class Course {
    +int id
    +string code
    +string name
    +int faculty_id
}

class User {
    +int id
    +string role
    +string student_number
    +string username
    +string email
    +string full_name
    +string password_hash
    +string department
    +string program
    +string qr_salt
}

class InstructorCourse {
    +int id
    +int instructor_id
    +int course_id
}

class StudentCourse {
    +int id
    +int student_id
    +int course_id
}

class ClearanceStatus {
    +int id
    +int student_id
    +int course_id
    +string state
    +string note
    +datetime updated_at
}

class StudentGroup {
    +int id
    +int faculty_id
    +int course_id
    +int created_by_user_id
    +string name
    +string description
}

class StudentGroupMember {
    +int id
    +int group_id
    +int student_id
}

Faculty "1" --> "*" Course
Faculty "1" --> "*" StudentGroup

User "1" --> "*" InstructorCourse : teaches
Course "1" --> "*" InstructorCourse : assigned_to

User "1" --> "*" StudentCourse : enrolls
Course "1" --> "*" StudentCourse : has_students

User "1" --> "*" ClearanceStatus
Course "1" --> "*" ClearanceStatus

Course "1" --> "*" StudentGroup
User "1" --> "*" StudentGroup : creates

StudentGroup "1" --> "*" StudentGroupMember
User "1" --> "*" StudentGroupMember
```

