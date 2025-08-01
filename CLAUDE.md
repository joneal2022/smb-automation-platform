# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Add more if needed

## Repository Overview

1. Initial Analysis and Planning
First think through the problem, read the codebase for relevant files, and write a plan to tasks/todo.md.
2. Design Inspiration
The folder design is a bootstrap5 template that I want to use as the design inspiration of the applications. Please do not make any changes to any file in this folder or subfolders. Use React-Bootstrap components to implement the visual designs shown in the templates.
3. Todo List Structure
The plan should have a list of todo items that you can check off as you complete them.
4. Plan Verification
Before you begin working, check in with me and I will verify the plan.
5. Task Execution
Then, begin working on the todo items, marking them as complete as you go.
6. Communication
Please every step of the way just give me a high level explanation of what changes you made.
7. Simplicity Principle
Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
8. Process Documentation
Every time you perform actions related to the project, append your actions to docs/activity.md and read that file whenever you find it necessary to assist you. Please include every prompt I give. 
9. Git Repository
Every time you make successful changes please push the changes to the current git repository.
10. React Build Folder
The build folder (created by `npm run build`) contains the compiled React application. All files for deployment are generated here. The application uses modern React with Vite or Create React App build process.
11. Component IDs and Data Attributes
In every React component make sure each major element has a unique data-testid that I can use to communicate with you through my prompts when I need to make style changes. Use descriptive names like `data-testid="workflow-builder-canvas"` or `data-testid="document-upload-zone"`.
12. Review Process
Finally, add a review section to the todo.md file with a summary of the changes you made and any other relevant information.