# Use-Case Diagram

```mermaid
usecaseDiagram
    actor Student as Student
    actor "Faculty / Officer" as Faculty
   

    rectangle "CHECK8 Web Application" {
        %% Authentication / Account
        (Login) as UC_Login
        (Sign up as Student) as UC_SignupStudent
        (Sign up as Instructor) as UC_SignupInstructor

        %% Student use-cases
        (View Clearance Dashboard) as UC_StudentDashboard
        (View Student QR Token) as UC_ViewQR
        (Download Clearance PDF) as UC_DownloadPDF

        %% Faculty use-cases
        (Verify Student Clearance (QR/Token)) as UC_Verify
        (Search Students) as UC_SearchStudents
        (Add Student to Clearance List) as UC_AddStudentClearance
        (Bulk Add Students to Clearance List) as UC_BulkAddStudents
        (Remove Student from Clearance List) as UC_RemoveStudentClearance
        (Update Clearance Status) as UC_UpdateStatus

        %% Student group management
        (List Student Groups) as UC_ListGroups
        (Create Student Group) as UC_CreateGroup
        (View Student Group & Members) as UC_ViewGroup
        (Add Students to Group) as UC_AddStudentsToGroup
        (Remove Student from Group) as UC_RemoveStudentFromGroup
        (Delete Student Group) as UC_DeleteGroup

        %% System admin use-cases (role management)
        (Add Faculty Role to User) as UC_AddFacultyRole
        (Remove Faculty Role from User) as UC_RemoveFacultyRole
    }

    %% Actor associations
    Student --> UC_Login
    Student --> UC_SignupStudent
    Student --> UC_StudentDashboard
    Student --> UC_ViewQR
    Student --> UC_DownloadPDF

    Faculty --> UC_Login
    Faculty --> UC_Verify
    Faculty --> UC_SearchStudents
    Faculty --> UC_AddStudentClearance
    Faculty --> UC_BulkAddStudents
    Faculty --> UC_RemoveStudentClearance
    Faculty --> UC_UpdateStatus
    Faculty --> UC_ListGroups
    Faculty --> UC_CreateGroup
    Faculty --> UC_ViewGroup
    Faculty --> UC_AddStudentsToGroup
    Faculty --> UC_RemoveStudentFromGroup
    Faculty --> UC_DeleteGroup


```

