# Student Groups Feature - User Guide

## Overview

The Student Groups feature allows Faculty/Officers to organize students into named groups or blocks for easier management and bulk operations. This is particularly useful when you need to process multiple students at once instead of adding them individually.

## How to Use

### 1. Creating a New Group

1. Go to **Faculty Dashboard**
2. Click on **"Student Groups"** button in the toolbar
3. In the "Create New Group" section:
   - Select the **Faculty/Department**
   - Enter a **Group Name** (e.g., "3rd Year CS Students", "Morning Batch")
   - Optionally add a **Description**
4. Click **"Create Group"**

### 2. Adding Students to a Group (Bulk)

**This is the main feature - add multiple students at once!**

1. Open a group by clicking **"Manage"** on the group card
2. In the "Add Multiple Students at Once" section:
   - Paste or type **Student IDs** (separated by commas or newlines)
   - Examples:
     ```
     123456
     123457
     123458
     ```
     OR:
     ```
     123456, 123457, 123458
     ```
3. Click **"Add Students to Group"**
4. The system will:
   - Add all valid student IDs
   - Skip any already in the group
   - Report how many were added/skipped

### 3. Managing Group Members

- View all members in the group table
- See when each student was added
- Remove individual students by clicking the **"Remove"** button
- All members are displayed with their details (Name, Department, Program)

### 4. Viewing All Groups

1. Click **"Student Groups"** from the Faculty Dashboard
2. See all your groups displayed as cards
3. Each card shows:
   - Group name
   - Faculty/Department
   - Number of members
   - Creation info
   - Manage and Delete buttons

### 5. Deleting a Group

1. Click the **"Delete"** button on the group card
2. Confirm deletion
3. **Note**: Only the group is deleted, students remain in the system

## Key Benefits

✅ **Bulk Operations**: Add 50 students to a group in seconds instead of 50 clicks
✅ **Organization**: Keep students organized by year, batch, course, etc.
✅ **Easy Management**: View all group members and remove them individually
✅ **Multiple Groups**: Create as many groups as you need
✅ **No Duplicates**: System prevents adding the same student twice
✅ **Flexible Input**: Enter IDs as comma-separated or newline-separated

## Example Workflows

### Scenario 1: Adding All 3rd Year Students
1. Export student list from your system
2. Copy the student IDs
3. Create group "3rd Year Students"
4. Paste all IDs in the bulk add field
5. Done! All students added instantly

### Scenario 2: Processing Batches
1. Create groups: "Batch A", "Batch B", "Batch C"
2. Add respective students to each group
3. Manage clearance by batch efficiently

### Scenario 3: Department-wise Management
1. Create groups by department
2. Bulk add all students in each department
3. Track clearance status per department

## Technical Details

- **Database**: Uses two new tables: `student_group` and `student_group_member`
- **Permissions**: You can only manage groups for your assigned faculties
- **Storage**: Groups are permanently stored until you delete them
- **Tracking**: System records when each student was added to a group

## Tips & Tricks

- **Export from Excel**: Copy student IDs from Excel column, paste directly
- **Mix Formats**: You can use both commas and newlines in one paste
- **Invalid IDs**: The system will skip any non-student IDs and report how many
- **Already Added**: If a student is already in the group, they won't be added twice
- **Mass Remove**: Delete the group and recreate it if you need to clear all members

## Support

If you encounter any issues:
1. Check that the student IDs are numeric
2. Verify students exist in the system
3. Ensure you have permission for the faculty
4. Check browser console for error messages
