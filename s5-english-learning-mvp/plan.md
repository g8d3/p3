# English Learning MVP Plan

## Overview
This MVP aims to create an English learning platform where teachers assign AI roles for students to interact with, and track student progress through AI analysis.

## User Types

### Students
- **Chat with AI**: Engage in conversations with an AI assigned a specific role by their teacher.
- **Progress Tracking**: Another AI analyzes chat interactions and saves progress data for each student.

### Teachers
- **Set AI Roles**: Define roles for AIs that students will chat with (e.g., historical figures, professionals).
- **View Progress**: Access and review each student's progress based on AI analysis.

## Features
- User authentication for students and teachers
- Role assignment interface for teachers
- Chat interface for students
- Progress dashboard for teachers
- AI integration for chat and analysis

## Tech Stack
- Frontend: React
- Backend: Node.js with Express
- Database: SQLite or PostgreSQL
- AI: Many AI APIs for chat and analysis, let teacher set:
  - api key,
  - model id,
  - and base api url

## Implementation Plan
1. Set up basic project structure and authentication
2. Implement teacher dashboard for role assignment
3. Build student chat interface
4. Integrate AI for conversations
5. Add progress analysis and storage
6. Create progress viewing for teachers
7. Testing and deployment